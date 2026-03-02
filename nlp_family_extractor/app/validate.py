from __future__ import annotations
from typing import Dict, List, Tuple, Set

def validate_no_self_relationship(data: Dict) -> List[str]:
    errs = []
    for r in data.get("relationships", []):
        if r["from_id"] == r["to_id"]:
            errs.append(f"Self relationship detected: {r}")
    return errs

def validate_no_duplicate_edges(data: Dict) -> List[str]:
    errs = []
    seen: Set[Tuple[str, str, str]] = set()
    for r in data.get("relationships", []):
        key = (r["from_id"], r["to_id"], r["type"])
        if key in seen:
            errs.append(f"Duplicate relationship edge: {r}")
        else:
            seen.add(key)
    return errs

def validate_parent_age_gap(data: Dict, min_gap: int = 12) -> List[str]:
    # if there is birth_year
    errs = []
    people = {p["id"]: p for p in data.get("people", [])}
    for r in data.get("relationships", []):
        if r["type"] != "parent_of":
            continue
        parent = people.get(r["from_id"])
        child = people.get(r["to_id"])
        if not parent or not child:
            continue
        py = parent.get("birth_year")
        cy = child.get("birth_year")
        if isinstance(py, int) and isinstance(cy, int):
            if py > cy - min_gap:
                errs.append(
                    f"Suspicious parent/child age gap: parent({parent['full_name']}:{py}) "
                    f"child({child['full_name']}:{cy}) rel={r}"
                )
    return errs