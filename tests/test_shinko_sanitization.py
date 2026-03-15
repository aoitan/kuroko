import pytest
from unittest.mock import patch
from click.testing import CliRunner
import json
import subprocess
from pathlib import Path
from shinko.cli import main

def test_shinko_project_sanitization():
    runner = CliRunner()
    with runner.isolated_filesystem():
        report_file = Path("report.md")
        report_file.write_text("# Status\n| project | status |\n| --- | --- |\n| kuroko | active |", encoding="utf-8")
        
        with patch("shinko.cli.LLMClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.chat_completion.return_value = "Normal suggestion"
            
            # Use a project name with spaces, newlines, and control chars
            malicious_project = "kuroko\n\r;rm -rf /"
            
            result = runner.invoke(main, ["--input-file", "report.md", "--project", malicious_project, "--json-output"])
            assert result.exit_code == 0
            
            messages = mock_client.chat_completion.call_args[0][0]
            system_msg = messages[0]["content"]
            
            # Newlines, spaces, and semicolon should be stripped
            assert "kurokorm-rf" in system_msg
            assert "\n" not in system_msg[system_msg.find("Focus your suggestion on project"):]

