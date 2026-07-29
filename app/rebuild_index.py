"""Rebuild the policy search index and write a verification manifest.

Used by Kestra flow ``flows/ingest_policy.yaml`` (K-2) and for local smoke checks::

    uv run --no-sync python -m app.rebuild_index
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from app.config import DATA_DIR, POLICY_PATH, retrieval_method
from app.hybrid import rebuild_vector_index, retrieve
from app.ingest import load_policies
from app.search import build_index

MANIFEST_PATH = DATA_DIR / "index_manifest.json"


def _policy_sha256() -> str:
    return hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest()


def rebuild(*, smoke_query: str = "How can I get a refund?") -> dict:
    """Force-rebuild minsearch + pgvector index; persist JSON manifest for Kestra."""
    docs = load_policies()
    if not docs:
        raise SystemExit(f"No policy sections found in {POLICY_PATH}")

    build_index(force=True)
    vector_chunks = 0
    vector_error = None
    try:
        vector_chunks = rebuild_vector_index()
    except Exception as exc:  # noqa: BLE001
        vector_error = str(exc)

    method = retrieval_method()
    hits, used = retrieve(smoke_query, num_results=min(3, len(docs)), method=method)

    manifest = {
        "status": "ok" if vector_error is None else "partial",
        "rebuilt_at": datetime.now(timezone.utc).isoformat(),
        "policy_path": str(POLICY_PATH),
        "policy_sha256": _policy_sha256(),
        "section_count": len(docs),
        "vector_chunks": vector_chunks,
        "vector_error": vector_error,
        "retrieval_method": method,
        "smoke_retrieval_used": used,
        "sections": [{"id": d["id"], "section": d["section"]} for d in docs],
        "smoke_query": smoke_query,
        "smoke_hits": [
            {"id": h.get("id"), "section": h.get("section")} for h in hits
        ],
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    manifest = rebuild()
    print(f"status={manifest['status']}")
    print(f"sections={manifest['section_count']}")
    print(f"vector_chunks={manifest['vector_chunks']}")
    print(f"retrieval={manifest['retrieval_method']} used={manifest['smoke_retrieval_used']}")
    if manifest.get("vector_error"):
        print(f"vector_error={manifest['vector_error']}")
    print(f"policy_sha256={manifest['policy_sha256'][:12]}…")
    print(f"manifest={MANIFEST_PATH}")
    for i, hit in enumerate(manifest["smoke_hits"], 1):
        print(f"  smoke[{i}] {hit['section']}")


if __name__ == "__main__":
    main()
