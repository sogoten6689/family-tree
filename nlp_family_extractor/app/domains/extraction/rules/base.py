from __future__ import annotations

from typing import List, Protocol

from app.domains.extraction.schemas import ExtractedRelation


class RelationRule(Protocol):
    """
    Base protocol for extraction rules.

    This project currently uses an MVP extractor implementation; these protocols
    are added for future step-by-step refactors.
    """

    name: str

    def extract(self, sentence: str) -> List[ExtractedRelation]:
        ...

