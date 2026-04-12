import json
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from kanpe.cli import invoke_shinko

def test_invoke_shinko_success():
    report_path = Path("report.md")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"suggestion": "Try harder."}),
            stderr=""
        )
        
        suggestion = invoke_shinko("shinko", report_path)
        assert suggestion == "Try harder."
        
        # Verify call (defaults to sys.executable -m shinko.cli when cmd is "shinko")
        args, kwargs = mock_run.call_args
        assert "--json-output" in args[0]
        assert str(report_path) in args[0]


def test_invoke_shinko_prefers_structured_records_for_results():
    report_path = Path("report.md")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "schema_version": "shinko-insight-v1",
                    "results": [
                        {
                            "project": "kuroko",
                            "score": 91,
                            "suggestion": "- legacy suggestion",
                            "records": [
                                {
                                    "kind": "next_action",
                                    "summary": "依頼先に確認する",
                                    "judgements": {
                                        "is_todo": True,
                                        "is_ongoing": True,
                                        "should_review_this_week": True,
                                    },
                                    "next_action": "担当者へ連絡する",
                                    "blocked_reason": "先方回答待ち",
                                }
                            ],
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            stderr="",
        )

        suggestion = invoke_shinko("shinko", report_path)

    assert "#### kuroko (Score: 91)" in suggestion
    assert "`next_action` [TODO / 継続 / 今週確認]: 依頼先に確認する" in suggestion
    assert "next action: 担当者へ連絡する" in suggestion
    assert "blocked: 先方回答待ち" in suggestion
    assert "legacy suggestion" not in suggestion

def test_invoke_shinko_custom_cmd():
    report_path = Path("report.md")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"suggestion": "Custom."}),
            stderr=""
        )
        
        suggestion = invoke_shinko("/usr/local/bin/shinko --some-opt", report_path)
        assert suggestion == "Custom."
        
        args, kwargs = mock_run.call_args
        assert args[0][0] == "/usr/local/bin/shinko"
        assert "--some-opt" in args[0]

def test_invoke_shinko_with_mode_and_project():
    report_path = Path("report.md")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"suggestion": "Targeted suggestion"}),
            stderr=""
        )
        
        suggestion = invoke_shinko("shinko", report_path, mode="rescue", project="kuroko")
        assert suggestion == "Targeted suggestion"
        
        args, kwargs = mock_run.call_args
        assert "--mode" in args[0]
        assert "rescue" in args[0]
        assert "--project" in args[0]
        assert "kuroko" in args[0]

def test_invoke_shinko_with_lang():
    report_path = Path("report.md")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"suggestion": "Localized suggestion"}),
            stderr=""
        )
        
        # Test Chinese
        suggestion = invoke_shinko("shinko", report_path, lang="Chinese")
        assert suggestion == "Localized suggestion"
        
        args, kwargs = mock_run.call_args
        assert "--lang" in args[0]
        assert "Chinese" in args[0]
        
        # Test Japanese
        invoke_shinko("shinko", report_path, lang="Japanese")
        args, kwargs = mock_run.call_args
        assert "--lang" in args[0]
        assert "Japanese" in args[0]

def test_invoke_shinko_file_not_found():
    report_path = Path("report.md")
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RuntimeError, match="shinko command not found"):
            invoke_shinko("nonexistent-cmd", report_path)

def test_invoke_shinko_timeout():
    report_path = Path("report.md")
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["shinko"], timeout=60)):
        with pytest.raises(RuntimeError, match="shinko command timed out"):
            invoke_shinko("shinko", report_path)

def test_invoke_shinko_error_exit():
    report_path = Path("report.md")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Critical error"
        )
        
        with pytest.raises(RuntimeError, match="shinko command failed"):
            invoke_shinko("shinko", report_path)

def test_invoke_shinko_invalid_json():
    report_path = Path("report.md")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Not JSON at all",
            stderr=""
        )
        
        with pytest.raises(RuntimeError, match="Failed to parse shinko output as JSON"):
            invoke_shinko("shinko", report_path)

def test_invoke_shinko_custom_timeout():
    report_path = Path("report.md")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"suggestion": "Delayed success"}),
            stderr=""
        )
        
        invoke_shinko("shinko", report_path, timeout=300)
        
        args, kwargs = mock_run.call_args
        assert kwargs["timeout"] == 300
