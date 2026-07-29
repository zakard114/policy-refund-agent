"""pgvector storage + cosine search for policy chunk embeddings."""

from __future__ import annotations

import logging

import numpy as np
import psycopg

from app.database import _dsn

logger = logging.getLogger(__name__)

TABLE = "policy_chunk_embeddings"


def _to_pgvector(vec: np.ndarray) -> str:
    return "[" + ",".join(f"{float(x):.8f}" for x in vec.tolist()) + "]"


def connect() -> psycopg.Connection:
    return psycopg.connect(_dsn(), connect_timeout=10)


def stored_dim(conn: psycopg.Connection) -> int | None:
    """Return embedding dim if the table has rows; None if missing/empty."""
    exists = conn.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        )
        """,
        (TABLE,),
    ).fetchone()[0]
    if not exists:
        return None
    row = conn.execute(
        f"SELECT vector_dims(embedding) FROM {TABLE} LIMIT 1"
    ).fetchone()
    return int(row[0]) if row else None


def row_count(conn: psycopg.Connection) -> int:
    exists = conn.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        )
        """,
        (TABLE,),
    ).fetchone()[0]
    if not exists:
        return 0
    return int(conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0])


def recreate_schema(conn: psycopg.Connection, dim: int) -> None:
    """Enable pgvector and (re)create the embeddings table for this dim."""
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.execute(f"DROP TABLE IF EXISTS {TABLE}")
    conn.execute(
        f"""
        CREATE TABLE {TABLE} (
            chunk_id   TEXT PRIMARY KEY,
            section    TEXT NOT NULL,
            body       TEXT NOT NULL,
            embedding  vector({dim}) NOT NULL
        )
        """
    )
    conn.commit()


def upsert_chunks(
    conn: psycopg.Connection,
    docs: list[dict],
    matrix: np.ndarray,
) -> None:
    with conn.cursor() as cur:
        for i, doc in enumerate(docs):
            cur.execute(
                f"""
                INSERT INTO {TABLE} (chunk_id, section, body, embedding)
                VALUES (%s, %s, %s, %s::vector)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    section = EXCLUDED.section,
                    body = EXCLUDED.body,
                    embedding = EXCLUDED.embedding
                """,
                (
                    doc["id"],
                    doc["section"],
                    doc["text"],
                    _to_pgvector(matrix[i]),
                ),
            )
    conn.commit()


def search_sql(
    conn: psycopg.Connection,
    query_vec: np.ndarray,
    top_k: int = 3,
) -> list[tuple[str, str, float]]:
    """`<=>` = cosine distance. Similarity ~= 1 - distance for L2-normalized vectors."""
    q = _to_pgvector(query_vec)
    rows = conn.execute(
        f"""
        SELECT
            chunk_id,
            section,
            1 - (embedding <=> %s::vector) AS cosine_sim
        FROM {TABLE}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (q, q, top_k),
    ).fetchall()
    return [(r[0], r[1], float(r[2])) for r in rows]


def ensure_indexed(
    conn: psycopg.Connection,
    docs: list[dict],
    matrix: np.ndarray,
) -> None:
    """Create/refresh vector table when dim or row count does not match corpus."""
    dim = int(matrix.shape[1])
    current = stored_dim(conn)
    n = row_count(conn)
    if current != dim or n != len(docs):
        logger.info(
            "Refreshing %s (stored_dim=%s need=%s rows=%s need=%s)",
            TABLE,
            current,
            dim,
            n,
            len(docs),
        )
        recreate_schema(conn, dim)
        upsert_chunks(conn, docs, matrix)
