from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class Person:
    id: str
    full_name: str
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    gender: Optional[str] = None  # "M" | "F" | None

@dataclass
class Relationship:
    from_id: str
    to_id: str
    type: str  # "parent_of" | "spouse_of"
    confidence: float = 0.8
    source: str = "nlp"