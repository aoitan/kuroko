import json
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from shinko.cli import main

def test_shinko_cli_options():
    runner = CliRunner()
    with runner.isolated_filesystem():
        report_file = Path("report.md")
        report_file.write_text("# Status\n| project | status |\n| --- | --- |\n| kuroko | active |", encoding="utf-8")
        
        # Test default (normal mode)
        with patch("shinko.cli.LLMClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.chat_completion.return_value = "Normal suggestion"
            
            result = runner.invoke(main, ["insight", "--input-file", "report.md", "--json-output"])
            assert result.exit_code == 0
            
            messages = mock_client.chat_completion.call_args[0][0]
            assert "expert developer assistant" in messages[0]["content"]
            assert "Normal suggestion" in result.output

        # Test rescue mode
        with patch("shinko.cli.LLMClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.chat_completion.return_value = "Rescue suggestion"
            
            result = runner.invoke(main, ["insight", "--input-file", "report.md", "--mode", "rescue", "--json-output"])
            # This should fail if --mode is not implemented
            assert result.exit_code == 0
            
            messages = mock_client.chat_completion.call_args[0][0]
            assert "stale" in messages[0]["content"]
            assert "Rescue suggestion" in result.output

        # Test deep mode
        with patch("shinko.cli.LLMClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.chat_completion.return_value = "Deep suggestion"
            
            result = runner.invoke(main, ["insight", "--input-file", "report.md", "--mode", "deep", "--json-output"])
            assert result.exit_code == 0
            
            messages = mock_client.chat_completion.call_args[0][0]
            assert "complex" in messages[0]["content"] or "heavy" in messages[0]["content"]
            assert "Deep suggestion" in result.output

        # Test project option
        with patch("shinko.cli.LLMClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.chat_completion.return_value = "Project suggestion"
            
            result = runner.invoke(main, ["insight", "--input-file", "report.md", "--project", "kuroko", "--json-output"])

            assert result.exit_code == 0
            
            messages = mock_client.chat_completion.call_args[0][0]
            assert "project 'kuroko'" in messages[0]["content"]
            assert "Project suggestion" in result.output
