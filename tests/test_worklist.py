import pytest
import json
from unittest.mock import patch, MagicMock
from kuroko.worklist import fetch_worklist

def test_fetch_worklist_parsing():
    # Mock gh pr list
    pr_json = '[{"number":1,"title":"PR 1","state":"OPEN","updatedAt":"2026-03-01T12:00:00Z","url":"https://...","labels":[{"name":"bug"}]}]'
    # Mock gh issue list
    issue_json = '[{"number":2,"title":"Issue 1","state":"OPEN","updatedAt":"2026-03-01T13:00:00Z","url":"https://...","labels":[]}]'
    
    def side_effect(args, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        if "pr" in args:
            mock.stdout = pr_json
        else:
            mock.stdout = issue_json
        return mock

    with patch("subprocess.run", side_effect=side_effect):
        data = fetch_worklist("owner/repo", limit=5)
        
        assert len(data["pull_requests"]) == 1
        assert data["pull_requests"][0]["id"] == 1
        assert data["pull_requests"][0]["labels"] == ["bug"]
        
        assert len(data["issues"]) == 1
        assert data["issues"][0]["id"] == 2
        assert data["issues"][0]["labels"] == []

def test_fetch_worklist_no_gh_command():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RuntimeError, match="gh command not found"):
            fetch_worklist("owner/repo")

from click.testing import CliRunner
from shinko.cli import main

def test_cli_worklist_json(tmp_path):
    config_file = tmp_path / "kuroko.config.yaml"
    config_file.write_text("""
version: 1
projects:
  - name: my-project
    root: /tmp
    repo: owner/repo
""")
    
    def side_effect(args, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        if "pr" in args:
            mock.stdout = '[]'
        else:
            mock.stdout = '[]'
        return mock

    with patch("subprocess.run", side_effect=side_effect):
        runner = CliRunner()
        result = runner.invoke(main, ["--config", str(config_file), "worklist", "--json-output"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["items"][0]["project"] == "my-project"
        assert data["items"][0]["repo"] == "owner/repo"
