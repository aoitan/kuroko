import json

import pytest

from kuroko_core.db import init_db
from kuroko_core.embeddings import HashEmbeddingClient, cosine_similarity, find_similar_chunks


def test_hash_embedding_client_is_deterministic():
    client = HashEmbeddingClient(model="hash-v1")

    first = client.embed_texts(["same text"])[0]
    second = client.embed_texts(["same text"])[0]
    third = client.embed_texts(["different text"])[0]

    assert first == second
    assert first != third


def test_hash_embedding_client_rejects_unsupported_dimensions():
    with pytest.raises(ValueError, match="dimensions must be between 1 and 16"):
        HashEmbeddingClient(model="hash-v1", dimensions=17)


def test_cosine_similarity_rejects_mismatched_dimensions():
    with pytest.raises(ValueError, match="embedding dimensions must match"):
        cosine_similarity([1.0, 0.0], [1.0])


def test_find_similar_chunks_orders_by_similarity():
    conn = init_db(":memory:")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO source_texts (source_type, path, directory_context, raw_text, file_hash)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("memo", "/tmp/memo.md", "tmp", "raw", "hash-source"),
    )
    source_id = cursor.lastrowid

    chunks = [
        (source_id, 0, "origin", None, None, "hash-1"),
        (source_id, 1, "near", None, None, "hash-2"),
        (source_id, 2, "far", None, None, "hash-3"),
    ]
    chunk_ids = []
    for chunk in chunks:
        cursor.execute(
            """
            INSERT INTO chunks (source_id, chunk_index, chunk_text, heading, block_timestamp, chunk_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            chunk,
        )
        chunk_ids.append(cursor.lastrowid)

    embeddings = {
        chunk_ids[0]: [1.0, 0.0],
        chunk_ids[1]: [0.8, 0.2],
        chunk_ids[2]: [-1.0, 0.0],
    }
    for chunk_id, vector in embeddings.items():
        cursor.execute(
            """
            INSERT INTO chunk_embeddings (chunk_id, embedding, embedding_model, chunking_version)
            VALUES (?, ?, ?, ?)
            """,
            (chunk_id, json.dumps(vector), "test-model", "1"),
        )

    cursor.execute(
        """
        INSERT INTO chunks (source_id, chunk_index, chunk_text, heading, block_timestamp, chunk_hash)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (source_id, 3, "other version", None, None, "hash-4"),
    )
    other_version_chunk_id = cursor.lastrowid
    cursor.execute(
        """
        INSERT INTO chunk_embeddings (chunk_id, embedding, embedding_model, chunking_version)
        VALUES (?, ?, ?, ?)
        """,
        (other_version_chunk_id, json.dumps([0.99, 0.01]), "test-model", "2"),
    )

    conn.commit()

    results = find_similar_chunks(
        conn,
        query_chunk_id=chunk_ids[0],
        model="test-model",
        limit=2,
        exclude_self=True,
    )

    assert [item["chunk_id"] for item in results] == [chunk_ids[1], chunk_ids[2]]
    assert results[0]["score"] > results[1]["score"]

    conn.close()
