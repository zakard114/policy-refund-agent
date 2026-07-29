"""Hybrid retrieval: keyword (minsearch) + vector (pgvector) fused with RRF."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

import numpy as np

from app.ingest import load_policies
from app import pgvector_store
from app.search import search as keyword_search
from app.tfidf import build_tfidf, chunk_blob, embed_query, tokenize

logger = logging.getLogger(__name__)

RRF_K = 60  # Cormack et al. / common RAG default


@dataclass
class _VectorIndex:
    docs: list[dict]
    docs_by_id: dict[str, dict]
    vocab: list[str]
    idf: np.ndarray
    matrix: np.ndarray


_lock = threading.Lock()
_index: _VectorIndex | None = None


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
            if not doc_id:
                continue
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def _build_local_index(*, force: bool = False) -> _VectorIndex:
    global _index
    with _lock:
        if _index is not None and not force:
            return _index
        docs = load_policies()
        tokens = [tokenize(chunk_blob(d)) for d in docs]
        vocab, matrix, idf = build_tfidf(tokens)
        _index = _VectorIndex(
            docs=docs,
            docs_by_id={str(d["id"]): d for d in docs},
            vocab=vocab,
            idf=idf,
            matrix=matrix,
        )
        return _index


def rebuild_vector_index() -> int:
    """Offline: rebuild TF-IDF + upsert into pgvector. Returns chunk count."""
    idx = _build_local_index(force=True)
    with pgvector_store.connect() as conn:
        pgvector_store.ensure_indexed(conn, idx.docs, idx.matrix)
    return len(idx.docs)


def _local_vector_ids(query: str, idx: _VectorIndex, top_k: int) -> list[str]:
    """Cosine rank over the in-memory TF-IDF matrix (no Postgres required)."""
    qvec = embed_query(query, idx.vocab, idx.idf)
    if qvec.size == 0 or idx.matrix.size == 0:
        return []
    sims = idx.matrix @ qvec
    order = np.argsort(-sims)[:top_k]
    return [str(idx.docs[i]["id"]) for i in order]


def _pgvector_ids(query: str, idx: _VectorIndex, top_k: int) -> list[str] | None:
    """Return ranked ids from pgvector, or None if DB/pgvector is unavailable."""
    try:
        qvec = embed_query(query, idx.vocab, idx.idf)
        with pgvector_store.connect() as conn:
            pgvector_store.ensure_indexed(conn, idx.docs, idx.matrix)
            vec_rows = pgvector_store.search_sql(conn, qvec, top_k=top_k)
        return [chunk_id for chunk_id, _section, _sim in vec_rows]
    except Exception as exc:  # noqa: BLE001 — cloud / no-DB environments
        logger.info("pgvector unavailable (%s); using local TF-IDF vector ranks", exc)
        return None


def hybrid_search(
    query: str,
    num_results: int = 3,
    *,
    candidate_n: int | None = None,
    rrf_k: int = RRF_K,
) -> list[dict]:
    """
    Online hybrid retrieval.

    keyword ranks ∥ vector ranks → RRF → top ``num_results`` full policy docs
    (same shape as ``app.search.search`` hits).

    Prefers pgvector when available; otherwise uses in-memory TF-IDF ranks
    (Streamlit Cloud / no Postgres).
    """
    idx = _build_local_index()
    pool = candidate_n or max(num_results * 2, len(idx.docs))

    kw_hits = keyword_search(query, num_results=pool)
    kw_ids = [str(h.get("id") or "") for h in kw_hits if h.get("id")]

    vec_ids = _pgvector_ids(query, idx, pool)
    if vec_ids is None:
        vec_ids = _local_vector_ids(query, idx, pool)

    fused = rrf_fuse([kw_ids, vec_ids], k=rrf_k)
    out: list[dict] = []
    for doc_id, score in fused:
        doc = idx.docs_by_id.get(doc_id)
        if doc is None:
            continue
        hit = dict(doc)
        hit["rrf_score"] = score
        out.append(hit)
        if len(out) >= num_results:
            break
    return out


def retrieve(
    query: str,
    num_results: int = 3,
    *,
    method: str = "hybrid",
) -> tuple[list[dict], str]:
    """
    Unified retrieval entry for the app.

    Returns (hits, method_used). Falls back to keyword if hybrid/vector fails.
    """
    method = (method or "hybrid").lower().strip()
    if method == "keyword":
        return keyword_search(query, num_results=num_results), "keyword"

    try:
        if method == "vector":
            idx = _build_local_index()
            vec_ids = _pgvector_ids(query, idx, num_results)
            if vec_ids is None:
                vec_ids = _local_vector_ids(query, idx, num_results)
                used = "vector-local"
            else:
                used = "vector"
            hits = []
            qvec = embed_query(query, idx.vocab, idx.idf)
            sims = idx.matrix @ qvec if qvec.size and idx.matrix.size else None
            id_to_row = {str(d["id"]): i for i, d in enumerate(idx.docs)}
            for chunk_id in vec_ids:
                doc = idx.docs_by_id.get(chunk_id)
                if doc is None:
                    continue
                hit = dict(doc)
                if sims is not None and chunk_id in id_to_row:
                    hit["cosine_sim"] = float(sims[id_to_row[chunk_id]])
                hits.append(hit)
            return hits, used

        # default: hybrid (pgvector or local TF-IDF + keyword RRF)
        return hybrid_search(query, num_results=num_results), "hybrid"
    except Exception as exc:  # noqa: BLE001 — keep Q&A up if retrieval path fails
        logger.warning("Retrieval method=%s failed (%s); falling back to keyword", method, exc)
        return keyword_search(query, num_results=num_results), "keyword"
