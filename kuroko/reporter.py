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
    collapse_details: bool = True,
    worklists: Optional[List[Dict[str, Any]]] = None
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

    # 3) Worklist
    if worklists is not None:
        lines.append("## Worklist")
        if not worklists:
            lines.append("No worklist data available or no repositories configured.")
        else:
            for res in worklists:
                pr_count = len(res["pull_requests"])
                issue_count = len(res["issues"])
                total_prs = res.get("total_pull_requests", -1)
                total_issues = res.get("total_issues", -1)
                
                pr_total_str = f"{total_prs}" if total_prs >= 0 else "unknown"
                issue_total_str = f"{total_issues}" if total_issues >= 0 else "unknown"
                
                lines.append(f"### {res['project']} ({res['repo']})")
                lines.append(f"Summary: {pr_total_str} Open PRs (showing latest {pr_count}), {issue_total_str} Open Issues (showing latest {issue_count})")
                lines.append("")
                
                lines.append("#### Open Pull Requests")
                if not res["pull_requests"]:
                    lines.append("No open PRs.")
                else:
                    lines.append("| ID | Title | Labels | Updated |")
                    lines.append("|---|---|---|---|")
                    for pr in res["pull_requests"]:
                        labels_str = ", ".join(pr['labels']) if pr['labels'] else "-"
                        labels_str = labels_str.replace('|', '&#124;').replace('\n', ' ')
                        # Escape Markdown link brackets
                        title_safe = pr['title'].replace('|', '&#124;').replace('\n', ' ').replace('[', '\\[').replace(']', '\\]')
                        title_link = f"[{title_safe}]({pr['url']})"
                        lines.append(f"| #{pr['id']} | {title_link} | {labels_str} | {pr['updated_at']} |")
                
                lines.append("")
                lines.append("#### Open Issues")
                if not res["issues"]:
                    lines.append("No open issues.")
                else:
                    lines.append("| ID | Title | Labels | Updated |")
                    lines.append("|---|---|---|---|")
                    for issue in res["issues"]:
                        labels_str = ", ".join(issue['labels']) if issue['labels'] else "-"
                        labels_str = labels_str.replace('|', '&#124;').replace('\n', ' ')
                        # Escape Markdown link brackets
                        title_safe = issue['title'].replace('|', '&#124;').replace('\n', ' ').replace('[', '\\[').replace(']', '\\]')
                        title_link = f"[{title_safe}]({issue['url']})"
                        lines.append(f"| #{issue['id']} | {title_link} | {labels_str} | {issue['updated_at']} |")
                lines.append("")
        lines.append("")

    # 4) Blockers
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
                details.append("    ~~~~")
                # Use tildes for outer fence to allow triple backticks inside without escaping issues
                for line in entry['evd'].split('\n'):
                    details.append(f"    {line}")
                details.append("    ~~~~")
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

    # 5) Recent
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

    # 6) Sources
    if include_path:
        lines.append("## Sources")
        if not entries:
            lines.append("No entries found.")
            lines.append("")
        else:
            unique_paths = sorted(list({entry['file_path'] for entry in entries if entry.get('file_path')}))
            for path in unique_paths:
                lines.append(f"- `{path}`")
            lines.append("")

    return "\n".join(lines)
