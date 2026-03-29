import sqlite3
import os
import pytest
from pathlib import Path
from kuroko_core.db import init_db

def test_init_db_creates_table(tmp_path):
    db_file = tmp_path / "test_kuroko.db"
    conn = init_db(str(db_file))
    
    # Check if table exists
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='source_texts';")
    table = cursor.fetchone()
    assert table is not None
    assert table[0] == 'source_texts'
    
    # Check schema
    cursor.execute("PRAGMA table_info(source_texts);")
    columns = {col[1] for col in cursor.fetchall()}
    expected_columns = {
        'id', 'source_type', 'path', 'directory_context', 
        'raw_text', 'file_hash', 'updated_at', 'imported_at'
    }
    assert expected_columns.issubset(columns)

    # Check if chunks table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chunks';")
    table = cursor.fetchone()
    assert table is not None
    assert table[0] == 'chunks'

    # Check chunks schema
    cursor.execute("PRAGMA table_info(chunks);")
    chunk_columns = {col[1] for col in cursor.fetchall()}
    expected_chunk_columns = {
        'id', 'source_id', 'chunk_index', 'chunk_text', 
        'heading', 'block_timestamp', 'chunk_hash'
    }
    assert expected_chunk_columns.issubset(chunk_columns)

    # Check if index on chunk_hash exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_chunks_hash';")
    assert cursor.fetchone() is not None

    # Check if chunk_embeddings table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chunk_embeddings';")
    table = cursor.fetchone()
    assert table is not None
    assert table[0] == "chunk_embeddings"

    cursor.execute("PRAGMA table_info(chunk_embeddings);")
    embedding_columns = {col[1] for col in cursor.fetchall()}
    expected_embedding_columns = {
        "chunk_id",
        "embedding",
        "embedding_model",
        "embedded_at",
        "chunking_version",
    }
    assert expected_embedding_columns.issubset(embedding_columns)

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_chunk_embeddings_model';"
    )
    assert cursor.fetchone() is not None
    
    conn.close()

def test_init_db_in_memory():
    conn = init_db(":memory:")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='source_texts';")
    assert cursor.fetchone() is not None
    conn.close()

def test_init_db_relative_filename(tmp_path):
    # Change current working directory to tmp_path
    import os
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        # Simple filename in current directory
        conn = init_db("test_simple.db")
        assert Path("test_simple.db").exists()
        conn.close()
    finally:
        os.chdir(old_cwd)

def test_init_db_deep_path(tmp_path):
    # Path with non-existent directories
    db_file = tmp_path / "deep" / "subdir" / "test.db"
    conn = init_db(str(db_file))
    assert db_file.exists()
    conn.close()
