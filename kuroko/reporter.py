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

    # Escape filter names/values just in case
    filters_str = ", ".join(f"{html.escape(k)}={html.escape(v)}" for k, v in (filters or {}).items() if v)
    if not filters_str:
        filters_str = "none"

    lines = []

    lines.append(f"# {html.escape(title)}")
    lines.append("")
    lines.append(f"- generated_at: {generated_at.isoformat()}")
    lines.append(f"- per_project_files: {per_project_files}")
    lines.append(f"- filters: {filters_str}")
    lines.append("")

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
            # Escape HTML and | then replace newlines with <br> to avoid breaking the table and XSS
            act_str = html.escape(entry['act']).replace('|', '&#124;').replace('\n', '<br>')
            lines.append(f"| {entry['date']} | {entry['time']} | {phase_str} | {html.escape(entry['project'])} | {issue_str} | {act_str} |")
        lines.append("")

    lines.append("## Blockers")
    blockers = [e for e in entries if e.get('block') and e['block'].strip().lower() not in BLOCK_IGNORE]

    if not blockers:
        lines.append("No active blockers.")
        lines.append("")
    else:
        for entry in blockers:
            issue_str = f"#{entry['issue']}" if entry.get('issue') else "misc"
            phase_str = _shorten_phase(entry['phase'])
            # Escape for safety
            block_text = html.escape(entry['block']).replace('\n', ' ')
            headline = f"- **[{html.escape(entry['project'])} {issue_str} | {entry['date']} {entry['time']} | {phase_str}] {block_text}**"
            lines.append(headline)

            details = []
            # Also escape newlines in act for consistency in details list
            act_detail = html.escape(entry['act']).replace('\n', ' ')
            details.append(f"  - act: {act_detail}")
            if include_evidence and entry.get('evd'):
                details.append("  - evd:")
                details.append("    ```")
                # Do NOT html.escape here to avoid double escaping in code block.
                # Just prevent escaping the code block itself.
                evd_safe = entry['evd'].replace('```', '\\`\\`\\` ')
                for line in evd_safe.split('\n'):
                    details.append(f"    {line}")
                details.append("    ```")
            if include_path and entry.get('file_path'):
                details.append(f"  - file_path: `{entry['file_path']}`")

            if collapse_details:
                lines.append("  <details markdown=\"1\"><summary>details</summary>\n")
                lines.extend(details)
                lines.append("\n  </details>")
            else:
                lines.extend(details)
            lines.append("")

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
                # Replace newlines for single-line display
                act_oneline = html.escape(entry['act']).replace('\n', ' ')
                lines.append(f"- {entry['time']} {phase_str} {html.escape(entry['project'])} {issue_str} {act_oneline}")
            lines.append("")


    if include_path:
        lines.append("## Sources")
        if not entries:
            lines.append("No entries found.")
            lines.append("")
        else:
            unique_paths = sorted(list({entry['file_path'] for entry in entries if entry.get('file_path')}))
            for path in unique_paths:
                lines.append(f"- {path}")
            lines.append("")

    return "\n".join(lines)
