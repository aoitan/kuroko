import html
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
from kuroko.constants import BLOCK_IGNORE


PHASE_MAP = {
    "planning": "plan",
    "coding": "code",
    "review": "rev",
    "fix": "fix",
    "closing": "done"
}


def _shorten_phase(phase: str) -> str:
    if not phase:
        return ""
    return PHASE_MAP.get(phase.lower(), phase)


def generate_report(
    entries: List[Dict[str, Any]],
    title: str = "Kuroko Report",
    generated_at: Optional[datetime] = None,
    per_project_files: int = 5,
    filters: Optional[Dict[str, str]] = None,
    include_path: bool = False,
    include_evidence: bool = True,
    collapse_details: bool = True
) -> str:
    if generated_at is None:
        generated_at = datetime.now()

    filters_str = ", ".join(f"{k}={v}" for k, v in (filters or {}).items() if v)
    if not filters_str:
        filters_str = "none"

    lines = []

    # 1) Header
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- generated_at: {generated_at.isoformat()}")
    lines.append(f"- per_project_files: {per_project_files}")
    lines.append(f"- filters: {filters_str}")
    lines.append("")

    # 2) Status
    lines.append("## Status")
    if not entries:
        lines.append("No entries found.")
        lines.append("")
    else:
        lines.append("| date | time | phase | project | issue | act |")
        lines.append("|---|---:|---|---|---:|---|")

        latest_by_proj = {}
        for entry in entries:
            if entry['project'] not in latest_by_proj:
                latest_by_proj[entry['project']] = entry

        for project in sorted(latest_by_proj.keys()):
            entry = latest_by_proj[project]
            issue_str = f"#{entry['issue']}" if entry.get('issue') else "-"
            phase_str = _shorten_phase(entry['phase'])
            # Escape | and replace newlines with <br> to avoid breaking the table
            # No html.escape here to maintain human readability in Markdown files.
            act_str = entry['act'].replace('|', '&#124;').replace('\n', '<br>')
            lines.append(f"| {entry['date']} | {entry['time']} | {phase_str} | {entry['project']} | {issue_str} | {act_str} |")
        lines.append("")

    # 3) Blockers
    lines.append("## Blockers")
    blockers = [e for e in entries if e.get('block') and e['block'].strip().lower() not in BLOCK_IGNORE]

    if not blockers:
        lines.append("No active blockers.")
        lines.append("")
    else:
        for entry in blockers:
            issue_str = f"#{entry['issue']}" if entry.get('issue') else "misc"
            phase_str = _shorten_phase(entry['phase'])
            block_text = entry['block'].replace('\n', ' ')
            headline = f"- **[{entry['project']} {issue_str} | {entry['date']} {entry['time']} | {phase_str}] {block_text}**"
            lines.append(headline)

            details = []
            act_detail = entry['act'].replace('\n', ' ')
            details.append(f"  - act: {act_detail}")
            if include_evidence and entry.get('evd'):
                details.append("  - evd:")
                details.append("    ```")
                # Prevent escaping the code block itself
                evd_safe = entry['evd'].replace('```', '\\`\\`\\` ')
                for line in evd_safe.split('\n'):
                    details.append(f"    {line}")
                details.append("    ```")
            if include_path and entry.get('file_path'):
                details.append(f"  - file_path: `{entry['file_path']}`")

            if collapse_details:
                # markdown="1" is needed for Python-Markdown to parse content inside raw HTML blocks
                lines.append("  <details markdown=\"1\"><summary>details</summary>")
                lines.append("")
                lines.extend(details)
                lines.append("")
                lines.append("  </details>")
            else:
                lines.extend(details)
            lines.append("")

    # 4) Recent
    lines.append("## Recent")
    if not entries:
        lines.append("No entries found.")
        lines.append("")
    else:
        by_date = defaultdict(list)
        for entry in entries:
            by_date[entry['date']].append(entry)

        for date in sorted(by_date.keys(), reverse=True):
            lines.append(f"### {date}")
            day_entries = sorted(by_date[date], key=lambda x: x["time"], reverse=True)
            for entry in day_entries:
                issue_str = f"#{entry['issue']}" if entry.get('issue') else "-"
                phase_str = _shorten_phase(entry['phase'])
                act_oneline = entry['act'].replace('\n', ' ')
                lines.append(f"- {entry['time']} {phase_str} {entry['project']} {issue_str} {act_oneline}")
            lines.append("")

    # 5) Sources
    if include_path:
        lines.append("## Sources")
        if not entries:
            lines.append("No entries found.")
            lines.append("")
        else:
            unique_paths = sorted(list({entry['file_path'] for entry in entries if entry.get('file_path')}))
            for path in unique_paths:
                lines.append(f"- `{html.escape(path)}`")
            lines.append("")

    return "\n".join(lines)
