"""M2-3 - store chunk vectors in pra-postgres (pgvector) and search with SQL.

Why: M2-2 kept vectors in Python RAM. Real services store + search in the DB.
What: upsert policy chunk embeddings into a `vector` column, query top-k with cosine.
How: reuse M2-2 TF-IDF (teaching embedder) + pgvector operator `<=>` (cosine distance).

Note on operators (pgvector):
  <->  L2 distance
  <#>  negative inner product
  <=>  cosine distance   <-- we use this (ORDER BY ASC = most similar)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import psycopg

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_SCRIPTS = Path(__file__).resolve().parent
_ROOT = _SCRIPTS.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.database import _dsn  # same .env DSN as the app (pra @ :5435)
from app.ingest import load_policies

# Load M2-2 helpers without making scripts/ a package.
_spec = importlib.util.spec_from_file_location(
    "m2_2_vector_rag",
    _SCRIPTS / "m2_2_vector_rag.py",
)
_m2 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_m2)

tokenize = _m2.tokenize
chunk_blob = _m2.chunk_blob
build_tfidf = _m2.build_tfidf
embed_query = _m2.embed_query


def _to_pgvector(vec: np.ndarray) -> str:
    """Format a numpy vector as pgvector text input: '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{float(x):.8f}" for x in vec.tolist()) + "]"


def ensure_schema(conn: psycopg.Connection, dim: int) -> None:
    """Enable pgvector and (re)create the embeddings table for this dim."""
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # Recreate when dim changes (TF-IDF vocab size is not fixed forever).
    conn.execute("DROP TABLE IF EXISTS policy_chunk_embeddings")
    conn.execute(
        f"""
        CREATE TABLE policy_chunk_embeddings (
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
    """Insert one row per policy chunk (offline indexing into Postgres)."""
    with conn.cursor() as cur:
        for i, doc in enumerate(docs):
            cur.execute(
                """
                INSERT INTO policy_chunk_embeddings (chunk_id, section, body, embedding)
                VALUES (%s, %s, %s, %s::vector)
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
    """
    Online search inside Postgres.

    `<=>` = cosine distance. Similarity ~= 1 - distance for normalized vectors.
    """
    q = _to_pgvector(query_vec)
    rows = conn.execute(
        """
        SELECT
            chunk_id,
            section,
            1 - (embedding <=> %s::vector) AS cosine_sim
        FROM policy_chunk_embeddings
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (q, q, top_k),
    ).fetchall()
    return [(r[0], r[1], float(r[2])) for r in rows]


def main() -> None:
    docs = load_policies()
    tokens = [tokenize(chunk_blob(d)) for d in docs]
    vocab, matrix, idf = build_tfidf(tokens)
    dim = int(matrix.shape[1])
    if dim == 0:
        raise SystemExit("Empty TF-IDF matrix - no tokens in policy chunks.")

    dsn = _dsn()
    print(f"DB: {dsn.split('@')[-1]}")  # host:port/db only (no password)
    print(f"Chunks: {len(docs)}, embedding dim: {dim} (TF-IDF vocab)")

    with psycopg.connect(dsn, connect_timeout=10) as conn:
        # --- Offline: write vectors into pra-postgres ---
        ensure_schema(conn, dim)
        upsert_chunks(conn, docs, matrix)
        n = conn.execute("SELECT COUNT(*) FROM policy_chunk_embeddings").fetchone()[0]
        print(f"Stored rows in policy_chunk_embeddings: {n}")

        # --- Online: SQL cosine search (Done when for M2-3) ---
        query = "What's the window to return something I regret buying undamaged?"
        qvec = embed_query(query, vocab, idf)
        print(f"\nQuery: {query!r}")
        print("Top-k via pgvector (ORDER BY embedding <=> query):")
        for i, (chunk_id, section, sim) in enumerate(search_sql(conn, qvec, top_k=3), 1):
            print(f"  [{i}] {section}  id={chunk_id}  cosine_sim={sim:.4f}")

        top = search_sql(conn, qvec, top_k=1)[0]
        print("\nM2-3 check: DB top-k search OK" if top else "\nM2-3 check: FAILED")
        print(f"top-1 section: {top[1]}")


if __name__ == "__main__":
    main()
