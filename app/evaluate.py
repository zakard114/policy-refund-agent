"""Retrieval + generation evaluation: Hit@K, MRR, Fact Pass, LLM Judge."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.config import DATA_DIR, EVAL_PATH
from app.judge import JudgeScores, judge_answer
from app.llm import SUPPORT_SYSTEM_PROMPT, chat, format_context
from app.query import prepare_search_query
from app.search import search

DEFAULT_RESULTS_PATH = DATA_DIR / "eval_results.json"
HIT_KS = (1, 3, 5)


@dataclass
class CaseResult:
    case_id: str
    question: str
    label: str
    search_query: str
    expected_section_ids: list[str] = field(default_factory=list)
    retrieved_ids: list[str] = field(default_factory=list)
    reciprocal_rank: float | None = None
    hit_at: dict[str, bool | None] = field(default_factory=dict)
    facts_passed: bool | None = None
    missing_facts: list[str] = field(default_factory=list)
    answer: str = ""
    judge_relevance: int | None = None
    judge_accuracy: int | None = None
    judge_tone: int | None = None
    judge_mean: float | None = None
    judge_comment: str = ""


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_eval_cases(path: Path = EVAL_PATH) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases", data if isinstance(data, list) else [])
    if not cases:
        msg = f"No eval cases found in {path}"
        raise ValueError(msg)
    return cases


def first_relevant_rank(expected_ids: list[str], retrieved_ids: list[str]) -> int | None:
    """1-based rank of the first expected section, or None if missing."""
    if not expected_ids:
        return None
    for i, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in expected_ids:
            return i
    return None


def hit_at_k(rank: int | None, k: int) -> bool:
    return rank is not None and rank <= k


def facts_in_answer(answer: str, expected_facts: list[str]) -> tuple[bool, list[str]]:
    if not expected_facts:
        return True, []
    answer_lower = answer.lower()
    missing = [fact for fact in expected_facts if fact.lower() not in answer_lower]
    return not missing, missing


def _apply_judge(result: CaseResult, scores: JudgeScores) -> None:
    result.judge_relevance = scores.relevance
    result.judge_accuracy = scores.accuracy
    result.judge_tone = scores.tone
    result.judge_mean = scores.mean
    result.judge_comment = scores.comment


def evaluate_case(
    case: dict,
    *,
    num_results: int,
    retrieval_only: bool,
    case_index: int | None = None,
    case_total: int | None = None,
) -> CaseResult:
    question = case["question"]
    label = case.get("label", "answerable")
    expected_section_ids = case.get("expected_section_ids", [])
    expected_facts = case.get("expected_facts", [])
    case_id = case.get("id", question[:40])

    if case_index is not None and case_total is not None:
        print(f"... [{case_index}/{case_total}] {case_id}", flush=True)

    prepared = prepare_search_query(question)
    results = search(prepared.search_query, num_results=num_results)
    retrieved_ids = [doc.get("id", "") for doc in results]

    rank = first_relevant_rank(expected_section_ids, retrieved_ids)
    hit_map: dict[str, bool | None] = {}
    for k in HIT_KS:
        if label == "unanswerable":
            hit_map[f"@{k}"] = None
        else:
            hit_map[f"@{k}"] = hit_at_k(rank, k)

    reciprocal = None if rank is None else 1.0 / rank
    if label == "unanswerable":
        reciprocal = None

    result = CaseResult(
        case_id=case_id,
        question=question,
        label=label,
        search_query=prepared.search_query,
        expected_section_ids=expected_section_ids,
        retrieved_ids=retrieved_ids,
        reciprocal_rank=reciprocal,
        hit_at=hit_map,
    )

    if retrieval_only:
        return result

    context = format_context(results)
    user = (
        "Policy excerpts:\n"
        f"{context}\n\n"
        f"Customer question ({prepared.language}): {prepared.original}\n"
        f"Answer in {prepared.language}."
    )
    try:
        chat_result = chat(system=SUPPORT_SYSTEM_PROMPT, user=user)
        result.answer = chat_result.answer

        if label != "unanswerable" and expected_facts:
            passed, missing = facts_in_answer(chat_result.answer, expected_facts)
            result.facts_passed = passed
            result.missing_facts = missing

        time.sleep(1.2)  # soften Cerebras queue pressure before judge call
        scores = judge_answer(
            question=prepared.original,
            answer=result.answer,
            policy_excerpts=context,
            label=label,
        )
        _apply_judge(result, scores)
    except Exception as exc:  # noqa: BLE001 — keep batch eval alive on flaky network
        print(f"  ! failed: {type(exc).__name__}: {exc}", flush=True)
        if not result.answer:
            result.answer = f"[eval error] {type(exc).__name__}: {exc}"
    return result


def summarize(results: list[CaseResult]) -> dict:
    answerable = [r for r in results if r.label != "unanswerable"]
    unanswerable = [r for r in results if r.label == "unanswerable"]

    summary: dict = {
        "total_cases": len(results),
        "answerable_cases": len(answerable),
        "unanswerable_cases": len(unanswerable),
        "hit_rate": {},
        "mrr": None,
        "fact_pass_rate": None,
        "llm_judge": None,
    }

    if answerable:
        for k in HIT_KS:
            key = f"@{k}"
            hits = sum(1 for r in answerable if r.hit_at.get(key) is True)
            summary["hit_rate"][key] = {
                "rate": hits / len(answerable),
                "hits": hits,
                "n": len(answerable),
            }
        mrr_all = [
            (r.reciprocal_rank if r.reciprocal_rank is not None else 0.0)
            for r in answerable
        ]
        summary["mrr"] = {
            "score": sum(mrr_all) / len(answerable),
            "n": len(answerable),
        }

    scored = [r for r in answerable if r.facts_passed is not None]
    if scored:
        passed = sum(1 for r in scored if r.facts_passed)
        summary["fact_pass_rate"] = {
            "rate": passed / len(scored),
            "passed": passed,
            "n": len(scored),
        }

    judged = [r for r in results if r.judge_mean is not None]
    if judged:
        def _avg(attr: str) -> float:
            vals = [getattr(r, attr) for r in judged if getattr(r, attr) is not None]
            return sum(vals) / len(vals) if vals else 0.0

        summary["llm_judge"] = {
            "n": len(judged),
            "relevance": _avg("judge_relevance"),
            "accuracy": _avg("judge_accuracy"),
            "tone": _avg("judge_tone"),
            "mean": sum(r.judge_mean for r in judged if r.judge_mean is not None) / len(judged),
            "note": "Same-model judge (Gemma); treat as relative signal, not absolute truth.",
        }

    return summary


def write_results(
    results: list[CaseResult],
    summary: dict,
    *,
    path: Path,
    retrieval_only: bool,
) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "retrieval-only" if retrieval_only else "full",
        "summary": summary,
        "cases": [asdict(r) for r in results],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def print_report(
    results: list[CaseResult],
    summary: dict,
    *,
    retrieval_only: bool,
    results_path: Path | None,
) -> None:
    mode = "retrieval-only" if retrieval_only else "full"
    print("=== Evaluation Report ===")
    print(f"cases: {summary['total_cases']} "
          f"(answerable={summary['answerable_cases']}, "
          f"unanswerable={summary['unanswerable_cases']})")
    print(f"mode: {mode}")
    print()

    for i, result in enumerate(results, 1):
        print(f"[{i}] {result.case_id} ({result.label})")
        print(f"  question: {result.question}")
        print(f"  search_query: {result.search_query}")
        if result.label == "unanswerable":
            print(f"  retrieved_sections: {result.retrieved_ids}")
            print("  note: excluded from Hit@K / MRR (no gold section)")
        else:
            hits = ", ".join(
                f"{k}={result.hit_at.get(k)}" for k in (f"@{x}" for x in HIT_KS)
            )
            rr = result.reciprocal_rank
            rr_s = f"{rr:.3f}" if rr is not None else "0 (miss)"
            print(f"  hits: {hits}")
            print(f"  reciprocal_rank: {rr_s}")
            print(f"  expected: {result.expected_section_ids}")
            print(f"  retrieved: {result.retrieved_ids}")
        if not retrieval_only:
            if result.answer:
                preview = result.answer.replace("\n", " ")
                print(f"  answer: {preview[:140]}{'...' if len(preview) > 140 else ''}")
            if result.facts_passed is not None:
                print(f"  facts_passed: {result.facts_passed}")
                if result.missing_facts:
                    print(f"  missing_facts: {result.missing_facts}")
            if result.judge_mean is not None:
                print(
                    f"  judge: R={result.judge_relevance} "
                    f"A={result.judge_accuracy} T={result.judge_tone} "
                    f"mean={result.judge_mean:.2f}"
                )
                if result.judge_comment:
                    print(f"  judge_comment: {result.judge_comment}")
        print()

    print("--- Summary ---")
    for k in HIT_KS:
        key = f"@{k}"
        block = summary["hit_rate"].get(key)
        if not block:
            continue
        print(
            f"Hit Rate @{k}: {block['rate']:.0%} "
            f"({block['hits']}/{block['n']})"
        )
    if summary["mrr"]:
        mrr = summary["mrr"]
        print(f"MRR: {mrr['score']:.3f} (n={mrr['n']})")
    if summary.get("fact_pass_rate"):
        fp = summary["fact_pass_rate"]
        print(f"Fact Pass Rate: {fp['rate']:.0%} ({fp['passed']}/{fp['n']})")
    if summary.get("llm_judge"):
        j = summary["llm_judge"]
        print(
            f"LLM Judge (1-5): mean={j['mean']:.2f} "
            f"(R={j['relevance']:.2f} A={j['accuracy']:.2f} T={j['tone']:.2f}, n={j['n']})"
        )
        print(f"  note: {j['note']}")
    if results_path:
        print(f"results file: {results_path}")


def run_evaluation(
    *,
    eval_path: Path = EVAL_PATH,
    num_results: int = 5,
    retrieval_only: bool = True,
    limit: int | None = None,
) -> tuple[list[CaseResult], dict]:
    cases = load_eval_cases(eval_path)
    if limit is not None:
        cases = cases[: max(0, limit)]
    total = len(cases)
    results = [
        evaluate_case(
            case,
            num_results=num_results,
            retrieval_only=retrieval_only,
            case_index=i,
            case_total=total,
        )
        for i, case in enumerate(cases, start=1)
    ]
    return results, summarize(results)


def main(argv: list[str] | None = None) -> int:
    _configure_stdout()
    parser = argparse.ArgumentParser(
        prog="python -m app.evaluate",
        description="Evaluate retrieval Hit@K/MRR and optional LLM Judge scores.",
    )
    parser.add_argument("--eval-path", type=Path, default=EVAL_PATH)
    parser.add_argument(
        "-n",
        "--num-results",
        type=int,
        default=5,
        help="Retrieve top-n for Hit@5 (default: 5)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Generate answers + Fact Pass + LLM Judge (slower)",
    )
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="Deprecated alias: retrieval-only is now the default",
    )
    parser.add_argument(
        "--results-path",
        type=Path,
        default=DEFAULT_RESULTS_PATH,
        help=f"Write JSON report (default: {DEFAULT_RESULTS_PATH})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Evaluate only the first N cases (smoke / rate-limit friendly)",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Do not write eval_results.json",
    )
    args = parser.parse_args(argv)

    retrieval_only = not args.full
    results, summary = run_evaluation(
        eval_path=args.eval_path,
        num_results=args.num_results,
        retrieval_only=retrieval_only,
        limit=args.limit,
    )

    results_path = None if args.no_write else args.results_path
    if results_path is not None:
        write_results(results, summary, path=results_path, retrieval_only=retrieval_only)

    print_report(
        results,
        summary,
        retrieval_only=retrieval_only,
        results_path=results_path,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
