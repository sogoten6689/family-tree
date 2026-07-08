from __future__ import annotations

from typing import List

from app.domains.extraction.rules.patterns import RE_SENTENCE_SPLIT


def split_sentences(text: str) -> List[str]:
    """
    Split a text into sentences to prevent regex patterns from leaking across boundaries.
    Uses the same delimiter heuristic as the existing MVP (RE_SENTENCE_SPLIT).
    """

    return [s.strip() for s in RE_SENTENCE_SPLIT.split(text) if s.strip()]

