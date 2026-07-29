"""M2-4 follow-up: 3-way retrieval eval (keyword / vector / hybrid RRF).

Uses the same Hit@K + MRR definitions as app/evaluate.py.
Does not call the LLM (retrieval-only).
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

from app.database import _dsn as app_dsn
from app.evaluate import (
    HIT_KS,
    first_relevant_rank,
    hit_at_k,
    load_eval_cases,
)
from app.ingest import load_policies
from app.query import prepare_search_query
from app.search import search as keyword_search


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_m2 = _load("m2_2_vector_rag", "m2_2_vector_rag.py")
_m3 = _load("m2_3_pgvector", "m2_3_pgvector.py")
_m4 = _load("m2_4_rrf", "m2_4_rrf.py")

tokenize = _m2.tokenize
chunk_blob = _m2.chunk_blob
build_tfidf = _m2.build_tfidf
embed_query = _m2.embed_query
ensure_schema = _m3.ensure_schema
upsert_chunks = _m3.upsert_chunks
search_sql = _m3.search_sql
rrf_fuse = _m4.rrf_fuse
RRF_K = _m4.RRF_K


def _retrieve_ids(
    method: str,
    search_query: str,
    *,
    conn: psycopg.Connection,
    vocab: list,
    idf,
    top_n: int,
) -> list[str]:
    if method == "keyword":
        hits = keyword_search(search_query, num_results=top_n)
        return [str(h.get("id") or "") for h in hits if h.get("id")]

    qvec = embed_query(search_query, vocab, idf)
    vec_rows = search_sql(conn, qvec, top_k=top_n)
    vec_ids = [chunk_id for chunk_id, _s, _sim in vec_rows]

    if method == "vector":
        return vec_ids

    # hybrid = RRF(keyword ranks, vector ranks)
    kw_ids = [str(h.get("id") or "") for h in keyword_search(search_query, num_results=top_n)]
    fused = rrf_fuse([kw_ids, vec_ids], k=RRF_K)
    return [doc_id for doc_id, _score in fused[:top_n]]


def _aggregate(cases_metrics: list[dict]) -> dict[str, float]:
    """Mean Hit@K and MRR over answerable cases with gold ids."""
    n = len(cases_metrics)
    if n == 0:
        return {f"hit@{k}": 0.0 for k in HIT_KS} | {"mrr": 0.0, "n": 0}

    out: dict[str, float] = {"n": float(n)}
    for k in HIT_KS:
        out[f"hit@{k}"] = sum(1.0 for m in cases_metrics if m[f"hit@{k}"]) / n
    out["mrr"] = sum(m["rr"] for m in cases_metrics) / n
    return out


def main() -> None:
    cases = [c for c in load_eval_cases() if c.get("label", "answerable") == "answerable"]
    cases = [c for c in cases if c.get("expected_section_ids")]
    top_n = max(HIT_KS)

    docs = load_policies()
    tokens = [tokenize(chunk_blob(d)) for d in docs]
    vocab, matrix, idf = build_tfidf(tokens)
    dim = int(matrix.shape[1])

    methods = ("keyword", "vector", "hybrid")
    per_method: dict[str, list[dict]] = {m: [] for m in methods}

    dsn = app_dsn()
    print(f"DB: {dsn.split('@')[-1]}")
    print(f"answerable cases: {len(cases)}; top_n={top_n}; RRF k={RRF_K}; dim={dim}")

    with psycopg.connect(dsn, connect_timeout=10) as conn:
        ensure_schema(conn, dim)
        upsert_chunks(conn, docs, matrix)

        for i, case in enumerate(cases, start=1):
            case_id = case.get("id", f"case_{i}")
            question = case["question"]
            expected = case["expected_section_ids"]
            prepared = prepare_search_query(question)
            sq = prepared.search_query
            print(f"... [{i}/{len(cases)}] {case_id}", flush=True)

            for method in methods:
                ids = _retrieve_ids(
                    method,
                    sq,
                    conn=conn,
                    vocab=vocab,
                    idf=idf,
                    top_n=top_n,
                )
                rank = first_relevant_rank(expected, ids)
                row = {
                    "hit@1": hit_at_k(rank, 1),
                    "hit@3": hit_at_k(rank, 3),
                    "hit@5": hit_at_k(rank, 5),
                    "rr": 0.0 if rank is None else 1.0 / rank,
                }
                per_method[method].append(row)

    # --- 3-way summary table ---
    print("\n=== 3-way retrieval eval (answerable only) ===")
    header = f"{'method':<10} {'n':>4} {'Hit@1':>8} {'Hit@3':>8} {'Hit@5':>8} {'MRR':>8}"
    print(header)
    print("-" * len(header))
    summary = {}
    for method in methods:
        agg = _aggregate(per_method[method])
        summary[method] = agg
        print(
            f"{method:<10} {int(agg['n']):>4} "
            f"{agg['hit@1']:>8.3f} {agg['hit@3']:>8.3f} {agg['hit@5']:>8.3f} {agg['mrr']:>8.3f}"
        )

    # Pick best by MRR then Hit@1/3/5; detect full tie (eval saturation)
    key = lambda m: (
        summary[m]["mrr"],
        summary[m]["hit@1"],
        summary[m]["hit@3"],
        summary[m]["hit@5"],
    )
    best = max(methods, key=key)
    tied = [m for m in methods if key(m) == key(best)]
    if len(tied) > 1:
        print(
            f"\nTie on all metrics ({', '.join(tied)}). "
            "Eval set saturated — prefer hybrid (RRF) for Module-2 resilience "
            "(Case B in m2_4_rrf.py); keyword stays ZoomCamp lexical baseline."
        )
    else:
        print(f"\nBest by MRR (then Hit@1/3/5): {best}")
    print("Next: wire chosen method into app/llm.py answer_question when ready.")


if __name__ == "__main__":
    main()
