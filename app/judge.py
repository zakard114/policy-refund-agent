"""LLM-as-judge scoring for generated support answers."""

from __future__ import annotations

import re
from dataclasses import dataclass

JUDGE_SYSTEM_PROMPT = """You are a strict evaluator for Zakard Shop customer-support answers.
Score the assistant reply on a 1-5 integer scale for each criterion:

RELEVANCE: Does the reply directly address the customer's question?
ACCURACY: Does the reply stay faithful to the policy excerpts (no invented rules)?
  For questions that cannot be answered from the excerpts, high Accuracy means the reply
  refuses to invent details and suggests contacting support.
TONE: Is the reply professional, polite, and on-brand for Zakard Shop support?

Scale: 1 = very poor, 3 = acceptable, 5 = excellent.

Reply using exactly this format (no extra commentary):
RELEVANCE: <1-5>
ACCURACY: <1-5>
TONE: <1-5>
COMMENT: <one short sentence>"""


@dataclass
class JudgeScores:
    relevance: int | None = None
    accuracy: int | None = None
    tone: int | None = None
    comment: str = ""
    raw: str = ""

    @property
    def mean(self) -> float | None:
        vals = [v for v in (self.relevance, self.accuracy, self.tone) if v is not None]
        if not vals:
            return None
        return sum(vals) / len(vals)


def parse_judge_response(raw: str) -> JudgeScores:
    scores = JudgeScores(raw=raw.strip())
    for line in raw.splitlines():
        stripped = line.strip()
        upper = stripped.upper()
        if upper.startswith("RELEVANCE:"):
            scores.relevance = _parse_score(stripped.split(":", 1)[1])
        elif upper.startswith("ACCURACY:"):
            scores.accuracy = _parse_score(stripped.split(":", 1)[1])
        elif upper.startswith("TONE:"):
            scores.tone = _parse_score(stripped.split(":", 1)[1])
        elif upper.startswith("COMMENT:"):
            scores.comment = stripped.split(":", 1)[1].strip()
    return scores


def _parse_score(value: str) -> int | None:
    match = re.search(r"[1-5]", value)
    if not match:
        return None
    return int(match.group(0))


def judge_answer(
    *,
    question: str,
    answer: str,
    policy_excerpts: str,
    label: str = "answerable",
) -> JudgeScores:
    """Ask Gemma to score a support answer against policy excerpts."""
    from app.llm import chat

    label_note = (
        "This question is labeled UNANSWERABLE from the policy corpus. "
        "Reward honest refusal; penalize invented policy details."
        if label == "unanswerable"
        else "This question should be answerable from the policy excerpts."
    )
    user = (
        f"{label_note}\n\n"
        f"Customer question:\n{question}\n\n"
        f"Policy excerpts:\n{policy_excerpts}\n\n"
        f"Assistant answer:\n{answer}"
    )
    result = chat(system=JUDGE_SYSTEM_PROMPT, user=user, temperature=0.0)
    return parse_judge_response(result.answer)
