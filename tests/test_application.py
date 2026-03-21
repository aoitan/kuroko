import warnings
from pathlib import Path
from unittest.mock import patch

from kuroko.application import build_report_text, build_shinko_context, parse_report_args
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
