from typing import List, Dict, Any
from datetime import datetime
from collections import defaultdict

PHASE_MAP = {
    "planning": "plan",
    "coding": "code",
    "review": "rev",
    "fix": "fix",
    "closing": "done"
}

def _shorten_phase(phase: str) -> str:
    return PHASE_MAP.get(phase.lower(), phase)

def generate_report(
    entries: List[Dict[str, Any]],
    title: str = "Kuroko Report",
    generated_at: datetime = None,
    per_project_files: int = 5,
    filters: Dict[str, str] = None,
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
    
    if not entries:
        lines.append("No entries found.")
        return "\n".join(lines)
        
    # 2) Status
    lines.append("## Status")
    lines.append("| date | time | phase | project | issue | act |")
    lines.append("|---|---:|---|---|---:|---|")
    
    latest_by_proj = {}
    for e in entries:
        if e['project'] not in latest_by_proj:
            latest_by_proj[e['project']] = e
            
    # Sort projects for stability
    for proj in sorted(latest_by_proj.keys()):
        e = latest_by_proj[proj]
        issue_str = f"#{e['issue']}" if e.get('issue') else "-"
        phase_str = _shorten_phase(e['phase'])
        lines.append(f"| {e['date']} | {e['time']} | {phase_str} | {e['project']} | {issue_str} | {e['act']} |")
    lines.append("")
    
    # 3) Blockers
    lines.append("## Blockers")
    block_ignore = ["なし", "none", "n/a", "na", "-"]
    blockers = [e for e in entries if e.get('block') and e['block'].strip().lower() not in block_ignore]
    
    if not blockers:
        lines.append("No active blockers.")
    else:
        for e in blockers:
            issue_str = f"#{e['issue']}" if e.get('issue') else "misc"
            phase_str = _shorten_phase(e['phase'])
            headline = f"- **[{e['project']} {issue_str} | {e['date']} {e['time']} | {phase_str}] {e['block']}**"
            lines.append(headline)
            
            details = []
            details.append(f"  - act: {e['act']}")
            if include_evidence and e.get('evd'):
                details.append(f"  - evd: `{e['evd']}`")
            if include_path and e.get('file_path'):
                details.append(f"  - file_path: `{e['file_path']}`")
                
            if collapse_details:
                lines.append("  <details><summary>details</summary>\n")
                lines.extend(details)
                lines.append("\n  </details>")
            else:
                lines.extend(details)
            lines.append("")
            
    # 4) Recent
    lines.append("## Recent")
    by_date = defaultdict(list)
    for e in entries:
        by_date[e['date']].append(e)
        
    for date in sorted(by_date.keys(), reverse=True):
        lines.append(f"### {date}")
        for e in by_date[date]:
            issue_str = f"#{e['issue']}" if e.get('issue') else "-"
            phase_str = _shorten_phase(e['phase'])
            lines.append(f"- {e['time']} {phase_str} {e['project']} {issue_str} {e['act']}")
        lines.append("")
        
    # 5) Sources
    if include_path:
        lines.append("## Sources")
        unique_paths = sorted(list({e['file_path'] for e in entries if e.get('file_path')}))
        for p in unique_paths:
            lines.append(f"- {p}")
        lines.append("")

    return "\n".join(lines)
