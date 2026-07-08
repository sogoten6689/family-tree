from __future__ import annotations

from typing import List

from app.domains.extraction.schemas import ExtractedRelation


class SpouseRule:
    """
    Placeholder spouse rule.

    The current MVP extraction logic lives inside `FamilyExtractor` and is not
    wired to this class yet. This file exists to match the desired refactor layout.
    """

    name = "spouse_rule"

    def extract(self, sentence: str) -> List[ExtractedRelation]:
        return []

