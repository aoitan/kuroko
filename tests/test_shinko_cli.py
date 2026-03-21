import json
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from shinko.cli import main
from kuroko_core.db import init_db

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


def test_shinko_uses_db_chunk_context_when_available(tmp_path):
    runner = CliRunner()
    report_file = tmp_path / "report.md"
    report_file.write_text("Rendered report text", encoding="utf-8")

    project_root = tmp_path / "proj"
    project_root.mkdir()
    db_path = tmp_path / "kuroko.db"
    config_path = tmp_path / "kuroko.config.yaml"
    config_path.write_text(
        f"""
version: 1
db_path: {db_path}
projects:
  - name: kuroko
    root: {project_root}
""".strip(),
        encoding="utf-8",
    )

    conn = init_db(str(db_path))
    cursor = conn.cursor()
    memo_path = project_root / "memo.md"
    cursor.execute(
        """
        INSERT INTO source_texts (source_type, path, directory_context, raw_text, file_hash)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("memo", str(memo_path), "proj", "raw memo text", "hash-1"),
    )
    source_id = cursor.lastrowid
    cursor.execute(
        """
        INSERT INTO chunks (source_id, chunk_index, chunk_text, heading, block_timestamp, chunk_hash)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (source_id, 0, "db chunk text", "Daily", "2026-03-22 10:00", "chunk-hash-1"),
    )
    conn.commit()
    conn.close()

    with patch("shinko.cli.LLMClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.chat_completion.return_value = "DB-based suggestion"

        result = runner.invoke(
            main,
            ["--config", str(config_path), "insight", "--input-file", str(report_file), "--project", "kuroko", "--json-output"],
        )

    assert result.exit_code == 0
    messages = mock_client.chat_completion.call_args[0][0]
    assert "db chunk text" in messages[1]["content"]
    assert "raw memo text" in messages[1]["content"]
    assert "Rendered report text" not in messages[1]["content"]


def test_shinko_can_run_without_report_file_when_db_context_exists(tmp_path):
    runner = CliRunner()
    project_root = tmp_path / "proj"
    project_root.mkdir()
    db_path = tmp_path / "kuroko.db"
    config_path = tmp_path / "kuroko.config.yaml"
    config_path.write_text(
        f"""
version: 1
db_path: {db_path}
projects:
  - name: kuroko
    root: {project_root}
""".strip(),
        encoding="utf-8",
    )

    conn = init_db(str(db_path))
    cursor = conn.cursor()
    memo_path = project_root / "memo.md"
    cursor.execute(
        """
        INSERT INTO source_texts (source_type, path, directory_context, raw_text, file_hash)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("memo", str(memo_path), "proj", "memo only context", "hash-2"),
    )
    conn.commit()
    conn.close()

    with patch("shinko.cli.LLMClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.chat_completion.return_value = "DB-only suggestion"

        result = runner.invoke(
            main,
            ["--config", str(config_path), "insight", "--project", "kuroko", "--json-output"],
        )

    assert result.exit_code == 0
    messages = mock_client.chat_completion.call_args[0][0]
    assert "memo only context" in messages[1]["content"]
