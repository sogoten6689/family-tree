from __future__ import annotations

from typing import List

from app.domains.extraction.schemas import ExtractedRelation


class ParentChildRule:
    """
    Placeholder parent-child rule.

    Existing MVP rules are still inside `FamilyExtractor` for now.
    """

    name = "parent_child_rule"

    def extract(self, sentence: str) -> List[ExtractedRelation]:
        return []

