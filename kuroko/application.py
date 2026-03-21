import argparse
import os
import sqlite3
import shlex
import sys
import warnings
from pathlib import Path
from datetime import datetime
from typing import Iterable, Optional

from kuroko.collector import collect_checkpoints
from kuroko.reporter import generate_report
from kuroko_core.config import KurokoConfig, load_config


class ReportArgsParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(f"Unsupported report args: {message}")


def validate_report_date(date_str: Optional[str], param_name: str) -> Optional[str]:
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"Error: Invalid date format for {param_name}. Must be YYYY-MM-DD.") from exc


def normalize_issue(issue: Optional[str]) -> Optional[str]:
    if not issue:
        return None
    return issue.replace("ISSUE-", "").replace("#", "")


def _normalize_projects(project: Optional[Iterable[str]]) -> Optional[tuple[str, ...]]:
    if not project:
        return None
    return tuple(project)


def _collect_worklists(cfg: KurokoConfig, projects: Optional[tuple[str, ...]], limit: int = 5):
    from kuroko.worklist import fetch_worklist

    worklists = []
    for project in cfg.projects:
        if projects and project.name not in projects:
            continue
        if not project.repo:
            continue
        try:
            data = fetch_worklist(project.repo, limit=limit)
        except RuntimeError as exc:
            warnings.warn(f"Failed to fetch worklist for {project.name}: {exc}", RuntimeWarning)
            continue
        data["project"] = project.name
        worklists.append(data)
    return worklists


def build_report_text(
    cfg: KurokoConfig,
    *,
    per_project_files: Optional[int] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    project: Optional[Iterable[str]] = None,
    issue: Optional[str] = None,
    include_path: bool = False,
    include_evidence: bool = True,
    include_worklist: bool = False,
    collapse_details: bool = True,
    title: str = "Kuroko Report",
) -> str:
    since = validate_report_date(since, "--since")
    until = validate_report_date(until, "--until")
    clean_issue = normalize_issue(issue)
    projects = _normalize_projects(project)
    actual_per_project = per_project_files if per_project_files is not None else cfg.defaults.per_project_files

    entries = collect_checkpoints(
        config=cfg,
        since=since,
        until=until,
        projects=list(projects) if projects else None,
        issue=clean_issue,
        per_project_files=actual_per_project,
    )

    worklists = None
    if include_worklist:
        worklists = _collect_worklists(cfg, projects)

    filters = {}
    if projects:
        filters["project"] = ",".join(projects)
    if clean_issue:
        filters["issue"] = clean_issue
    if since:
        filters["since"] = since
    if until:
        filters["until"] = until

    return generate_report(
        entries=entries,
        title=title,
        per_project_files=actual_per_project,
        filters=filters,
        include_path=include_path,
        include_evidence=include_evidence,
        collapse_details=collapse_details,
        worklists=worklists,
    )


def render_report_to_path(
    output_path: Path,
    *,
    config_path: Optional[str] = None,
    per_project_files: Optional[int] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    project: Optional[Iterable[str]] = None,
    issue: Optional[str] = None,
    include_path: bool = False,
    include_evidence: bool = True,
    include_worklist: bool = False,
    collapse_details: bool = True,
    title: str = "Kuroko Report",
) -> str:
    cfg = load_config(config_path)
    content = build_report_text(
        cfg,
        per_project_files=per_project_files,
        since=since,
        until=until,
        project=project,
        issue=issue,
        include_path=include_path,
        include_evidence=include_evidence,
        include_worklist=include_worklist,
        collapse_details=collapse_details,
        title=title,
    )

    out_path = Path(output_path)
    if out_path.parent != Path(".") and not out_path.parent.exists():
        raise ValueError(f"Error: Directory '{out_path.parent}' does not exist.")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    return content


def parse_report_args(report_args: str) -> dict:
    parser = ReportArgsParser(add_help=False)
    parser.add_argument("--per-project-files", type=int, default=None)
    parser.add_argument("--since", default=None)
    parser.add_argument("--until", default=None)
    parser.add_argument("--project", action="append", default=[])
    parser.add_argument("--issue", default=None)
    parser.add_argument("--include-path", action="store_true")
    parser.add_argument("--include-evidence", dest="include_evidence", action="store_true", default=True)
    parser.add_argument("--no-include-evidence", dest="include_evidence", action="store_false")
    parser.add_argument("--include-worklist", action="store_true")
    parser.add_argument("--collapse-details", dest="collapse_details", action="store_true", default=True)
    parser.add_argument("--no-collapse-details", dest="collapse_details", action="store_false")
    parser.add_argument("--title", default="Kuroko Report")
    parsed = parser.parse_args(
        shlex.split(report_args, posix=(sys.platform != "win32")) if report_args else []
    )
    result = vars(parsed)
    result["project"] = tuple(result["project"])
    return result


def build_shinko_context(cfg: KurokoConfig, report_path: Path, project: Optional[str] = None, max_chars: int = 20000) -> str:
    db_path = Path(cfg.db_path).expanduser()
    if db_path.exists():
        context = _build_db_context(db_path, cfg, project=project)
        if context:
            return _truncate_context(context, max_chars)

    if report_path.exists():
        with open(report_path, "r", encoding="utf-8") as f:
            report_text = f.read()
        return _truncate_context(report_text, max_chars)

    raise FileNotFoundError(f"Report file not found: {report_path}")


def _build_db_context(db_path: Path, cfg: KurokoConfig, project: Optional[str] = None) -> str:
    project_roots = []
    for project_cfg in cfg.projects:
        if project and project_cfg.name != project:
            continue
        project_roots.append(str(Path(project_cfg.root).expanduser()))

    if project and not project_roots:
        return ""

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                s.path,
                s.directory_context,
                s.raw_text,
                c.chunk_index,
                c.chunk_text,
                c.heading,
                c.block_timestamp
            FROM source_texts s
            LEFT JOIN chunks c ON c.source_id = s.id
            ORDER BY s.updated_at DESC, s.id DESC, c.chunk_index ASC
            """
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    lines = []
    seen_sources = set()
    for path, directory_context, raw_text, chunk_index, chunk_text, heading, block_timestamp in rows:
        if project_roots and not any(_is_under_project_root(path, root) for root in project_roots):
            continue

        if path not in seen_sources:
            seen_sources.add(path)
            lines.append(f"Source: {path}")
            if directory_context:
                lines.append(f"Directory: {directory_context}")
            lines.append(f"Raw: {raw_text}")
        if chunk_text:
            header = f"Chunk {chunk_index}"
            meta = [value for value in (heading, block_timestamp) if value]
            if meta:
                header += f" ({' / '.join(meta)})"
            lines.append(f"{header}: {chunk_text}")
        lines.append("")

    return "\n".join(lines).strip()


def _truncate_context(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n(Truncated for LLM context...)"


def _is_under_project_root(path: str, root: str) -> bool:
    resolved_path = os.path.normcase(str(Path(path).expanduser().resolve(strict=False)))
    resolved_root = os.path.normcase(str(Path(root).expanduser().resolve(strict=False)))
    try:
        return os.path.commonpath([resolved_path, resolved_root]) == resolved_root
    except ValueError:
        return False
