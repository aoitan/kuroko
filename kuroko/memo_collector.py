import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from kuroko.chunker import chunk_text
from kuroko.inference import InferenceEngine
from kuroko_core.config import EmbeddingConfig, ProjectConfig
from kuroko_core.embeddings import create_embedding_client

def calculate_hash(content: str) -> str:
    """Calculates the SHA-256 hash of the content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _fetch_chunks_for_source(cursor, source_id: int) -> List[Dict]:
    cursor.execute(
        """
        SELECT id, chunk_index, chunk_text, heading, block_timestamp, chunk_hash
        FROM chunks
        WHERE source_id = ?
        ORDER BY chunk_index ASC, id ASC
        """,
        (source_id,),
    )
    rows = cursor.fetchall()
    return [
        {
            "id": row[0],
            "chunk_index": row[1],
            "chunk_text": row[2],
            "heading": row[3],
            "block_timestamp": row[4],
            "chunk_hash": row[5],
        }
        for row in rows
    ]


def _pop_matching_chunk(existing_chunks: List[Dict], chunk: Dict) -> Optional[Dict]:
    for index, existing in enumerate(existing_chunks):
        if existing["chunk_index"] == chunk["chunk_index"] and existing["chunk_hash"] == chunk["chunk_hash"]:
            return existing_chunks.pop(index)
    for index, existing in enumerate(existing_chunks):
        if existing["chunk_hash"] == chunk["chunk_hash"]:
            return existing_chunks.pop(index)
    return None


def save_chunks(cursor, source_id, raw_text):
    """Sync chunks for a source while preserving IDs for unchanged content."""
    existing_chunks = _fetch_chunks_for_source(cursor, source_id)
    next_chunks = chunk_text(raw_text)

    current_chunks = []
    changed_chunk_ids = set()

    for chunk in next_chunks:
        matched = _pop_matching_chunk(existing_chunks, chunk)
        if matched:
            cursor.execute(
                """
                UPDATE chunks
                SET chunk_index = ?, chunk_text = ?, heading = ?, block_timestamp = ?, chunk_hash = ?
                WHERE id = ?
                """,
                (
                    chunk["chunk_index"],
                    chunk["chunk_text"],
                    chunk["heading"],
                    chunk["block_timestamp"],
                    chunk["chunk_hash"],
                    matched["id"],
                ),
            )
            current_chunks.append({"id": matched["id"], **chunk})
            continue

        cursor.execute(
            """
            INSERT INTO chunks (source_id, chunk_index, chunk_text, heading, block_timestamp, chunk_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                chunk["chunk_index"],
                chunk["chunk_text"],
                chunk["heading"],
                chunk["block_timestamp"],
                chunk["chunk_hash"],
            ),
        )
        chunk_id = cursor.lastrowid
        current_chunks.append({"id": chunk_id, **chunk})
        changed_chunk_ids.add(chunk_id)

    for stale_chunk in existing_chunks:
        cursor.execute("DELETE FROM chunks WHERE id = ?", (stale_chunk["id"],))

    return current_chunks, changed_chunk_ids


def save_inferences(cursor, chunks: Iterable[Dict], changed_chunk_ids: Set[int]):
    """Extract and save rule-based inferences for the given chunks."""
    engine = InferenceEngine()

    chunk_list = list(chunks)
    if not chunk_list:
        return

    target_chunk_ids = set(changed_chunk_ids)
    if not target_chunk_ids:
        target_chunk_ids = {chunk["id"] for chunk in chunk_list}
    else:
        placeholders = ", ".join("?" for _ in chunk_list)
        cursor.execute(
            f"""
            SELECT c.id
            FROM chunks c
            LEFT JOIN inferences i ON i.chunk_id = c.id
            WHERE c.id IN ({placeholders})
            GROUP BY c.id
            HAVING COUNT(i.id) = 0
            """,
            tuple(chunk["id"] for chunk in chunk_list),
        )
        target_chunk_ids.update(row[0] for row in cursor.fetchall())

    for chunk in chunk_list:
        if chunk["id"] not in target_chunk_ids:
            continue

        base_date = None
        if chunk.get("block_timestamp"):
            try:
                base_date = datetime.fromisoformat(chunk["block_timestamp"])
            except ValueError:
                pass

        results = engine.extract(chunk["chunk_text"], base_date=base_date)

        savepoint_name = f"save_inferences_chunk_{chunk['id']}"
        cursor.execute(f"SAVEPOINT {savepoint_name}")
        try:
            cursor.execute("DELETE FROM inferences WHERE chunk_id = ?", (chunk["id"],))
            for res in results:
                cursor.execute(
                    """
                    INSERT INTO inferences (chunk_id, inference_type, content, metadata)
                    VALUES (?, ?, ?, ?)
                    """,
                    (chunk["id"], res.inference_type, res.content, res.metadata)
                )
        except Exception:
            cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            raise
        finally:
            cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")


def re_inference_all(db_conn):
    """Re-run inference for all chunks in the database."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, chunk_text, block_timestamp FROM chunks")
    rows = cursor.fetchall()

    chunks = [
        {
            "id": row[0],
            "chunk_text": row[1],
            "block_timestamp": row[2]
        }
        for row in rows
    ]

    for chunk in chunks:
        base_date = None
        if chunk.get("block_timestamp"):
            try:
                base_date = datetime.fromisoformat(chunk["block_timestamp"])
            except ValueError:
                pass

        results = InferenceEngine().extract(chunk["chunk_text"], base_date=base_date)
        cursor.execute("DELETE FROM inferences WHERE chunk_id = ?", (chunk["id"],))
        for res in results:
            cursor.execute(
                """
                INSERT INTO inferences (chunk_id, inference_type, content, metadata)
                VALUES (?, ?, ?, ?)
                """,
                (chunk["id"], res.inference_type, res.content, res.metadata)
            )
    db_conn.commit()


def sync_chunk_embeddings(
    cursor,
    chunks: Iterable[Dict],
    changed_chunk_ids: Set[int],
    embedding_config: Optional[EmbeddingConfig] = None,
):
    embedding_cfg = embedding_config or EmbeddingConfig()
    chunk_list = list(chunks)
    if not chunk_list:
        return

    placeholders = ", ".join("?" for _ in chunk_list)
    chunk_ids = [chunk["id"] for chunk in chunk_list]
    cursor.execute(
        f"""
        SELECT chunk_id, embedding_model, chunking_version
        FROM chunk_embeddings
        WHERE chunk_id IN ({placeholders})
        """,
        tuple(chunk_ids),
    )
    existing_embeddings = {
        row[0]: {"embedding_model": row[1], "chunking_version": row[2]}
        for row in cursor.fetchall()
    }

    target_chunks = []
    for chunk in chunk_list:
        record = existing_embeddings.get(chunk["id"])
        if chunk["id"] in changed_chunk_ids or record is None:
            target_chunks.append(chunk)
            continue
        if record["embedding_model"] != embedding_cfg.model:
            target_chunks.append(chunk)
            continue
        if record["chunking_version"] != embedding_cfg.chunking_version:
            target_chunks.append(chunk)

    if not target_chunks:
        return

    client = create_embedding_client(embedding_cfg)
    vectors = client.embed_texts([chunk["chunk_text"] for chunk in target_chunks])
    for chunk, vector in zip(target_chunks, vectors):
        cursor.execute(
            """
            INSERT INTO chunk_embeddings (chunk_id, embedding, embedding_model, embedded_at, chunking_version)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET
                embedding = excluded.embedding,
                embedding_model = excluded.embedding_model,
                embedded_at = CURRENT_TIMESTAMP,
                chunking_version = excluded.chunking_version
            """,
            (
                chunk["id"],
                json.dumps(vector),
                embedding_cfg.model,
                embedding_cfg.chunking_version,
            ),
        )


def collect_memo(
    project: ProjectConfig,
    db_conn,
    embedding_config: Optional[EmbeddingConfig] = None,
):
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
                current_chunks = _fetch_chunks_for_source(cursor, db_id)
                sync_chunk_embeddings(cursor, current_chunks, set(), embedding_config=embedding_config)
                continue
                
            # Content changed, update it
            cursor.execute("""
            UPDATE source_texts 
            SET raw_text = ?, file_hash = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (raw_text, file_hash, db_id))
            
            # Update chunks (with error handling)
            try:
                current_chunks, changed_chunk_ids = save_chunks(cursor, db_id, raw_text)
                save_inferences(cursor, current_chunks, changed_chunk_ids)
                sync_chunk_embeddings(
                    cursor,
                    current_chunks,
                    changed_chunk_ids,
                    embedding_config=embedding_config,
                )
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
                current_chunks, changed_chunk_ids = save_chunks(cursor, source_id, raw_text)
                save_inferences(cursor, current_chunks, changed_chunk_ids)
                sync_chunk_embeddings(
                    cursor,
                    current_chunks,
                    changed_chunk_ids,
                    embedding_config=embedding_config,
                )
            except Exception as e:
                # TODO: Log error
                pass
            
            new_count += 1
            
    db_conn.commit()
    return new_count, updated_count
