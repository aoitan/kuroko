import hashlib
import json
import math
from typing import Iterable, List, Optional

from kuroko_core.config import EmbeddingConfig


class HashEmbeddingClient:
    """Deterministic local embedder for tests and offline operation."""

    def __init__(self, model: str = "hash-v1", dimensions: int = 8):
        if dimensions < 1 or dimensions > 16:
            raise ValueError("dimensions must be between 1 and 16")
        self.model = model
        self.dimensions = dimensions

    def embed_texts(self, texts: Iterable[str]) -> List[List[float]]:
        return [self._embed_single(text) for text in texts]

    def _embed_single(self, text: str) -> List[float]:
        digest = hashlib.sha256(f"{self.model}:{text}".encode("utf-8")).digest()
        values = []
        for index in range(self.dimensions):
            raw_value = digest[index * 2] << 8 | digest[index * 2 + 1]
            values.append((raw_value / 32767.5) - 1.0)
        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0:
            return [0.0 for _ in values]
        return [value / norm for value in values]


def create_embedding_client(config: Optional[EmbeddingConfig] = None) -> HashEmbeddingClient:
    embedding_config = config or EmbeddingConfig()
    return HashEmbeddingClient(model=embedding_config.model)


def cosine_similarity(left: List[float], right: List[float]) -> float:
    if len(left) != len(right):
        raise ValueError("embedding dimensions must match")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(l * r for l, r in zip(left, right)) / (left_norm * right_norm)


def find_similar_chunks(
    conn,
    *,
    model: str,
    limit: int = 5,
    query_text: Optional[str] = None,
    query_chunk_id: Optional[int] = None,
    chunking_version: Optional[str] = None,
    exclude_self: bool = True,
):
    if query_text is None and query_chunk_id is None:
        raise ValueError("query_text or query_chunk_id is required")

    cursor = conn.cursor()
    effective_chunking_version = chunking_version
    if query_chunk_id is not None:
        params = [query_chunk_id, model]
        version_clause = ""
        if chunking_version is not None:
            version_clause = " AND chunking_version = ?"
            params.append(chunking_version)
        cursor.execute(
            f"""
            SELECT embedding, chunking_version
            FROM chunk_embeddings
            WHERE chunk_id = ? AND embedding_model = ?{version_clause}
            """,
            tuple(params),
        )
        row = cursor.fetchone()
        if row is None:
            return []
        query_embedding = json.loads(row[0])
        effective_chunking_version = row[1]
    else:
        query_embedding = create_embedding_client(EmbeddingConfig(model=model)).embed_texts([query_text])[0]

    params = [model]
    version_clause = ""
    if effective_chunking_version is not None:
        version_clause = " AND ce.chunking_version = ?"
        params.append(effective_chunking_version)
    cursor.execute(
        f"""
        SELECT
            c.id,
            c.chunk_text,
            c.heading,
            c.block_timestamp,
            ce.embedding
        FROM chunks c
        JOIN chunk_embeddings ce ON ce.chunk_id = c.id
        WHERE ce.embedding_model = ?{version_clause}
        """,
        tuple(params),
    )
    rows = cursor.fetchall()

    results = []
    for chunk_id, chunk_text, heading, block_timestamp, embedding_json in rows:
        if exclude_self and query_chunk_id is not None and chunk_id == query_chunk_id:
            continue
        score = cosine_similarity(query_embedding, json.loads(embedding_json))
        results.append(
            {
                "chunk_id": chunk_id,
                "chunk_text": chunk_text,
                "heading": heading,
                "block_timestamp": block_timestamp,
                "score": score,
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:limit]
