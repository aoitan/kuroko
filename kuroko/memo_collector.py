import os
import hashlib
import glob
from pathlib import Path
from datetime import datetime
from kuroko_core.config import ProjectConfig
from kuroko.chunker import chunk_text

def calculate_hash(content: str) -> str:
    """Calculates the SHA-256 hash of the content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def save_chunks(cursor, source_id, raw_text):
    """Chunks the text and saves them to the chunks table."""
    # Delete existing chunks for this source
    cursor.execute("DELETE FROM chunks WHERE source_id = ?", (source_id,))
    
    # Generate and insert new chunks
    chunks = chunk_text(raw_text)
    for chunk in chunks:
        cursor.execute("""
        INSERT INTO chunks (source_id, chunk_index, chunk_text, heading, block_timestamp, chunk_hash)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            source_id,
            chunk["chunk_index"],
            chunk["chunk_text"],
            chunk["heading"],
            chunk["block_timestamp"],
            chunk["chunk_hash"]
        ))

def collect_memo(project: ProjectConfig, db_conn):
    """
    Collects memo.md files from the project root and saves them to the database.
    Returns (new_count, updated_count).
    """
    root_path = Path(project.root).expanduser()
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
            # TODO: Log error or use logging
            continue
            
        file_hash = calculate_hash(raw_text)
        path_str = str(memo_path.absolute())
        
        # 1. Check if the PATH already exists
        cursor.execute("SELECT id, file_hash FROM source_texts WHERE path = ?", (path_str,))
        path_row = cursor.fetchone()
        
        directory_context = memo_path.parent.name
        
        if path_row:
            db_id, db_hash = path_row
            if db_hash == file_hash:
                # Content hasn't changed for this path, skip
                continue
                
            # Content changed, update it
            cursor.execute("""
            UPDATE source_texts 
            SET raw_text = ?, file_hash = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (raw_text, file_hash, db_id))
            
            # Update chunks (with error handling)
            try:
                save_chunks(cursor, db_id, raw_text)
            except Exception as e:
                # TODO: Log error
                pass
            
            updated_count += 1
        else:
            # New path. Now check if EXACT same content (hash) already exists ANYWHERE
            # for global deduplication (as per Phase 1 requirements).
            cursor.execute("SELECT path FROM source_texts WHERE file_hash = ?", (file_hash,))
            hash_row = cursor.fetchone()
            if hash_row:
                # Content already exists in another path. Skip as per current policy.
                continue

            # Truly new path AND new content
            cursor.execute("""
            INSERT INTO source_texts (source_type, path, directory_context, raw_text, file_hash)
            VALUES (?, ?, ?, ?, ?)
            """, ("memo", path_str, directory_context, raw_text, file_hash))
            
            source_id = cursor.lastrowid
            # Save initial chunks
            try:
                save_chunks(cursor, source_id, raw_text)
            except Exception as e:
                # TODO: Log error
                pass
            
            new_count += 1
            
    db_conn.commit()
    return new_count, updated_count
