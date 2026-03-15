import json
import os
from pathlib import Path
from kuroko_core.history import HistoryLogger, HistorySummarizer

def test_history_logging(tmp_path):
    history_file = tmp_path / "history.jsonl"
    logger = HistoryLogger(history_file)
    
    logger.log_event(
        repo_root="/path/to/repo",
        target_project="kuroko",
        mode="deep",
        action="suggest"
    )
    
    assert history_file.exists()
    lines = history_file.read_text().splitlines()
    assert len(lines) == 1
    
    data = json.loads(lines[0])
    assert data["target_project"] == "kuroko"
    assert data["mode"] == "deep"
    assert "timestamp" in data
    assert data["repo_root"] == "/path/to/repo"

def test_history_summarizer(tmp_path):
    history_file = tmp_path / "history.jsonl"
    logger = HistoryLogger(history_file)
    
    # Log some events
    logger.log_event("/repo", "proj-a", "normal", "suggest")
    logger.log_event("/repo", "proj-a", "deep", "suggest")
    logger.log_event("/repo", "proj-b", "rescue", "suggest")
    
    summarizer = HistorySummarizer(history_file)
    summary = summarizer.get_summary(repo_root="/repo", days=7)
    
    assert "proj-a" in summary
    assert "proj-b" in summary
    assert "normal" in summary
    assert "deep" in summary
    assert "rescue" in summary
    assert "2 times" in summary # proj-a
