import json
import os
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from collections import Counter

def get_repo_root(report_path: Optional[str] = None) -> str:
    """Finds the repo root based on report_path if given, otherwise cwd."""
    start_dir = Path(report_path).parent.resolve() if report_path else Path.cwd()
    
    # Climb up to find .git
    current = start_dir
    while current != current.parent:
        if (current / ".git").exists():
            return str(current)
        current = current.parent
        
    try:
        # Fallback to git command if possible, though it uses cwd
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(start_dir),
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception:
        return str(start_dir)

class HistoryLogger:
    def __init__(self, history_path: str):
        self.history_path = Path(os.path.expanduser(history_path))

    def log_event(self, repo_root: str, target_project: Optional[str], mode: str, action: str):
        event = {
            "timestamp": datetime.now().isoformat(),
            "repo_root": repo_root,
            "target_project": target_project,
            "mode": mode,
            "action": action
        }
        
        # Ensure directory exists
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.history_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

class HistorySummarizer:
    def __init__(self, history_path: str):
        self.history_path = Path(os.path.expanduser(history_path))

    def get_summary(self, repo_root: str, days: int = 7) -> str:
        if not self.history_path.exists():
            return ""

        since = datetime.now() - timedelta(days=days)
        events = []
        
        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        ts = datetime.fromisoformat(data["timestamp"])
                        if ts >= since and data.get("repo_root") == repo_root:
                            events.append(data)
                    except (json.JSONDecodeError, ValueError, KeyError):
                        continue
        except Exception:
            return ""

        if not events:
            return ""

        # Aggregate data
        projects = [e["target_project"] for e in events if e.get("target_project")]
        modes = [e["mode"] for e in events if e.get("mode")]
        
        proj_counts = Counter(projects)
        mode_counts = Counter(modes)
        
        summary_lines = ["最近の作業傾向:"]
        
        if proj_counts:
            proj_parts = []
            for proj, count in proj_counts.most_common(3):
                proj_parts.append(f"{proj} ({count} times)")
            summary_lines.append(f"- 注目プロジェクト: {', '.join(proj_parts)}")
            
        if mode_counts:
            mode_parts = []
            for mode, count in mode_counts.most_common(3):
                mode_parts.append(f"{mode}")
            summary_lines.append(f"- よく使うモード: {', '.join(mode_parts)}")
            
        return "\n".join(summary_lines)
