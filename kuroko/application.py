import argparse
import hashlib
import json
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
        payload = build_shinko_insight_payload(cfg, project=project, max_chars=max_chars)
        if payload:
            return json.dumps(payload, ensure_ascii=False, indent=2)

    if report_path.exists():
        with open(report_path, "r", encoding="utf-8") as f:
            report_text = f.read()
        return _truncate_context(report_text, max_chars)

    raise FileNotFoundError(f"Report file not found: {report_path}")


def build_shinko_insight_payload(
    cfg: KurokoConfig,
    *,
    project: Optional[str] = None,
    max_chars: int = 20000,
    max_sources: int = 5,
    max_chunks_per_source: int = 8,
) -> Optional[dict]:
    db_path = Path(cfg.db_path).expanduser()
    if not db_path.exists():
        return None

    project_roots = []
    for project_cfg in cfg.projects:
        if project and project_cfg.name != project:
            continue
        project_roots.append(str(Path(project_cfg.root).expanduser()))

    if project and not project_roots:
        return None

    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        source_batch_size = max(max_sources or 0, 100)
        source_offset = 0
        selected_source_rows: list[sqlite3.Row] = []

        while True:
            source_rows = conn.execute(
                """
                SELECT
                    s.id AS source_id,
                    s.path,
                    s.directory_context,
                    s.raw_text,
                    s.file_hash,
                    s.updated_at
                FROM source_texts s
                ORDER BY s.updated_at DESC, s.id DESC
                LIMIT ? OFFSET ?
                """,
                (source_batch_size, source_offset),
            ).fetchall()
            if not source_rows:
                break

            for source_row in source_rows:
                path = source_row["path"]
                if project_roots and not any(_is_under_project_root(path, root) for root in project_roots):
                    continue
                selected_source_rows.append(source_row)
                if max_sources is not None and len(selected_source_rows) >= max_sources:
                    break

            if max_sources is not None and len(selected_source_rows) >= max_sources:
                break

            source_offset += len(source_rows)

        if not selected_source_rows:
            return None

        selected_source_ids = [row["source_id"] for row in selected_source_rows]
        placeholders = ", ".join("?" for _ in selected_source_ids)
        rows = conn.execute(
            f"""
            SELECT
                s.id AS source_id,
                s.path,
                s.directory_context,
                s.raw_text,
                s.file_hash,
                s.updated_at,
                c.id AS chunk_id,
                c.chunk_index,
                c.chunk_text,
                c.heading,
                c.block_timestamp,
                c.chunk_hash,
                i.id AS inference_id,
                i.inference_type,
                i.content AS inference_content,
                i.metadata AS inference_metadata
            FROM source_texts s
            LEFT JOIN chunks c ON c.source_id = s.id
            LEFT JOIN inferences i ON i.chunk_id = c.id
            WHERE s.id IN ({placeholders})
            ORDER BY s.updated_at DESC, s.id DESC, c.chunk_index ASC, c.id ASC, i.id ASC
            """,
            selected_source_ids,
        ).fetchall()
    finally:
        conn.close()

    sources_by_id: dict[int, dict] = {}
    source_order: list[int] = []
    total_chars = 0
    truncated = False
    exhausted_budget = False

    for row in rows:
        if exhausted_budget:
            truncated = True
            break

        path = row["path"]
        source_id = row["source_id"]
        source = sources_by_id.get(source_id)
        if source is None:
            if len(source_order) >= max_sources:
                truncated = True
                continue

            remaining_chars = max_chars - total_chars
            raw_excerpt, raw_truncated, raw_chars = _allocate_excerpt(row["raw_text"] or "", remaining_chars)
            total_chars += raw_chars
            truncated = truncated or raw_truncated
            if remaining_chars <= 0 or total_chars >= max_chars:
                exhausted_budget = True
                if not raw_excerpt:
                    break

            source = {
                "source_id": source_id,
                "path": path,
                "directory_context": row["directory_context"],
                "file_hash": row["file_hash"],
                "updated_at": row["updated_at"],
                "raw_text": raw_excerpt,
                "raw_text_truncated": raw_truncated,
                "chunks": [],
            }
            sources_by_id[source_id] = source
            source_order.append(source_id)

        chunk_id = row["chunk_id"]
        if chunk_id is None:
            continue

        chunks = source["chunks"]
        existing_chunk = next((item for item in chunks if item["chunk_id"] == chunk_id), None)
        if existing_chunk is None:
            if len(chunks) >= max_chunks_per_source:
                truncated = True
                continue

            remaining_chars = max_chars - total_chars
            chunk_excerpt, chunk_truncated, chunk_chars = _allocate_excerpt(
                row["chunk_text"] or "",
                remaining_chars,
            )
            total_chars += chunk_chars
            truncated = truncated or chunk_truncated
            if remaining_chars <= 0 or total_chars >= max_chars:
                exhausted_budget = True
                if not chunk_excerpt:
                    break
            existing_chunk = {
                "chunk_id": chunk_id,
                "chunk_index": row["chunk_index"],
                "heading": row["heading"],
                "block_timestamp": row["block_timestamp"],
                "chunk_hash": row["chunk_hash"],
                "chunk_text": chunk_excerpt,
                "chunk_text_truncated": chunk_truncated,
                "inferences": [],
            }
            chunks.append(existing_chunk)

        if row["inference_id"] is not None:
            existing_chunk["inferences"].append(
                {
                    "inference_type": row["inference_type"],
                    "content": row["inference_content"],
                    "metadata": row["inference_metadata"],
                }
            )

    ordered_sources = [sources_by_id[source_id] for source_id in source_order]
    if not ordered_sources:
        return None

    source_hash = hashlib.sha256(
        json.dumps(
            [
                {
                    "source_id": source["source_id"],
                    "path": source["path"],
                    "file_hash": source["file_hash"],
                    "chunks": [
                        {
                            "chunk_hash": chunk["chunk_hash"],
                            "inferences": chunk["inferences"],
                        }
                        for chunk in source["chunks"]
                    ],
                }
                for source in ordered_sources
            ],
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    return {
        "project": project or "overall",
        "generated_from": "db",
        "source_hash": source_hash,
        "extractor_version": "rule-based-v1",
        "truncated": truncated,
        "budget": {
            "max_chars": max_chars,
            "max_sources": max_sources,
            "max_chunks_per_source": max_chunks_per_source,
        },
        "sources": ordered_sources,
    }


def save_shinko_insight_result(
    db_path: str,
    *,
    project: str,
    source_hash: str,
    extractor_version: str,
    model: str,
    prompt_version: str,
    schema_version: str,
    payload_truncated: bool,
    records: list[dict],
) -> None:
    conn = sqlite3.connect(str(Path(db_path).expanduser()))
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(
            """
            UPDATE shinko_insights
            SET invalidated_at = CURRENT_TIMESTAMP
            WHERE project = ? AND invalidated_at IS NULL
            """,
            (project,),
        )

        for record in records:
            cursor = conn.execute(
                """
                INSERT INTO shinko_insights (
                    project,
                    kind,
                    summary,
                    is_todo,
                    is_ongoing,
                    should_review_this_week,
                    blocked_reason,
                    next_action,
                    confidence,
                    source_hash,
                    extractor_version,
                    model,
                    prompt_version,
                    schema_version,
                    payload_truncated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project,
                    record["kind"],
                    record["summary"],
                    int(record["judgements"]["is_todo"]),
                    int(record["judgements"]["is_ongoing"]),
                    int(record["judgements"]["should_review_this_week"]),
                    record.get("blocked_reason"),
                    record.get("next_action"),
                    float(record["confidence"]),
                    source_hash,
                    extractor_version,
                    model,
                    prompt_version,
                    schema_version,
                    int(payload_truncated),
                ),
            )
            insight_id = cursor.lastrowid
            for order, evidence in enumerate(record.get("evidence", []), start=1):
                conn.execute(
                    """
                    INSERT INTO shinko_insight_evidence (
                        insight_id,
                        source_id,
                        chunk_id,
                        quote_excerpt,
                        evidence_order
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        insight_id,
                        evidence.get("source_id"),
                        evidence.get("chunk_id"),
                        evidence.get("quote_excerpt"),
                        order,
                    ),
                )

        conn.commit()
    finally:
        conn.close()


def get_latest_shinko_insights(db_path: str, *, project: str) -> list[dict]:
    conn = sqlite3.connect(str(Path(db_path).expanduser()))
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                si.id,
                si.project,
                si.kind,
                si.summary,
                si.is_todo,
                si.is_ongoing,
                si.should_review_this_week,
                si.blocked_reason,
                si.next_action,
                si.confidence,
                si.source_hash,
                si.extractor_version,
                si.model,
                si.prompt_version,
                si.schema_version,
                si.analyzed_at,
                si.payload_truncated,
                se.source_id,
                se.chunk_id,
                se.quote_excerpt,
                se.evidence_order
            FROM shinko_insights si
            LEFT JOIN shinko_insight_evidence se ON se.insight_id = si.id
            WHERE si.project = ? AND si.invalidated_at IS NULL
            ORDER BY si.id ASC, se.evidence_order ASC, se.id ASC
            """,
            (project,),
        ).fetchall()
    finally:
        conn.close()

    insights: dict[int, dict] = {}
    ordered_ids: list[int] = []
    for row in rows:
        insight = insights.get(row["id"])
        if insight is None:
            insight = {
                "id": row["id"],
                "project": row["project"],
                "kind": row["kind"],
                "summary": row["summary"],
                "judgements": {
                    "is_todo": bool(row["is_todo"]),
                    "is_ongoing": bool(row["is_ongoing"]),
                    "should_review_this_week": bool(row["should_review_this_week"]),
                },
                "blocked_reason": row["blocked_reason"],
                "next_action": row["next_action"],
                "confidence": row["confidence"],
                "source_hash": row["source_hash"],
                "extractor_version": row["extractor_version"],
                "model": row["model"],
                "prompt_version": row["prompt_version"],
                "schema_version": row["schema_version"],
                "analyzed_at": row["analyzed_at"],
                "payload_truncated": bool(row["payload_truncated"]),
                "evidence": [],
            }
            insights[row["id"]] = insight
            ordered_ids.append(row["id"])
        if row["source_id"] is not None or row["chunk_id"] is not None or row["quote_excerpt"] is not None:
            insight["evidence"].append(
                {
                    "source_id": row["source_id"],
                    "chunk_id": row["chunk_id"],
                    "quote_excerpt": row["quote_excerpt"],
                }
            )

    return [insights[insight_id] for insight_id in ordered_ids]


def _truncate_context(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n(Truncated for LLM context...)"


def _allocate_excerpt(text: str, remaining_chars: int) -> tuple[str, bool, int]:
    if remaining_chars <= 0:
        return "", True, 0
    if len(text) <= remaining_chars:
        return text, False, len(text)
    return text[:remaining_chars], True, remaining_chars


def _is_under_project_root(path: str, root: str) -> bool:
    resolved_path = os.path.normcase(str(Path(path).expanduser().resolve(strict=False)))
    resolved_root = os.path.normcase(str(Path(root).expanduser().resolve(strict=False)))
    try:
        return os.path.commonpath([resolved_path, resolved_root]) == resolved_root
    except ValueError:
        return False
