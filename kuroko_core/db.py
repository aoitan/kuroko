import sqlite3
import os
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
    
    conn.commit()
    return conn
