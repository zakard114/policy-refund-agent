"""Smoke-test Cerebras (and env loading)."""

from __future__ import annotations

from app.llm import chat, get_model


def main() -> None:
    model = get_model()
    result = chat(
        system="You are a concise assistant.",
        user="Reply with exactly: policy-refund-agent LLM OK",
    )
    print(f"backend model: {model}")
    print(f"answer: {result.answer}")
    print(
        f"tokens: {result.prompt_tokens}+{result.completion_tokens} "
        f"({result.elapsed_time:.2f}s)"
    )


if __name__ == "__main__":
    main()
