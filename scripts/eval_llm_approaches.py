"""Compare two LLM answer prompts (rubric: multiple approaches → pick best).

Approach A: minimal grounded prompt
Approach B: production SUPPORT_SYSTEM_PROMPT (structured + safety rules)

Usage:
  python scripts/eval_llm_approaches.py
  python scripts/eval_llm_approaches.py --limit 4
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.env_paths  # noqa: F401
from app.evaluate import load_eval_cases
from app.hybrid import retrieve
from app.judge import judge_answer
from app.llm import SUPPORT_SYSTEM_PROMPT, chat, format_context
from app.query import prepare_search_query

OUT_PATH = ROOT / "data" / "eval_llm_approaches.json"

# Approach A — early / minimal prompt (grounded only)
PROMPT_A = """You are a helpful assistant for Zakard Shop.
Answer using only the policy excerpts. If unsure, say you do not know."""

# Approach B — production prompt (imported)
PROMPT_B = SUPPORT_SYSTEM_PROMPT

# Representative mix: policy FAQ + multilingual + unanswerable/injection
DEFAULT_CASE_IDS = [
    "en_period_deadline",
    "en_process_how",
    "ko_contact_hours",
    "en_unanswerable_shipping",
    "en_injection_ignore_prompt",
]


def _mean(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


def run_one(case: dict, system: str, *, num_results: int = 3) -> dict:
    prepared = prepare_search_query(case["question"])
    hits, method = retrieve(prepared.search_query, num_results=num_results)
    context = format_context(hits)
    user = (
        "Policy excerpts:\n"
        f"{context}\n\n"
        f"Customer question ({prepared.language}): {prepared.original}\n"
        f"Answer in {prepared.language}."
    )
    result = chat(system=system, user=user)
    time.sleep(1.0)
    scores = judge_answer(
        question=prepared.original,
        answer=result.answer,
        policy_excerpts=context,
        label=case.get("label", "answerable"),
    )
    return {
        "case_id": case["id"],
        "label": case.get("label", "answerable"),
        "question": case["question"],
        "retrieval_method": method,
        "answer_preview": (result.answer or "").replace("\n", " ")[:220],
        "judge_relevance": scores.relevance,
        "judge_accuracy": scores.accuracy,
        "judge_tone": scores.tone,
        "judge_mean": scores.mean,
        "judge_comment": scores.comment,
    }


def summarize_rows(rows: list[dict]) -> dict:
    means = [r["judge_mean"] for r in rows if r.get("judge_mean") is not None]
    return {
        "n": len(rows),
        "judge_mean": _mean(means),
        "relevance": _mean([r["judge_relevance"] for r in rows if r.get("judge_relevance") is not None]),
        "accuracy": _mean([r["judge_accuracy"] for r in rows if r.get("judge_accuracy") is not None]),
        "tone": _mean([r["judge_tone"] for r in rows if r.get("judge_tone") is not None]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare LLM prompt approaches A vs B")
    parser.add_argument("--limit", type=int, default=None, help="Use only first N of DEFAULT_CASE_IDS")
    parser.add_argument("--num-results", type=int, default=3)
    args = parser.parse_args()

    by_id = {c["id"]: c for c in load_eval_cases()}
    ids = DEFAULT_CASE_IDS[: args.limit] if args.limit else DEFAULT_CASE_IDS
    cases = [by_id[i] for i in ids if i in by_id]
    if not cases:
        print("No cases found", file=sys.stderr)
        return 1

    print(f"Comparing {len(cases)} cases × 2 prompts…", flush=True)
    rows_a: list[dict] = []
    rows_b: list[dict] = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case['id']} — approach A", flush=True)
        rows_a.append(run_one(case, PROMPT_A, num_results=args.num_results))
        time.sleep(1.0)
        print(f"[{i}/{len(cases)}] {case['id']} — approach B", flush=True)
        rows_b.append(run_one(case, PROMPT_B, num_results=args.num_results))
        time.sleep(1.0)

    sum_a = summarize_rows(rows_a)
    sum_b = summarize_rows(rows_b)
    selected = "B"
    if (sum_a.get("judge_mean") or 0) > (sum_b.get("judge_mean") or 0):
        selected = "A"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": (
            "LLM-as-judge comparison of two system prompts on the same retrieved context. "
            "Same-model judge (Gemma); relative signal only."
        ),
        "approaches": {
            "A": {
                "name": "minimal_grounded",
                "description": "Short grounded-only prompt (early baseline)",
                "summary": sum_a,
                "cases": rows_a,
            },
            "B": {
                "name": "production_support",
                "description": (
                    "Production SUPPORT_SYSTEM_PROMPT: structured bullets, "
                    "refusal rules, jailbreak/OOS safety (app/llm.py)"
                ),
                "summary": sum_b,
                "cases": rows_b,
            },
        },
        "selected": selected,
        "selected_reason": (
            "Higher mean LLM-judge score on the shared case set; "
            "also stronger explicit safety/refusal behavior for unanswerable/injection."
            if selected == "B"
            else "Higher mean LLM-judge score on the shared case set."
        ),
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print()
    print(f"A judge_mean={sum_a.get('judge_mean')}")
    print(f"B judge_mean={sum_b.get('judge_mean')}")
    print(f"selected={selected}")
    print(f"wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
