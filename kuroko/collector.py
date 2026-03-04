import re
import glob
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from kuroko.config import KurokoConfig
from kuroko.parser import parse_checkpoint_file

def collect_checkpoints(
    config: KurokoConfig,
    since: Optional[str] = None,
    until: Optional[str] = None,
    projects: Optional[List[str]] = None,
    issue: Optional[str] = None,
    per_project_files: Optional[int] = None
) -> List[Dict]:
    all_entries = []
    max_files = per_project_files if per_project_files is not None else config.defaults.per_project_files
    
    def normalize_date(date_str: Optional[str]) -> Optional[str]:
        if not date_str:
            return None
        try:
            # Supports slightly different formats and normalizes to YYYY-MM-DD
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            # If it's already in some other format, we might want to fail or just return as is
            return date_str

    norm_since = normalize_date(since)
    norm_until = normalize_date(until)
    
    for project in config.projects:
        if projects and project.name not in projects:
            continue
            
        root_path = Path(project.root)
        if not root_path.exists():
            continue
            
        pattern = str(root_path / "**" / config.defaults.checkpoint_dir / config.defaults.filename_glob)
        files = glob.glob(pattern, recursive=True)
        
        filtered_files = []
        max_depth = config.defaults.max_depth
        
        for f in files:
            file_path = Path(f)
            if max_depth is not None:
                try:
                    rel_parts = file_path.relative_to(root_path).parts
                    checkpoint_idx = rel_parts.index(config.defaults.checkpoint_dir)
                    if checkpoint_idx > max_depth:
                        continue
                except (ValueError, KeyError):
                    continue
                    
            filename = file_path.name
            meta_match = re.match(r'(\d{4}-\d{2}-\d{2})__(.*?)__(.*)\.md', filename)
            if meta_match:
                f_date = meta_match.group(1)
                f_issue_info = meta_match.group(3)
                
                # Precise extraction: ISSUE-123-something -> 123
                f_issue_match = re.search(r'ISSUE-(\d+)', f_issue_info)
                f_issue = f_issue_match.group(1) if f_issue_match else None

                if norm_since and f_date < norm_since:
                    continue
                if norm_until and f_date > norm_until:
                    continue
                if issue and f_issue != str(issue):
                    continue
                
                filtered_files.append(file_path)
            elif not issue:
                # Fallback for non-matching files (only if not filtering by issue)
                filtered_files.append(file_path)
            
        # Sort by (date_from_filename or mtime, filename) to get latest files first
        def sort_key(path: Path):
            name = path.name
            match = re.match(r'(\d{4}-\d{2}-\d{2})', name)
            if match:
                # Use filename date as high priority, but combine with mtime for precision
                return (match.group(1), path.stat().st_mtime, name)
            # Use mtime for both date and precision for non-matching files
            mtime = path.stat().st_mtime
            return (datetime.fromtimestamp(mtime).strftime('%Y-%m-%d'), mtime, name)

        filtered_files.sort(key=sort_key, reverse=True)
        filtered_files = filtered_files[:max_files]
        
        for path_obj in filtered_files:
            filename = path_obj.name
            meta_match = re.match(r'(\d{4}-\d{2}-\d{2})__(.*?)__(.*)\.md', filename)
            
            # Always use project name from config for consistency
            proj_name = project.name
            
            if meta_match:
                date_str = meta_match.group(1)
                issue_info = meta_match.group(3)
                
                # Precise extraction: ISSUE-123-something -> 123
                issue_match = re.search(r'ISSUE-(\d+)', issue_info)
                issue_id = issue_match.group(1) if issue_match else None
            else:
                date_str = datetime.fromtimestamp(path_obj.stat().st_mtime).strftime('%Y-%m-%d')
                issue_id = None
            
            with open(path_obj, "r", encoding="utf-8") as f:
                content = f.read()
                entries = parse_checkpoint_file(content)
                
                for entry in entries:
                    entry.update({
                        "project": proj_name,
                        "date": date_str,
                        "issue": issue_id,
                        "file_path": str(path_obj)
                    })
                    
                    if norm_since and entry["date"] < norm_since:
                        continue
                    if norm_until and entry["date"] > norm_until:
                        continue
                    if issue and entry["issue"] != str(issue):
                        continue
                        
                    all_entries.append(entry)
                    
    # Primary/Secondary: date and time (descending), Tertiary: project (ascending)
    all_entries.sort(key=lambda x: x["project"])
    all_entries.sort(key=lambda x: (x["date"], x["time"]), reverse=True)
    return all_entries
