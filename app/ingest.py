"""Load policy markdown into section dicts for later retrieval."""

from __future__ import annotations

import re

from app.config import POLICY_PATH


def _section_id(title: str) -> str:
    """Stable id from a heading, e.g. '1. Refund Period' -> '1._refund_period'."""
    return title.lower().replace(" ", "_")


# Extra searchable terms so keyword ranking prefers the right H2.
_SECTION_KEYWORDS: dict[str, str] = {
    "1. Refund Period": (
        "refund period deadline 7 days change of mind undamaged "
        "return window after delivery receipt"
    ),
    "2. Non-Refundable Conditions": (
        "non-refundable conditions negligence customer damage label "
        "package opening powered on electronics defect"
    ),
    "3. Refund Process": (
        "refund process Request Refund My Page photos "
        "3 business days customer service review"
    ),
    "4. Contact Information": (
        "contact information customer service phone 02-1234-5678 "
        "support hours 1:1 chat weekdays"
    ),
}


def load_policies() -> list[dict]:
    """Split the policy markdown on H2 headings into searchable chunks.

    Skips the H1 preamble (title/intro) so keyword search is not diluted by
    generic words like "Refund" / "Policy" that appear in the document title.
    """
    text = POLICY_PATH.read_text(encoding="utf-8")
    sections: list[dict] = []

    # Keep only H2 blocks ("## ..."). Ignore leading H1 + intro.
    parts = re.split(r"\n(?=## )", text)
    for part in parts:
        part = part.strip()
        if not part.startswith("## "):
            continue

        lines = part.split("\n", 1)
        title = lines[0].lstrip("#").strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if not body:
            continue

        sections.append({
            "id": _section_id(title),
            "section": title,
            "text": body,
            "keywords": _SECTION_KEYWORDS.get(title, title),
            "source": POLICY_PATH.name,
        })

    return sections
