from kuroko.reporter import generate_report

def test_generate_report_with_worklist():
    entries = [{
        "date": "2026-03-05", "time": "00:00", "phase": "coding",
        "project": "kuroko", "issue": "6", "act": "Implement integration",
        "evd": "", "block": "なし", "file_path": "..."
    }]
    worklists = [{
        "project": "kuroko",
        "repo": "aoitan/kuroko",
        "pull_requests": [{"id": 8, "title": "PR Title", "state": "OPEN", "updated_at": "...", "url": "...", "labels": []}],
        "issues": []
    }]
    
    report = generate_report(entries, worklists=worklists)
    
    assert "## Worklist" in report
    assert "### kuroko (aoitan/kuroko)" in report
    assert "PR Title" in report
    assert "| #8 |" in report

def test_generate_report_with_unknown_totals():
    entries = []
    worklists = [{
        "project": "kuroko",
        "repo": "aoitan/kuroko",
        "pull_requests": [],
        "issues": [],
        "total_pull_requests": -1,
        "total_issues": -1
    }]
    
    report = generate_report(entries, worklists=worklists)
    assert "Summary: unknown Open PRs (showing latest 0), unknown Open Issues (showing latest 0)" in report

def test_generate_report_without_worklist():
    entries = []
    report = generate_report(entries)
    assert "## Worklist" not in report

from click.testing import CliRunner
from kanpe.cli import main
from unittest.mock import patch

def test_cli_report_include_worklist(tmp_path):
    config_file = tmp_path / "kuroko.config.yaml"
    config_file.write_text("""
version: 1
projects:
  - name: my-project
    root: /tmp
    repo: owner/repo
""")
    output_md = tmp_path / "report.md"
    
    with patch("kuroko.worklist.fetch_worklist") as mock_fetch:
        mock_fetch.return_value = {
            "repo": "owner/repo",
            "pull_requests": [],
            "issues": []
        }
        runner = CliRunner()
        # Should succeed and include a worklist section since --include-worklist is implemented
        result = runner.invoke(main, ["--config", str(config_file), "report", str(output_md), "--include-worklist"])
        assert result.exit_code == 0
        assert "## Worklist" in output_md.read_text()
