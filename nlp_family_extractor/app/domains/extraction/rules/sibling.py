from __future__ import annotations

from typing import List

from app.domains.extraction.schemas import ExtractedRelation


class SiblingRule:
    """
    Placeholder sibling rule.

    Existing MVP extraction still generates sibling_of edges inside `FamilyExtractor`.
    """

    name = "sibling_rule"

    def extract(self, sentence: str) -> List[ExtractedRelation]:
        return []

