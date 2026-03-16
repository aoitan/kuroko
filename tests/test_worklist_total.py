from unittest.mock import patch, MagicMock, call
from kuroko.worklist import fetch_worklist

def test_fetch_worklist_with_totals():
    # Mock data for list and total count queries
    list_json = '[]'
    total_count = "123"
    
    def side_effect(args, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        if "api" in args:
            mock.stdout = total_count
        else:
            mock.stdout = list_json
        return mock

    with patch("subprocess.run", side_effect=side_effect) as mock_run:
        data = fetch_worklist("owner/repo", limit=5)
        
        assert data["total_pull_requests"] == 123
        assert data["total_issues"] == 123
        
        # Verify gh api was called with search query
        api_calls = [c for c in mock_run.call_args_list if "api" in c.args[0]]
        assert len(api_calls) == 2
        # Check that the query is passed as a separate argument following -f
        # cmd = ["gh", "api", "search/issues", "-f", "q=...", "-f", "per_page=1", "--jq", ".total_count"]
        # So we look for the argument after "-f"
        combined_args = " ".join(api_calls[0].args[0])
        assert "q=repo:owner/repo is:open is:pr" in combined_args

def test_fetch_worklist_fallback_on_error():
    # If search fails, it should fallback to list size
    from subprocess import CalledProcessError
    def side_effect(args, **kwargs):
        if "api" in args:
            raise CalledProcessError(1, args, stderr="API Error")
        
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = '[{"number":1,"title":"T","state":"OPEN","updatedAt":"...","url":"...","labels":[]}]'
        return mock

    with patch("subprocess.run", side_effect=side_effect):
        data = fetch_worklist("owner/repo", limit=5)
        # Should return -1 (unknown) instead of falling back to list length
        assert data["total_pull_requests"] == -1

from click.testing import CliRunner
from shinko.cli import main

def test_cli_worklist_shows_totals(tmp_path):
    config_file = tmp_path / "kuroko.config.yaml"
    config_file.write_text("""
version: 1
projects:
  - name: my-project
    root: /tmp
    repo: owner/repo
""")
    
    mock_data = {
        "repo": "owner/repo",
        "pull_requests": [{"id": 1, "title": "T", "state": "OPEN", "updated_at": "...", "url": "...", "labels": []}],
        "issues": [],
        "total_pull_requests": 10,
        "total_issues": 5,
        "project": "my-project"
    }
    
    with patch("kuroko.worklist.fetch_worklist", return_value=mock_data):
        runner = CliRunner()
        result = runner.invoke(main, ["--config", str(config_file), "worklist"])
        assert result.exit_code == 0
        assert "Summary: 10 Open PRs, 5 Open Issues" in result.output

def test_cli_worklist_shows_unknown_totals(tmp_path):
    config_file = tmp_path / "kuroko.config.yaml"
    config_file.write_text("""
version: 1
projects:
  - name: my-project
    root: /tmp
    repo: owner/repo
""")
    
    mock_data = {
        "repo": "owner/repo",
        "pull_requests": [],
        "issues": [],
        "total_pull_requests": -1,
        "total_issues": -1,
        "project": "my-project"
    }
    
    with patch("kuroko.worklist.fetch_worklist", return_value=mock_data):
        runner = CliRunner()
        result = runner.invoke(main, ["--config", str(config_file), "worklist"])
        assert result.exit_code == 0
        assert "Summary: unknown Open PRs, unknown Open Issues" in result.output
