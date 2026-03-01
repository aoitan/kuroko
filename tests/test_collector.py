import pytest
from datetime import datetime
from kuroko.collector import collect_checkpoints
from kuroko.config import KurokoConfig, ProjectConfig, DefaultsConfig

# tmp_path フィクスチャを使ってテスト用ディレクトリを作る。
@pytest.fixture
def dummy_workspace(tmp_path):
    # プロジェクトA
    proj_a = tmp_path / "project_a"
    proj_a.mkdir()
    chk_a = proj_a / "checkpoint"
    chk_a.mkdir()
    
    # 2026-02-28 (Issue 1)
    file_a1 = chk_a / "2026-02-28__project_a__ISSUE-1.md"
    file_a1.write_text("""# Timeline
- 10:00 [coding] act: did A
  block: なし
""")

    # 2026-03-01 (misc)
    file_a2 = chk_a / "2026-03-01__project_a__misc.md"
    file_a2.write_text("""# Timeline
- 09:00 [fix] act: fixed A
  block: none
""")

    # プロジェクトB
    proj_b = tmp_path / "project_b"
    proj_b.mkdir()
    chk_b = proj_b / "checkpoint"
    chk_b.mkdir()
    
    # 2026-02-25 (Issue 2)
    file_b1 = chk_b / "2026-02-25__project_b__ISSUE-2.md"
    file_b1.write_text("""# Timeline
- 11:00 [planning] act: planning B
  block: blocked!
""")

    cfg = KurokoConfig(
        projects=[
            ProjectConfig(name="project_a", root=str(proj_a)),
            ProjectConfig(name="project_b", root=str(proj_b)),
        ],
        defaults=DefaultsConfig(per_project_files=5)
    )
    return cfg


def test_collector_no_filter(dummy_workspace):
    entries = collect_checkpoints(dummy_workspace)
    assert len(entries) == 3
    # 最新順ソートの確認: 03-01 -> 02-28 -> 02-25
    assert entries[0]["date"] == "2026-03-01"
    assert entries[1]["date"] == "2026-02-28"
    assert entries[2]["date"] == "2026-02-25"


def test_collector_filter_since(dummy_workspace):
    entries = collect_checkpoints(dummy_workspace, since="2026-02-28")
    assert len(entries) == 2
    assert all(e["date"] >= "2026-02-28" for e in entries)


def test_collector_filter_until(dummy_workspace):
    entries = collect_checkpoints(dummy_workspace, until="2026-02-28")
    assert len(entries) == 2
    assert all(e["date"] <= "2026-02-28" for e in entries)


def test_collector_filter_projects(dummy_workspace):
    entries = collect_checkpoints(dummy_workspace, projects=["project_b"])
    assert len(entries) == 1
    assert entries[0]["project"] == "project_b"


def test_collector_filter_issue(dummy_workspace):
    entries = collect_checkpoints(dummy_workspace, issue="1")
    assert len(entries) == 1
    assert entries[0]["issue"] == "1"
