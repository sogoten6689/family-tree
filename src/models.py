from dataclasses import dataclass
from typing import Optional


@dataclass
class Person:
    id: str
    full_name: str
    gender: Optional[str] = None
    birth_year: Optional[int] = None
    death_year: Optional[int] = None


@dataclass
class Relationship:
    from_id: str
    to_id: str
    type: str  
    source: str = "unknown"
    confidence: float = 1.0
