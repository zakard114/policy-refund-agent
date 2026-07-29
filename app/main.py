"""CLI entry: question → search → LLM answer."""

from __future__ import annotations

import argparse
import sys

from app.llm import answer_question


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _configure_stdout()
    parser = argparse.ArgumentParser(
        prog="python -m app.main",
        description="Ask the Zakard Shop policy & refund agent (RAG).",
    )
    parser.add_argument(
        "question",
        nargs="+",
        help='Customer question, e.g. "How can I get a refund?"',
    )
    parser.add_argument(
        "-n",
        "--num-results",
        type=int,
        default=3,
        help="Number of policy sections to retrieve (default: 3)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Print only the answer text",
    )
    args = parser.parse_args(argv)
    question = " ".join(args.question).strip()
    if not question:
        parser.error("question must not be empty")

    result = answer_question(question, num_results=args.num_results)

    if args.quiet:
        print(result.answer)
        return 0

    print(f"question: {question}")
    if result.search_query and result.search_query != question:
        print(f"search_query: {result.search_query}")
    if result.language:
        print(f"language: {result.language}")
    print(f"model: {result.model}")
    print(
        f"tokens: {result.prompt_tokens}+{result.completion_tokens} "
        f"({result.elapsed_time:.2f}s)"
    )
    print(f"\nanswer:\n{result.answer}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
