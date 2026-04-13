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
    chunk_id = cursor.lastrowid
    conn.commit()
    conn.close()

    with patch("shinko.cli.LLMClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.chat_completion.return_value = json.dumps(
            {
                "schema_version": "shinko-insight-v1",
                "project": "kuroko",
                "records": [
                    {
                        "kind": "next_action",
                        "summary": "DB-based suggestion",
                        "judgements": {
                            "is_todo": True,
                            "is_ongoing": True,
                            "should_review_this_week": True,
                        },
                        "blocked_reason": None,
                        "next_action": "DB-based suggestion",
                        "confidence": 0.9,
                        "evidence": [{"source_id": source_id, "chunk_id": chunk_id, "quote_excerpt": "db chunk text"}],
                    }
                ],
            },
            ensure_ascii=False,
        )

        result = runner.invoke(
            main,
            ["--config", str(config_path), "insight", "--input-file", str(report_file), "--project", "kuroko", "--json-output"],
        )

    assert result.exit_code == 0
    messages = mock_client.chat_completion.call_args[0][0]
    assert '"chunk_text": "db chunk text"' in messages[1]["content"]
    assert '"raw_text": "raw memo text"' in messages[1]["content"]
    assert "Rendered report text" not in messages[1]["content"]
    payload = json.loads(result.output)
    assert payload["schema_version"] == "shinko-insight-v1"
    assert payload["results"][0]["records"][0]["summary"] == "DB-based suggestion"


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
    source_id = cursor.lastrowid
    conn.commit()
    conn.close()

    with patch("shinko.cli.LLMClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.chat_completion.return_value = json.dumps(
            {
                "schema_version": "shinko-insight-v1",
                "project": "kuroko",
                "records": [
                    {
                        "kind": "task",
                        "summary": "DB-only suggestion",
                        "judgements": {
                            "is_todo": True,
                            "is_ongoing": False,
                            "should_review_this_week": False,
                        },
                        "blocked_reason": None,
                        "next_action": "DB-only suggestion",
                        "confidence": 0.7,
                        "evidence": [{"source_id": source_id, "chunk_id": None, "quote_excerpt": "memo only"}],
                    }
                ],
            },
            ensure_ascii=False,
        )

        result = runner.invoke(
            main,
            ["--config", str(config_path), "insight", "--project", "kuroko", "--json-output"],
        )

    assert result.exit_code == 0
    messages = mock_client.chat_completion.call_args[0][0]
    assert '"raw_text": "memo only context"' in messages[1]["content"]


def test_shinko_json_output_uses_legacy_envelope_when_any_result_is_legacy(tmp_path):
    runner = CliRunner()
    report_file = tmp_path / "report.md"
    report_file.write_text("# Status\n| project | status |\n| --- | --- |\n| kuroko | active |", encoding="utf-8")
    config_path = tmp_path / "kuroko.config.yaml"
    config_path.write_text(
        """
version: 1
projects:
  - name: kuroko
    root: .
""".strip(),
        encoding="utf-8",
    )

    with patch("shinko.cli.LLMClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.chat_completion.return_value = '{"suggestion":"legacy suggestion","score":1}'

        result = runner.invoke(
            main,
            ["--config", str(config_path), "insight", "--input-file", str(report_file), "--json-output"],
        )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema_version"] == "legacy-v1"
    assert payload["results"][0]["schema_version"] == "legacy-v1"


def test_shinko_persists_structured_insights(tmp_path):
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
llm:
  model: test-model
""".strip(),
        encoding="utf-8",
    )

    conn = init_db(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO source_texts (source_type, path, directory_context, raw_text, file_hash)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("memo", str(project_root / "memo.md"), "proj", "メモ本文", "hash-1"),
    )
    source_id = cursor.lastrowid
    cursor.execute(
        """
        INSERT INTO chunks (source_id, chunk_index, chunk_text, heading, block_timestamp, chunk_hash)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (source_id, 0, "担当者の返答待ち", "Daily", "2026-03-22 10:00", "chunk-hash-1"),
    )
    chunk_id = cursor.lastrowid
    conn.commit()
    conn.close()

    with patch("shinko.cli.LLMClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.chat_completion.return_value = json.dumps(
            {
                "schema_version": "shinko-insight-v1",
                "project": "kuroko",
                "records": [
                    {
                        "kind": "blocked_reason",
                        "summary": "担当者の返答待ちで停止している",
                        "judgements": {
                            "is_todo": False,
                            "is_ongoing": True,
                            "should_review_this_week": True,
                        },
                        "blocked_reason": "担当者の返答待ち",
                        "next_action": "水曜までに再度 ping する",
                        "confidence": 0.91,
                        "evidence": [{"source_id": source_id, "chunk_id": chunk_id, "quote_excerpt": "返答待ち"}],
                    }
                ],
            },
            ensure_ascii=False,
        )

        result = runner.invoke(main, ["--config", str(config_path), "insight", "--project", "kuroko", "--json-output"])

    assert result.exit_code == 0

    conn = init_db(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT project, kind, blocked_reason, next_action, model FROM shinko_insights")
    row = cursor.fetchone()
    assert row == ("kuroko", "blocked_reason", "担当者の返答待ち", "水曜までに再度 ping する", "test-model")
    cursor.execute("SELECT source_id, chunk_id, quote_excerpt FROM shinko_insight_evidence")
    evidence = cursor.fetchone()
    assert evidence == (source_id, chunk_id, "返答待ち")
    conn.close()
