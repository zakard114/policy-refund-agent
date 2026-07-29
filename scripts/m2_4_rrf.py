"""M2-4 - Reciprocal Rank Fusion (keyword + pgvector ranks).

Flow (online):
  query
    -> keyword ranks (minsearch)
    -> vector ranks  (pgvector cosine distance <=>)
    -> RRF merge
    -> final top chunks (= hybrid shortlist / context candidates)

RRF (Cormack et al.):
  score(d) = sum over rankings R of  1 / (k + rank_R(d))
  rank is 1-based; k is typically 60.

Done when (roadmap): 3-way table keyword / vector / hybrid(RRF) for sample queries.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import psycopg

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_SCRIPTS = Path(__file__).resolve().parent
_ROOT = _SCRIPTS.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.ingest import load_policies
from app.search import search as keyword_search

# --- load M2-2 / M2-3 helpers ---
def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_m2 = _load("m2_2_vector_rag", "m2_2_vector_rag.py")
_m3 = _load("m2_3_pgvector", "m2_3_pgvector.py")

tokenize = _m2.tokenize
chunk_blob = _m2.chunk_blob
build_tfidf = _m2.build_tfidf
embed_query = _m2.embed_query

from app.database import _dsn as app_dsn

ensure_schema = _m3.ensure_schema
upsert_chunks = _m3.upsert_chunks
search_sql = _m3.search_sql


RRF_K = 60  # standard constant from the RRF paper / common RAG practice


def rrf_fuse(
    ranked_lists: list[list[str]],
    *,
    k: int = RRF_K,
) -> list[tuple[str, float]]:
    """
    Merge multiple ranked id lists.

    ranked_lists[i] = [id_at_rank1, id_at_rank2, ...]  (best first)
    Returns [(id, rrf_score), ...] sorted by score desc.
    """
    scores: dict[str, float] = {}
    for ranking in ranked_lists:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def keyword_ranks(query: str, top_n: int = 4) -> list[str]:
    """Return chunk ids in keyword rank order (best first)."""
    hits = keyword_search(query, num_results=top_n)
    return [str(h.get("id") or "") for h in hits if h.get("id")]


def vector_ranks(
    conn: psycopg.Connection,
    query: str,
    vocab: list,
    idf,
    top_n: int = 4,
) -> list[str]:
    """Return chunk ids in pgvector cosine rank order (best first)."""
    qvec = embed_query(query, vocab, idf)
    rows = search_sql(conn, qvec, top_k=top_n)
    return [chunk_id for chunk_id, _section, _sim in rows]


def section_by_id(docs: list[dict]) -> dict[str, str]:
    return {d["id"]: d["section"] for d in docs}


def run_case(
    label: str,
    query: str,
    docs: list[dict],
    conn: psycopg.Connection,
    vocab: list,
    idf,
) -> None:
    id_to_section = section_by_id(docs)
    kw = keyword_ranks(query, top_n=len(docs))
    vec = vector_ranks(conn, query, vocab, idf, top_n=len(docs))
    hybrid = rrf_fuse([kw, vec], k=RRF_K)

    def fmt(ids: list[str]) -> str:
        if not ids:
            return "(none)"
        top = ids[0]
        return f"{id_to_section.get(top, top)} [{top}]"

    print(f"\n{'=' * 64}")
    print(label)
    print(f"Query: {query!r}\n")
    print(f"{'method':<10} {'top-1 section':<40} ranks (ids)")
    print("-" * 64)
    print(f"{'keyword':<10} {fmt(kw):<40} {kw}")
    print(f"{'vector':<10} {fmt(vec):<40} {vec}")
    hybrid_ids = [doc_id for doc_id, _ in hybrid]
    print(f"{'hybrid':<10} {fmt(hybrid_ids):<40} {hybrid_ids}")
    print("\nRRF scores (k=60):")
    for doc_id, score in hybrid:
        print(f"  {score:.6f}  {id_to_section.get(doc_id, doc_id)}")


def main() -> None:
    docs = load_policies()
    tokens = [tokenize(chunk_blob(d)) for d in docs]
    vocab, matrix, idf = build_tfidf(tokens)
    dim = int(matrix.shape[1])

    dsn = app_dsn()
    print(f"DB: {dsn.split('@')[-1]}")
    print(f"RRF k={RRF_K}; chunks={len(docs)}; dim={dim}")

    with psycopg.connect(dsn, connect_timeout=10) as conn:
        # Refresh vector index so ranks match current TF-IDF (same as M2-3).
        ensure_schema(conn, dim)
        upsert_chunks(conn, docs, matrix)

        # 3-way cases (roadmap Done when)
        run_case(
            "Case A - change-of-mind / return window",
            "What's the window to return something I regret buying undamaged?",
            docs,
            conn,
            vocab,
            idf,
        )
        run_case(
            "Case B - contact paraphrase",
            "When can I call you guys about my order?",
            docs,
            conn,
            vocab,
            idf,
        )
        run_case(
            "Case C - process how-to",
            "How do I request a refund on My Page?",
            docs,
            conn,
            vocab,
            idf,
        )

    print("\nM2-4 check: keyword + vector ranks fused with RRF (see table above).")


if __name__ == "__main__":
    main()
