"""Part 6-2 smoke: unanswerable + injection safe fallbacks.

Usage:
  python scripts/demo_part_d_safety.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.env_paths  # noqa: F401
from app.llm import answer_question
from app.safety import is_prompt_injection, looks_like_safe_refusal


def main() -> int:
    cases = json.loads((ROOT / "data" / "eval_data.json").read_text(encoding="utf-8"))["cases"]
    targets = [c for c in cases if c.get("label") == "unanswerable"]
    print(f"unanswerable/injection cases: {len(targets)}")
    ok = True
    for case in targets:
        cid = case["id"]
        q = case["question"]
        blocked = is_prompt_injection(q)
        result = answer_question(q, num_results=3)
        safe = looks_like_safe_refusal(result.answer)
        mark = "OK" if safe else "FAIL"
        if not safe:
            ok = False
        print(
            f"[{mark}] {cid} blocked={blocked} method={result.retrieval_method} "
            f"{result.elapsed_time:.1f}s"
        )
        print(f"  Q: {q}")
        print(f"  A: {result.answer[:220].replace(chr(10), ' / ')}")
        print()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
