"""Part 6-1 smoke: mock evaluate_refund decisions (+ optional LLM agent).

Usage:
  python scripts/demo_part_c_tools.py
  python scripts/demo_part_c_tools.py --with-llm
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.env_paths  # noqa: F401
from app.tools import evaluate_refund, list_demo_order_ids, lookup_order


DEMO_CASES = [
    ("ZK-1001", "eligible"),
    ("ZK-1002", "ineligible"),
    ("ZK-1003", "need_more_info"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Part C / 6-1 tools demo")
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="Also call answer_with_agent for ZK-1001 (needs API key)",
    )
    args = parser.parse_args()

    print("Demo order ids:", ", ".join(list_demo_order_ids()))
    print()
    ok = True
    for order_id, expected in DEMO_CASES:
        decision = evaluate_refund(order_id)
        got = decision.get("decision")
        mark = "OK" if got == expected else "FAIL"
        if got != expected:
            ok = False
        print(f"[{mark}] {order_id} → {got} (want {expected})")
        print(f"  reasons: {decision.get('reasons')}")
        print(f"  lookup: {json.dumps(lookup_order(order_id).get('order', {}), ensure_ascii=False)}")
        print()

    if args.with_llm:
        from app.agent import answer_with_agent

        q = "Can I get a refund for order ZK-1001? Change of mind."
        print("--- LLM agent ---")
        print("Q:", q)
        result = answer_with_agent(q)
        print(f"method={result.retrieval_method} tools={result.search_query} {result.elapsed_time:.1f}s")
        print(result.answer[:500])
        print()

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
