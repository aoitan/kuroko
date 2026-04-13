import warnings
from pathlib import Path
from unittest.mock import patch

from kuroko.application import (
    build_report_text,
    build_shinko_context,
    build_shinko_insight_payload,
    get_latest_shinko_insights,
    parse_report_args,
    save_shinko_insight_result,
)
from kuroko_core.config import KurokoConfig, ProjectConfig
from kuroko_core.db import init_db


def test_parse_report_args_uses_platform_aware_shlex_split():
    with patch("kuroko.application.shlex.split", return_value=["--project", "kuroko"]) as mock_split:
        with patch("kuroko.application.sys.platform", "win32"):
            parse_report_args('--project "kuroko"')

    assert mock_split.call_args.kwargs["posix"] is False


def test_build_shinko_context_filters_true_project_descendants_only(tmp_path):
    db_path = tmp_path / "kuroko.db"
    project_root = tmp_path / "project1"
    sibling_root = tmp_path / "project10"
    project_root.mkdir()
    sibling_root.mkdir()

    cfg = KurokoConfig(
        db_path=str(db_path),
        projects=[
            ProjectConfig(name="p1", root=str(project_root)),
            ProjectConfig(name="p10", root=str(sibling_root)),
        ],
    )

    conn = init_db(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO source_texts (source_type, path, directory_context, raw_text, file_hash)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("memo", str(project_root / "memo.md"), "project1", "target project memo", "hash-1"),
    )
    cursor.execute(
        """
        INSERT INTO source_texts (source_type, path, directory_context, raw_text, file_hash)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("memo", str(sibling_root / "memo.md"), "project10", "wrong sibling memo", "hash-2"),
    )
    conn.commit()
    conn.close()

    context = build_shinko_context(cfg, tmp_path / "missing-report.md", project="p1")

    assert "target project memo" in context
    assert "wrong sibling memo" not in context


def test_build_report_text_continues_when_worklist_fetch_fails(tmp_path):
    cfg = KurokoConfig(
        projects=[
            ProjectConfig(name="ok", root=str(tmp_path / "ok"), repo="owner/ok"),
            ProjectConfig(name="ng", root=str(tmp_path / "ng"), repo="owner/ng"),
        ]
    )

    def fake_fetch(repo, limit):
        if repo == "owner/ng":
            raise RuntimeError("gh failed")
        return {"repo": repo, "pull_requests": [], "issues": []}

    with patch("kuroko.worklist.fetch_worklist", side_effect=fake_fetch):
        with warnings.catch_warnings(record=True) as captured:
            report = build_report_text(cfg, include_worklist=True)

    assert "### ok (owner/ok)" in report
    assert "owner/ng" not in report
    assert any("Failed to fetch worklist for ng" in str(item.message) for item in captured)


def test_build_shinko_insight_payload_includes_chunks_and_inferences(tmp_path):
    db_path = tmp_path / "kuroko.db"
    project_root = tmp_path / "project1"
    project_root.mkdir()

    cfg = KurokoConfig(
        db_path=str(db_path),
        projects=[ProjectConfig(name="p1", root=str(project_root))],
    )

    conn = init_db(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO source_texts (source_type, path, directory_context, raw_text, file_hash)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("memo", str(project_root / "memo.md"), "project1", "target project memo", "hash-1"),
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
    cursor.execute(
        """
        INSERT INTO inferences (chunk_id, inference_type, content, metadata)
        VALUES (?, ?, ?, ?)
        """,
        (chunk_id, "TODO", "明日までに対応", '{"pattern":"test"}'),
    )
    conn.commit()
    conn.close()

    payload = build_shinko_insight_payload(cfg, project="p1")

    assert payload is not None
    assert payload["project"] == "p1"
    assert payload["generated_from"] == "db"
    assert payload["sources"][0]["raw_text"] == "target project memo"
    assert payload["sources"][0]["chunks"][0]["chunk_text"] == "db chunk text"
    assert payload["sources"][0]["chunks"][0]["inferences"][0]["inference_type"] == "TODO"


def test_build_shinko_insight_payload_hash_changes_when_inference_changes(tmp_path):
    db_path = tmp_path / "kuroko.db"
    project_root = tmp_path / "project1"
    project_root.mkdir()

    cfg = KurokoConfig(
        db_path=str(db_path),
        projects=[ProjectConfig(name="p1", root=str(project_root))],
    )

    conn = init_db(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO source_texts (source_type, path, directory_context, raw_text, file_hash)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("memo", str(project_root / "memo.md"), "project1", "target project memo", "hash-1"),
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
    cursor.execute(
        """
        INSERT INTO inferences (chunk_id, inference_type, content, metadata)
        VALUES (?, ?, ?, ?)
        """,
        (chunk_id, "TODO", "明日までに対応", '{"pattern":"test"}'),
    )
    conn.commit()

    first_payload = build_shinko_insight_payload(cfg, project="p1")

    cursor.execute(
        """
        UPDATE inferences
        SET content = ?, metadata = ?
        WHERE chunk_id = ?
        """,
        ("来週までに対応", '{"pattern":"updated"}', chunk_id),
    )
    conn.commit()
    conn.close()

    second_payload = build_shinko_insight_payload(cfg, project="p1")

    assert first_payload is not None
    assert second_payload is not None
    assert first_payload["source_hash"] != second_payload["source_hash"]


def test_build_shinko_insight_payload_stops_when_char_budget_is_exhausted(tmp_path):
    db_path = tmp_path / "kuroko.db"
    project_root = tmp_path / "project1"
    project_root.mkdir()

    cfg = KurokoConfig(
        db_path=str(db_path),
        projects=[ProjectConfig(name="p1", root=str(project_root))],
    )

    conn = init_db(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO source_texts (source_type, path, directory_context, raw_text, file_hash)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("memo", str(project_root / "memo.md"), "project1", "A" * 12, "hash-1"),
    )
    source_id = cursor.lastrowid
    cursor.execute(
        """
        INSERT INTO chunks (source_id, chunk_index, chunk_text, heading, block_timestamp, chunk_hash)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (source_id, 0, "B" * 8, "Daily", None, "chunk-hash-1"),
    )
    conn.commit()
    conn.close()

    payload = build_shinko_insight_payload(cfg, project="p1", max_chars=5)

    assert payload is not None
    assert payload["truncated"] is True
    assert payload["sources"][0]["raw_text"] == "AAAAA"
    assert payload["sources"][0]["chunks"] == []


def test_save_shinko_insight_result_invalidates_previous_batch(tmp_path):
    db_path = tmp_path / "kuroko.db"
    init_db(str(db_path)).close()

    save_shinko_insight_result(
        str(db_path),
        project="kuroko",
        source_hash="hash-1",
        extractor_version="rule-based-v1",
        model="test-model",
        prompt_version="prompt-v1",
        schema_version="shinko-insight-v1",
        payload_truncated=False,
        records=[
            {
                "kind": "task",
                "summary": "初回の要約",
                "judgements": {
                    "is_todo": True,
                    "is_ongoing": True,
                    "should_review_this_week": False,
                },
                "blocked_reason": None,
                "next_action": "最初の次アクション",
                "confidence": 0.8,
                "evidence": [{"source_id": None, "chunk_id": None, "quote_excerpt": "short"}],
            }
        ],
    )
    save_shinko_insight_result(
        str(db_path),
        project="kuroko",
        source_hash="hash-2",
        extractor_version="rule-based-v1",
        model="test-model",
        prompt_version="prompt-v2",
        schema_version="shinko-insight-v1",
        payload_truncated=True,
        records=[
            {
                "kind": "next_action",
                "summary": "最新の要約",
                "judgements": {
                    "is_todo": True,
                    "is_ongoing": True,
                    "should_review_this_week": True,
                },
                "blocked_reason": None,
                "next_action": "最新の次アクション",
                "confidence": 0.9,
                "evidence": [],
            }
        ],
    )

    insights = get_latest_shinko_insights(str(db_path), project="kuroko")

    assert len(insights) == 1
    assert insights[0]["summary"] == "最新の要約"
    assert insights[0]["source_hash"] == "hash-2"
    assert insights[0]["payload_truncated"] is True
