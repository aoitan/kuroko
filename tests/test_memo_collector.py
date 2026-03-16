import os
import sqlite3
import hashlib
from pathlib import Path
from kuroko_core.db import init_db
from kuroko.memo_collector import collect_memo
from kuroko_core.config import ProjectConfig

def test_collect_memo_inserts_new_file(tmp_path):
    # Setup mock project
    project_root = tmp_path / "project"
    project_root.mkdir()
    memo_file = project_root / "memo.md"
    content = "Test memo content"
    memo_file.write_text(content, encoding="utf-8")
    
    # Setup mock DB
    db_conn = init_db(":memory:")
    
    config = ProjectConfig(name="test_proj", root=str(project_root))
    
    # Run collector
    new_count, updated_count = collect_memo(config, db_conn)
    
    assert new_count == 1
    assert updated_count == 0
    
    # Verify DB content
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, path, raw_text, file_hash FROM source_texts")
    row = cursor.fetchone()
    assert row is not None
    source_id = row[0]
    assert row[1] == str(memo_file)
    assert row[2] == content
    assert row[3] == hashlib.sha256(content.encode("utf-8")).hexdigest()
    
    # Verify chunks
    cursor.execute("SELECT source_id, chunk_index, chunk_text FROM chunks WHERE source_id = ?", (source_id,))
    chunk_row = cursor.fetchone()
    assert chunk_row is not None
    assert chunk_row[0] == source_id
    assert chunk_row[1] == 0
    assert chunk_row[2] == content

    db_conn.close()

def test_collect_memo_updates_chunks(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    memo_file = project_root / "memo.md"
    memo_file.write_text("Block 1\n\nBlock 2", encoding="utf-8")
    
    db_conn = init_db(":memory:")
    config = ProjectConfig(name="test_proj", root=str(project_root))
    
    # First run
    collect_memo(config, db_conn)
    
    cursor = db_conn.cursor()
    cursor.execute("SELECT id FROM source_texts")
    source_id = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM chunks WHERE source_id = ?", (source_id,))
    assert cursor.fetchone()[0] == 2
    
    # Update content (only 1 block)
    memo_file.write_text("Single block", encoding="utf-8")
    
    # Second run
    collect_memo(config, db_conn)
    
    # Verify chunks are replaced
    cursor.execute("SELECT COUNT(*) FROM chunks WHERE source_id = ?", (source_id,))
    assert cursor.fetchone()[0] == 1
    
    db_conn.close()

def test_collect_memo_skips_unchanged_file(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    memo_file = project_root / "memo.md"
    content = "Stable content"
    memo_file.write_text(content, encoding="utf-8")
    
    db_conn = init_db(":memory:")
    config = ProjectConfig(name="test_proj", root=str(project_root))
    
    # First run
    collect_memo(config, db_conn)
    
    # Second run
    new_count, updated_count = collect_memo(config, db_conn)
    
    assert new_count == 0
    assert updated_count == 0
    
    db_conn.close()

def test_collect_memo_updates_changed_file(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    memo_file = project_root / "memo.md"
    memo_file.write_text("Old content", encoding="utf-8")
    
    db_conn = init_db(":memory:")
    config = ProjectConfig(name="test_proj", root=str(project_root))
    
    # First run
    collect_memo(config, db_conn)
    
    cursor = db_conn.cursor()
    cursor.execute("SELECT imported_at FROM source_texts")
    imported_at_first = cursor.fetchone()[0]
    
    import time
    time.sleep(1.1)  # Ensure timestamp can change
    
    # Update content
    new_content = "New content"
    memo_file.write_text(new_content, encoding="utf-8")
    
    # Second run
    new_count, updated_count = collect_memo(config, db_conn)
    
    assert new_count == 0
    assert updated_count == 1
    
    # Verify DB content
    cursor.execute("SELECT raw_text, imported_at, updated_at FROM source_texts")
    row = cursor.fetchone()
    assert row[0] == new_content
    assert row[1] == imported_at_first  # MUST be preserved
    assert row[2] > row[1]  # updated_at should be later
    
    db_conn.close()

def test_collect_memo_global_hash_dedup(tmp_path):
    # Two files in different paths but same content
    root1 = tmp_path / "p1"
    root1.mkdir()
    (root1 / "memo.md").write_text("same content")
    
    root2 = tmp_path / "p2"
    root2.mkdir()
    (root2 / "memo.md").write_text("same content")
    
    db_conn = init_db(":memory:")
    
    # First project
    collect_memo(ProjectConfig(name="p1", root=str(root1)), db_conn)
    
    # Second project (should be skipped due to same hash)
    new_count, _ = collect_memo(ProjectConfig(name="p2", root=str(root2)), db_conn)
    
    assert new_count == 0
    
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM source_texts")
    assert cursor.fetchone()[0] == 1
    
    db_conn.close()

def test_collect_memo_updates_even_if_hash_exists_elsewhere(tmp_path):
    # File A has "Content 1"
    root_a = tmp_path / "a"
    root_a.mkdir()
    memo_a = root_a / "memo.md"
    memo_a.write_text("Content 1")
    
    # File B has "Content 2"
    root_b = tmp_path / "b"
    root_b.mkdir()
    memo_b = root_b / "memo.md"
    memo_b.write_text("Content 2")
    
    db_conn = init_db(":memory:")
    
    # Initial collection
    collect_memo(ProjectConfig(name="a", root=str(root_a)), db_conn)
    collect_memo(ProjectConfig(name="b", root=str(root_b)), db_conn)
    
    # Now update File B to have "Content 1" (same as A)
    memo_b.write_text("Content 1")
    
    # Re-collect B
    collect_memo(ProjectConfig(name="b", root=str(root_b)), db_conn)
    
    # Verify DB: File B's raw_text should now be "Content 1"
    cursor = db_conn.cursor()
    cursor.execute("SELECT raw_text FROM source_texts WHERE path = ?", (str(memo_b.absolute()),))
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == "Content 1"
    
    db_conn.close()

def test_collect_memo_recursive(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "subdir").mkdir()
    (project_root / "memo.md").write_text("Root memo")
    (project_root / "subdir" / "memo.md").write_text("Subdir memo")
    
    db_conn = init_db(":memory:")
    config = ProjectConfig(name="test_proj", root=str(project_root))
    
    new_count, _ = collect_memo(config, db_conn)
    assert new_count == 2
    
    db_conn.close()
