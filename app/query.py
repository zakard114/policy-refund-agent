"""Prepare user questions for English keyword search."""

from __future__ import annotations

import re
from dataclasses import dataclass

PREPARE_SEARCH_SYSTEM = """You prepare customer questions for keyword search over English policy documents.
Policy sections are:
1) Refund Period — deadlines, days after delivery/receipt, change of mind, undamaged returns
2) Non-Refundable Conditions — customer damage, negligence, label/package removal, powered-on electronics
3) Refund Process — how to request, My Page, photos, Customer Service processing time
4) Contact Information — phone number, support hours, 1:1 chat (not the refund steps)

Given a question in any language:
1. Identify the language (English name).
2. Write a short English SEARCH_QUERY with distinctive terms for the MOST LIKELY section.
   Prefer section-specific words over generic "refund" alone.
   Examples:
   - time/deadline/return after delivery → include "refund period" "7 days"
   - damaged myself / powered on / label removed → include "non-refundable" "negligence" or "electronics"
   - how to request / photos / My Page → include "refund process" "Request Refund"
   - phone / hours / chat support → include "contact" "customer service" (do not add "process")

Reply using exactly this format (two lines, no extra text):
LANGUAGE: <language name in English>
SEARCH_QUERY: <English keywords for search>"""

# Rule-based expansions for recurring Top-1 misses (keyword RAG).
_EXPANSION_RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\b(deadline|how many days|time limit|after (delivery|receipt|receiving)"
            r"|change of mind|undamaged|return window)\b",
            re.I,
        ),
        "refund period 7 days",
    ),
    (
        re.compile(
            r"\b(negligence|damaged (the )?product myself|self[- ]?inflicted|"
            r"removed? (the )?label|opened? (the )?package|powered? on|"
            r"electronic device|non[- ]?refundable)\b",
            re.I,
        ),
        "non-refundable conditions negligence electronics",
    ),
    (
        re.compile(
            r"\b(how (can|do) i (get|request)|request refund|my page|"
            r"attach(ed)? photos?|business days|refund process|"
            r"how long|processing time|complete a refund)\b",
            re.I,
        ),
        "refund process Request Refund My Page",
    ),
    (
        re.compile(
            r"\b(phone number|support hours|operating hours|1:1 chat|"
            r"contact information|customer support available|"
            r"when is customer support|customer service phone)\b",
            re.I,
        ),
        "contact information customer service phone hours chat",
    ),
    (
        re.compile(r"\breturn\b.*\b(delivery|delivered|receive|received)\b", re.I),
        "refund period 7 days return",
    ),
]

_EN_MARKERS = re.compile(
    r"\b(the|what|when|where|how|can|do|does|is|are|my|refund|return|"
    r"customer|support|phone|photos?|days?)\b",
    re.I,
)


@dataclass
class PreparedQuery:
    original: str
    language: str
    search_query: str


def expand_search_query(query: str) -> str:
    """Append section-discriminative terms when cues match."""
    extras: list[str] = []
    for pattern, hint in _EXPANSION_RULES:
        if pattern.search(query):
            extras.append(hint)
    if not extras:
        return query

    tokens = query.split()
    seen = {token.lower() for token in tokens}
    for extra in extras:
        for token in extra.split():
            key = token.lower()
            if key not in seen:
                tokens.append(token)
                seen.add(key)
    return " ".join(tokens)


def _looks_english(text: str) -> bool:
    """Skip LLM only for English-like ASCII (not unaccented French/Spanish)."""
    if not text or any(ord(ch) >= 128 for ch in text):
        return False
    return bool(_EN_MARKERS.search(text))


def _guess_language(question: str) -> str:
    if re.search(r"[\uac00-\ud7a3]", question or ""):
        return "Korean"
    if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", question or ""):
        return "Japanese"
    if _looks_english(question):
        return "English"
    return "English"


def prepare_search_query(question: str, *, use_llm: bool = True) -> PreparedQuery:
    """Detect language and produce an English query for minsearch.

    ``use_llm=False`` skips the rewrite LLM (retrieval-only / no API key).
    """
    question = question.strip()

    if not use_llm or _looks_english(question):
        return PreparedQuery(
            original=question,
            language=_guess_language(question) if not use_llm else "English",
            search_query=expand_search_query(question),
        )

    from app.llm import chat

    result = chat(
        system=PREPARE_SEARCH_SYSTEM,
        user=question,
        temperature=0.0,
    )
    language, search_query = _parse_prepare_response(result.answer, question)
    search_query = expand_search_query(f"{search_query} {question}")
    return PreparedQuery(
        original=question,
        language=language,
        search_query=search_query,
    )


def _parse_prepare_response(raw: str, fallback_question: str) -> tuple[str, str]:
    language = "English"
    search_query = fallback_question
    for line in raw.splitlines():
        stripped = line.strip()
        upper = stripped.upper()
        if upper.startswith("LANGUAGE:"):
            language = stripped.split(":", 1)[1].strip() or language
        elif upper.startswith("SEARCH_QUERY:"):
            search_query = stripped.split(":", 1)[1].strip() or search_query
    return language, search_query
