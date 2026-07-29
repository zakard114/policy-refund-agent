"""M2-2 - in-memory Vector RAG (no Qdrant / pgvector).

Offline: embed real policy chunks (TF-IDF over tokens, pure numpy).
Online: embed the user question, rank by cosine similarity, print top context.

Compares keyword (minsearch) vs vector on paraphrase queries.
Done when: see a case where rankings differ, or vector clearly supplies the right context.

Note: TF-IDF is a teaching stand-in for "turn text into numbers".
Neural embeddings (MiniLM, etc.) come later if we need stronger synonyms.
"""

from __future__ import annotations

import math
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

# Windows consoles often use cp949; force UTF-8 so prints do not crash.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Allow `python scripts/m2_2_vector_rag.py` from repo root or from scripts/.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.ingest import load_policies
from app.search import search as keyword_search


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens (simple bag-of-words tokenizer)."""
    return re.findall(r"[a-z0-9]+", text.lower())


def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """
    Same idea as M2-1: (v1 · v2) / (||v1|| * ||v2||).
    Returns 0.0 if either vector has zero length (undefined cosine).
    """
    dot = float(np.dot(v1, v2))
    n1 = float(np.linalg.norm(v1))
    n2 = float(np.linalg.norm(v2))
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    return dot / (n1 * n2)


def chunk_blob(doc: dict) -> str:
    """
    Text we embed for one policy chunk.
    Uses real corpus fields (not the toy vectors from M2-1).
    """
    return " ".join(
        [
            str(doc.get("section") or ""),
            str(doc.get("keywords") or ""),
            str(doc.get("text") or ""),
        ]
    )


def build_tfidf(
    docs_tokens: list[list[str]],
) -> tuple[list[str], np.ndarray, np.ndarray]:
    """
    Offline indexing step.

    1) Build vocab from all chunk tokens.
    2) IDF = rarer terms get higher weight.
    3) Each row = one chunk as a TF-IDF vector, then L2-normalized.
    """
    # Document frequency: how many chunks contain each term.
    df: Counter[str] = Counter()
    for toks in docs_tokens:
        df.update(set(toks))

    vocab = sorted(df.keys())
    if not vocab:
        empty = np.zeros((len(docs_tokens), 0), dtype=np.float64)
        return [], empty, np.zeros(0, dtype=np.float64)

    n_docs = len(docs_tokens)
    # Smoothed IDF so unseen / rare terms stay stable on tiny corpora.
    idf = np.array(
        [math.log((n_docs + 1) / (df[t] + 1)) + 1.0 for t in vocab],
        dtype=np.float64,
    )
    index = {t: i for i, t in enumerate(vocab)}
    matrix = np.zeros((n_docs, len(vocab)), dtype=np.float64)

    for row, toks in enumerate(docs_tokens):
        tf = Counter(toks)
        length = max(len(toks), 1)
        for t, c in tf.items():
            j = index[t]
            # TF = relative frequency inside the chunk; then * IDF.
            matrix[row, j] = (c / length) * idf[j]

    # L2-normalize rows so cosine focuses on direction (like M2-1).
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    matrix = matrix / norms
    return vocab, matrix, idf


def embed_query(text: str, vocab: list[str], idf: np.ndarray) -> np.ndarray:
    """
    Online query embedding.

    Must use the *same* vocab + idf as the offline index
    (do not re-fit IDF on the query alone).
    """
    if not vocab:
        return np.zeros(0, dtype=np.float64)

    tf = Counter(tokenize(text))
    n = max(sum(tf.values()), 1)
    vec = np.zeros(len(vocab), dtype=np.float64)
    index = {t: i for i, t in enumerate(vocab)}
    for t, c in tf.items():
        if t in index:
            j = index[t]
            vec[j] = (c / n) * idf[j]
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec = vec / norm
    return vec


def vector_search(
    query: str,
    docs: list[dict],
    vocab: list[str],
    doc_matrix: np.ndarray,
    idf: np.ndarray,
    top_k: int = 3,
) -> list[tuple[float, dict]]:
    """Embed query, score every chunk with cosine, return top_k hits."""
    q = embed_query(query, vocab, idf)
    scored: list[tuple[float, dict]] = []
    for i, doc in enumerate(docs):
        score = cosine_similarity(q, doc_matrix[i])
        scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


def run_compare(
    label: str,
    query: str,
    docs: list[dict],
    vocab: list[str],
    matrix: np.ndarray,
    idf: np.ndarray,
) -> None:
    """Side-by-side: keyword search vs vector search, then mini RAG context."""
    print(f"\n{'=' * 60}")
    print(f"{label}")
    print(f"Query: {query!r}\n")

    # Baseline already used in the app (Part 1-2 minsearch).
    print("--- Keyword (minsearch) ---")
    kw_hits = keyword_search(query, num_results=3)
    for i, doc in enumerate(kw_hits, 1):
        print(f"  [{i}] {doc.get('section')}")

    # New path for M2-2: dense-ish TF-IDF vectors + cosine.
    print("\n--- Vector (in-memory TF-IDF + cosine) ---")
    vec_hits = vector_search(query, docs, vocab, matrix, idf, top_k=3)
    for i, (score, doc) in enumerate(vec_hits, 1):
        print(f"  [{i}] {doc['section']}  cosine={score:.4f}")

    # Mini RAG: top vector hit becomes the context string we would feed an LLM.
    top_score, top_doc = vec_hits[0]
    print("\n--- Mini RAG context (vector top-1) ---")
    print(f"section: {top_doc['section']}")
    print(f"score:   {top_score:.4f}")
    print(top_doc["text"][:400])
    if len(top_doc["text"]) > 400:
        print("...")

    kw_top = kw_hits[0].get("section") if kw_hits else None
    vec_top = top_doc["section"]
    print("\n--- Check ---")
    print(f"keyword top-1: {kw_top}")
    print(f"vector  top-1: {vec_top}")
    if kw_top != vec_top:
        print("Different top-1: inspect which answer is more useful for the query.")
    else:
        print("Same top-1 for this query; ranking lists above still show the vector path.")


def main() -> None:
    # --- Offline: load real chunks and build the vector index once ---
    docs = load_policies()
    tokens = [tokenize(chunk_blob(d)) for d in docs]
    vocab, matrix, idf = build_tfidf(tokens)

    print(f"Indexed {len(docs)} policy chunks, vocab={len(vocab)}")
    for d in docs:
        print(f"  - {d['section']} ({d['id']})")

    # --- Online demos: embed query + cosine (reuse M2-1 intuition) ---
    run_compare(
        "Case A - change-of-mind / return window",
        "What's the window to return something I regret buying undamaged?",
        docs,
        vocab,
        matrix,
        idf,
    )
    # Few exact policy keywords on purpose (harder for pure keyword matching).
    run_compare(
        "Case B - contact paraphrase (few exact policy keywords)",
        "When can I call you guys about my order?",
        docs,
        vocab,
        matrix,
        idf,
    )


if __name__ == "__main__":
    main()
