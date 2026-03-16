import pytest
from pathlib import Path
from kuroko_core.config import KurokoConfig, ProjectConfig
from kuroko_core.db import init_db
from kuroko.collector import collect_checkpoints, save_checkpoints_to_db

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_kuroko.db"
    conn = init_db(str(db_path))
    yield conn, str(db_path)
    conn.close()

def test_save_checkpoints_to_db(temp_db, tmp_path):
    conn, db_path = temp_db
    
    # Setup dummy project and checkpoint
    proj_dir = tmp_path / "proj1"
    cp_dir = proj_dir / "checkpoint"
    cp_dir.mkdir(parents=True)
    cp_file = cp_dir / "2026-03-16__proj1__ISSUE-1.md"
    cp_file.write_text("# Timeline\n\n- 10:00 [coding] act: feat1\n  evd: logs\n  block: none", encoding="utf-8")
    
    config = KurokoConfig(
        projects=[ProjectConfig(name="proj1", root=str(proj_dir))],
        db_path=db_path
    )
    
    # Collect entries
    entries = collect_checkpoints(config)
    assert len(entries) == 1
    
    # Action: Save to DB
    save_checkpoints_to_db(entries, conn)
    
    # Verify
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM source_texts")
    assert cursor.fetchone()[0] == 1
    
    cursor.execute("SELECT count(*) FROM chunks")
    assert cursor.fetchone()[0] == 1
    
    # Verify content
    cursor.execute("SELECT raw_text FROM source_texts")
    assert "feat1" in cursor.fetchone()[0]
