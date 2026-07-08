from __future__ import annotations

from typing import List

from app.domains.extraction.rules.patterns import NAME_CAPS, NAME_WITH_TITLE


def extract_person_candidates(text: str) -> List[str]:
    """
    Candidate name extractor via regex heuristics.

    This is currently a lightweight helper for future refactors.
    The current MVP extractor still uses its internal candidate pipeline.
    """
    out: List[str] = []

    for m in NAME_WITH_TITLE.finditer(text):
        raw = m.group(0).strip()
        if raw and raw not in out:
            out.append(raw)

    for m in NAME_CAPS.finditer(text):
        raw = m.group(1).strip()
        if raw and raw not in out:
            out.append(raw)

    return out

