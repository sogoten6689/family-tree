from typing import List, Dict
from src.models import Person, Relationship


ALLOWED_REL_TYPES = {"parent_of", "spouse_of", "sibling_of"}


def validate_data(people: List[Person], relationships: List[Relationship]) -> List[str]:
    errors: List[str] = []

    people_by_id: Dict[str, Person] = {p.id: p for p in people}

    if len(people_by_id) != len(people):
        errors.append("Duplicate person_id found.")

    for p in people:
        if not p.id or not p.full_name:
            errors.append(f"Invalid person record: {p}")
        if p.birth_year and p.death_year and p.birth_year > p.death_year:
            errors.append(f"[{p.id}] birth_year > death_year")

    spouse_pairs = set()  # to detect contradictions/duplicates
    for r in relationships:
        if r.type not in ALLOWED_REL_TYPES:
            errors.append(f"Invalid relation type: {r.type}")
            continue

        if r.from_id == r.to_id:
            errors.append(f"Self relationship not allowed: {r.from_id} -> {r.to_id} ({r.type})")

        if r.from_id not in people_by_id:
            errors.append(f"from_id not found: {r.from_id}")
            continue
        if r.to_id not in people_by_id:
            errors.append(f"to_id not found: {r.to_id}")
            continue

        if r.confidence < 0 or r.confidence > 1:
            errors.append(f"Confidence out of range [0,1]: {r}")

        if r.type == "parent_of":
            p_from = people_by_id[r.from_id]
            p_to = people_by_id[r.to_id]
            if p_from.birth_year and p_to.birth_year:
                age_gap = p_to.birth_year - p_from.birth_year
                if age_gap < 12:
                    errors.append(
                        f"Unrealistic parent age gap ({age_gap}) for {r.from_id} -> {r.to_id}"
                    )

        if r.type == "spouse_of":
            pair = tuple(sorted([r.from_id, r.to_id]))
            if pair in spouse_pairs:
                errors.append(f"Duplicate spouse relationship: {pair[0]} - {pair[1]}")
            spouse_pairs.add(pair)

    return errors
