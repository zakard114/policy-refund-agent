"""TF-IDF embeddings (teaching stand-in for neural embeds). Shared by hybrid search."""

from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens (simple bag-of-words tokenizer)."""
    return re.findall(r"[a-z0-9]+", text.lower())


def chunk_blob(doc: dict) -> str:
    """Text we embed for one policy chunk."""
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
    Offline indexing: vocab + IDF + L2-normalized TF-IDF matrix (one row per chunk).
    """
    df: Counter[str] = Counter()
    for toks in docs_tokens:
        df.update(set(toks))

    vocab = sorted(df.keys())
    if not vocab:
        empty = np.zeros((len(docs_tokens), 0), dtype=np.float64)
        return [], empty, np.zeros(0, dtype=np.float64)

    n_docs = len(docs_tokens)
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
            matrix[row, j] = (c / length) * idf[j]

    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    matrix = matrix / norms
    return vocab, matrix, idf


def embed_query(text: str, vocab: list[str], idf: np.ndarray) -> np.ndarray:
    """Online query embedding using the same vocab + idf as the offline index."""
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
