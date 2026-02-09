import json
from typing import List, Tuple
from src.models import Person, Relationship


def load_family_json(path: str) -> Tuple[List[Person], List[Relationship]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    people = [Person(**p) for p in data.get("people", [])]
    relationships = [Relationship(**r) for r in data.get("relationships", [])]
    return people, relationships
