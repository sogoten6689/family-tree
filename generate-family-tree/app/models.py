from dataclasses import dataclass
from typing import List


@dataclass
class Person:
    full_name: str
    gender: str
    birth_year: int
    death_year: int
    birth_place: str
    occupation: str
    father: str
    mother: str
    spouse: List[str]
    children: List[str]