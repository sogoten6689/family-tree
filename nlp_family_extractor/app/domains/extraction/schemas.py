from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class ExtractedRelation:
    source_person: str
    relation_type: str
    target_person: str
    evidence: str
    rule_name: str
    confidence: float = 1.0


@dataclass
class ExtractionResult:
    # Currently unused by the existing MVP extractor; reserved for future refactor.
    relations: List[ExtractedRelation]

