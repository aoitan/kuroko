import re
import glob
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from kuroko.config import KurokoConfig
from kuroko.parser import parse_checkpoint_file

def collect_checkpoints(config: KurokoConfig) -> List[Dict]:
    all_entries = []
    
    for project in config.projects:
        checkpoint_path = Path(project.root) / config.defaults.checkpoint_dir
        pattern = str(checkpoint_path / config.defaults.filename_glob)
        files = glob.glob(pattern)
        
        # ファイル名でソート（YYYY-MM-DD__... なので文字列ソートで新しい順にできる）
        files.sort(reverse=True)
        
        # プロジェクトごとの上限
        files = files[:config.defaults.per_project_files]
        
        for file_path in files:
            path_obj = Path(file_path)
            filename = path_obj.name
            
            # ファイル名からメタデータを抽出
            # YYYY-MM-DD__{project}__ISSUE-{number}.md
            # YYYY-MM-DD__{project}__misc.md
            meta_match = re.match(r'(\d{4}-\d{2}-\d{2})__(.*?)__(.*)\.md', filename)
            if meta_match:
                date_str = meta_match.group(1)
                proj_name = meta_match.group(2)
                issue_info = meta_match.group(3)
                issue_id = issue_info.replace("ISSUE-", "") if "ISSUE-" in issue_info else None
            else:
                # パースできない場合はmtimeとファイル名から推測
                date_str = datetime.fromtimestamp(path_obj.stat().st_mtime).strftime('%Y-%m-%d')
                proj_name = project.name
                issue_id = None
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                entries = parse_checkpoint_file(content)
                
                for entry in entries:
                    entry.update({
                        "project": proj_name,
                        "date": date_str,
                        "issue": issue_id,
                        "file_path": str(file_path)
                    })
                    all_entries.append(entry)
                    
    # 全エントリを日付と時間でソート
    all_entries.sort(key=lambda x: (x["date"], x["time"]), reverse=True)
    return all_entries
