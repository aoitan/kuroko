import sqlite3
from pathlib import Path


def init_db(db_path: str):
    """Initializes the SQLite database and creates the source_texts table."""
    # Expand user if necessary
    if db_path.startswith("~"):
        db_path = str(Path(db_path).expanduser())
        
    # Ensure parent directory exists
    if db_path != ":memory:":
        db_path_obj = Path(db_path)
        if db_path_obj.parent != Path("."):
            db_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
    conn = sqlite3.connect(db_path)
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    
    # Create source_texts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS source_texts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_type TEXT NOT NULL,
        path TEXT NOT NULL UNIQUE,
        directory_context TEXT,
        raw_text TEXT NOT NULL,
        file_hash TEXT NOT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        imported_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create index on file_hash and path for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_source_texts_hash ON source_texts(file_hash)")
    
    # Create chunks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER NOT NULL,
        chunk_index INTEGER NOT NULL,
        chunk_text TEXT NOT NULL,
        heading TEXT,
        block_timestamp TEXT,
        chunk_hash TEXT NOT NULL,
        FOREIGN KEY (source_id) REFERENCES source_texts(id) ON DELETE CASCADE
    )
    """)
    
    # Create index for chunks
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_hash ON chunks(chunk_hash)")

    # Create derived embedding store for chunk similarity lookup
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chunk_embeddings (
        chunk_id INTEGER PRIMARY KEY,
        embedding TEXT NOT NULL,
        embedding_model TEXT NOT NULL,
        embedded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        chunking_version TEXT NOT NULL,
        FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
    )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_model ON chunk_embeddings(embedding_model)"
    )
    
    # Create inferences table for rule-based extraction results
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chunk_id INTEGER NOT NULL,
        inference_type TEXT NOT NULL,
        content TEXT NOT NULL,
        metadata TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inferences_chunk ON inferences(chunk_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inferences_type ON inferences(inference_type)")
    
    conn.commit()
    return conn
