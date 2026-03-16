import json
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from shinko.cli import main

def test_shinko_with_history_context():
    runner = CliRunner()
    with runner.isolated_filesystem():
        report_file = Path("report.md")
        report_file.write_text("# Status\n| project | status |\n| --- | --- |\n| kuroko | active |", encoding="utf-8")
        
        with patch("shinko.cli.LLMClient") as mock_client_class, \
             patch("kuroko_core.history.HistorySummarizer.get_summary") as mock_summary:
            
            mock_client = mock_client_class.return_value
            mock_client.chat_completion.return_value = "Advised"
            mock_summary.return_value = "You worked on kuroko 3 times recently."
            
            result = runner.invoke(main, ["insight", "--input-file", "report.md", "--json-output"])
            assert result.exit_code == 0
            
            messages = mock_client.chat_completion.call_args[0][0]
            system_msg = messages[0]["content"]
            assert "You worked on kuroko 3 times recently." in system_msg
            assert "Advised" in result.output
