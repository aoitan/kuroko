import os
import hashlib
import glob
from pathlib import Path
from datetime import datetime
from kuroko_core.config import ProjectConfig

def calculate_hash(content: str) -> str:
    """Calculates the SHA-256 hash of the content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def collect_memo(project: ProjectConfig, db_conn):
    """
    Collects memo.md files from the project root and saves them to the database.
    Returns (new_count, updated_count).
    """
    root_path = Path(project.root)
    if not root_path.exists():
        return 0, 0
    
    # Search for memo.md files recursively
    memo_files = list(root_path.glob("**/memo.md"))
    
    new_count = 0
    updated_count = 0
    
    cursor = db_conn.cursor()
    
    for memo_path in memo_files:
        try:
            with open(memo_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
        except Exception as e:
            # TODO: Log error
            continue
            
        file_hash = calculate_hash(raw_text)
        path_str = str(memo_path.absolute())
        
        # 1. Check if EXACT same content (hash) already exists ANYWHERE
        # This fulfills the "prevent re-import of same content" requirement globally.
        cursor.execute("SELECT path FROM source_texts WHERE file_hash = ?", (file_hash,))
        hash_row = cursor.fetchone()
        if hash_row:
            # Content already exists. If it's the SAME path, we just skip (no change).
            # If it's a DIFFERENT path, we also skip (global deduplication).
            continue

        # 2. If content is new, check if the PATH already exists
        cursor.execute("SELECT id, file_hash FROM source_texts WHERE path = ?", (path_str,))
        path_row = cursor.fetchone()
        
        directory_context = memo_path.parent.name
        
        if path_row:
            db_id, db_hash = path_row
            # We already checked global hash above, so if we are here, it means 
            # this path exists but content (hash) has changed.
            cursor.execute("""
            UPDATE source_texts 
            SET raw_text = ?, file_hash = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (raw_text, file_hash, db_id))
            updated_count += 1
        else:
            # New path AND new content
            cursor.execute("""
            INSERT INTO source_texts (source_type, path, directory_context, raw_text, file_hash)
            VALUES (?, ?, ?, ?, ?)
            """, ("memo", path_str, directory_context, raw_text, file_hash))
            new_count += 1
            
    db_conn.commit()
    return new_count, updated_count
