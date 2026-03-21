import json
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from shinko.cli import main

def test_shinko_insight_with_lang():
    runner = CliRunner()
    with runner.isolated_filesystem():
        report_file = Path("report.md")
        report_file.write_text("# Status\n| project | status |\n| --- | --- |\n| kuroko | active |", encoding="utf-8")
        
        with patch("shinko.cli.LLMClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.chat_completion.return_value = "English suggestion"
            
            # --lang English を指定
            result = runner.invoke(main, ["insight", "--input-file", "report.md", "--lang", "English", "--json-output"])
            assert result.exit_code == 0
            
            messages = mock_client.chat_completion.call_args[0][0]
            system_msg = messages[0]["content"]
            user_msg = messages[1]["content"]
            # システムプロンプトに "Answer in English." が含まれていることを確認
            assert "Answer in English." in system_msg
            # ユーザーメッセージのラベルを確認
            assert "Current status report:" in user_msg

def test_shinko_insight_with_config_lang():
    runner = CliRunner()
    with runner.isolated_filesystem():
        report_file = Path("report.md")
        report_file.write_text("# Status\n| project | status |\n| --- | --- |\n| kuroko | active |", encoding="utf-8")
        
        config_file = Path("kuroko.config.yaml")
        config_file.write_text("llm:\n  language: Japanese", encoding="utf-8")
        
        with patch("shinko.cli.LLMClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.chat_completion.return_value = "日本語の提案"
            
            # --lang を指定しない（デフォルトは設定ファイルから読み込まれるべき）
            result = runner.invoke(main, ["--config", "kuroko.config.yaml", "insight", "--input-file", "report.md", "--json-output"])
            assert result.exit_code == 0
            
            messages = mock_client.chat_completion.call_args[0][0]
            system_msg = messages[0]["content"]
            user_msg = messages[1]["content"]
            # システムプロンプトに日本語の指示が含まれていることを確認
            assert "必ず日本語で回答してください。" in system_msg
            # ユーザーメッセージのラベルが日本語であることを確認
            assert "現在の進捗レポート:" in user_msg
