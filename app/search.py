"""Keyword search over policy sections (minsearch)."""

from __future__ import annotations

from minsearch import Index

from app.config import search_boost
from app.ingest import load_policies

# Prefer section/keywords over long overlapping body text.
DEFAULT_BOOST = search_boost()

_index: Index | None = None


def build_index(*, force: bool = False) -> Index:
    """Load policy chunks and fit a minsearch text index (cached)."""
    global _index
    if _index is not None and not force:
        return _index

    docs = load_policies()
    index = Index(
        text_fields=["section", "keywords", "text"],
        keyword_fields=[],
    )
    index.fit(docs)
    _index = index
    return index


def search(query: str, num_results: int = 3, boost_dict: dict | None = None):
    """Return top matching policy sections for ``query``."""
    index = build_index()
    return index.search(
        query,
        num_results=num_results,
        boost_dict=boost_dict or DEFAULT_BOOST,
    )


if __name__ == "__main__":
    query = "When is the refund deadline?"
    results = search(query)
    print(f"query: {query}")
    print(f"docs indexed: {len(load_policies())}")
    print(f"hits: {len(results)}")
    for i, doc in enumerate(results, 1):
        print(f"\n[{i}] section={doc.get('section')!r}")
        print(f"    id={doc.get('id')!r}")
        text = (doc.get("text") or "").replace("\n", " ")
        print(f"    text={text[:160]!r}")
