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
    
    # max file count configuration
    max_files = per_project_files if per_project_files is not None else config.defaults.per_project_files
    
    for project in config.projects:
        # Filter by project names
        if projects and project.name not in projects:
            continue
            
        root_path = Path(project.root)
        if not root_path.exists():
            continue
            
        # 再帰的に checkpoint ディレクトリ内のファイルを探索
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
            filtered_files.append(file_path)
            
        filtered_files.sort(key=lambda x: x.name, reverse=True)
        filtered_files = filtered_files[:max_files]
        
        for path_obj in filtered_files:
            filename = path_obj.name
            
            meta_match = re.match(r'(\d{4}-\d{2}-\d{2})__(.*?)__(.*)\.md', filename)
            if meta_match:
                date_str = meta_match.group(1)
                proj_name = meta_match.group(2)
                issue_info = meta_match.group(3)
                issue_id = issue_info.replace("ISSUE-", "") if "ISSUE-" in issue_info else None
            else:
                date_str = datetime.fromtimestamp(path_obj.stat().st_mtime).strftime('%Y-%m-%d')
                proj_name = project.name
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
                    
                    # Apply filters
                    if since and entry["date"] < since:
                        continue
                    if until and entry["date"] > until:
                        continue
                    if issue and entry["issue"] != str(issue):
                        continue
                        
                    all_entries.append(entry)
                    
    all_entries.sort(key=lambda x: (x["date"], x["time"]), reverse=True)
    return all_entries
