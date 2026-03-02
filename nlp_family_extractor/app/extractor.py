from __future__ import annotations

import re
from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

from .models import Person, Relationship
from .normalizer import normalize_text, normalize_name, infer_gender_from_title, find_year
from .patterns import (
    NAME_CAPS, NAME_WITH_TITLE,
    RE_BIRTH, RE_DEATH,
    RE_CHILD_OF, RE_SPOUSE
)

def _pick_longest_match(candidates: List[str], chunk: str) -> Optional[str]:
    hits = [c for c in candidates if c and c in chunk]
    if not hits:
        return None
    return max(hits, key=len)

class FamilyExtractor:
    """
    MVP rule-based:
    - Detect people candidates (heuristics)
    - Extract birth/death years
    - Extract spouse_of and parent_of relations by keyword patterns
    - Export JSON: people + relationships
    """
    def __init__(self, id_prefix: str = "P"):
        self.id_prefix = id_prefix
        self._next_id = 1
        self._people_by_key: Dict[Tuple[str, Optional[int]], Person] = {}
        self._name_index: Dict[str, List[Tuple[Tuple[str, Optional[int]], Person]]] = {}
        self._relationships: List[Relationship] = []

    def _new_id(self) -> str:
        pid = f"{self.id_prefix}{self._next_id:03d}"
        self._next_id += 1
        return pid

    def _get_or_create(self, full_name: str, birth_year: Optional[int] = None, gender: Optional[str] = None) -> Person:
        key = (full_name, birth_year)
        if key in self._people_by_key:
            p = self._people_by_key[key]
            if gender and not p.gender:
                p.gender = gender
            return p

        p = Person(id=self._new_id(), full_name=full_name, birth_year=birth_year, gender=gender)
        self._people_by_key[key] = p
        self._name_index.setdefault(full_name, []).append((key, p))
        return p

    def _all_candidate_names(self, text: str) -> List[Tuple[str, Optional[str]]]:
        """
        return list of (raw_name, gender_hint)
        """
        out = []
        # title + name
        for m in NAME_WITH_TITLE.finditer(text):
            raw = m.group(0)
            g = infer_gender_from_title(raw)
            out.append((raw, g))

        # capitalized sequences (no title)
        for m in NAME_CAPS.finditer(text):
            raw = m.group(1)
            out.append((raw, None))

        # unique by raw
        seen = set()
        uniq = []
        for raw, g in out:
            raw = raw.strip()
            if raw not in seen:
                seen.add(raw)
                uniq.append((raw, g))
        return uniq

    def parse(self, input_text: str) -> Dict:
        text = normalize_text(input_text)

        # gather candidates
        raw_candidates = self._all_candidate_names(text)
        # normalize names
        normalized_candidates = []
        for raw, g in raw_candidates:
            name = normalize_name(raw)
            if len(name.split()) < 2:
                continue
            normalized_candidates.append((name, g))

        # create initial persons without birth_year
        candidates_names = sorted({n for n, _ in normalized_candidates}, key=len, reverse=True)
        name_to_person: Dict[str, Person] = {}
        for name, g in normalized_candidates:
            p = self._get_or_create(name, None, g)
            name_to_person[name] = p

        # 2) extract birth/death year near name (simple window)
        for name, _ in normalized_candidates:
            # find "name ... sinh ... YEAR"
            m = re.search(rf"{re.escape(name)}(.{{0,80}})", text)
            if not m:
                continue
            window = m.group(0)

            # birth
            if RE_BIRTH.search(window):
                y = find_year(window)
                if y:
                    # re-create with birth_year key (move)
                    old = name_to_person[name]
                    p = self._get_or_create(name, y, old.gender)
                    p.death_year = old.death_year or p.death_year
                    name_to_person[name] = p

            # death
            if RE_DEATH.search(window):
                y = find_year(window)
                if y:
                    name_to_person[name].death_year = y

        # refresh candidates for matching chunks
        candidates = sorted(set(name_to_person.keys()), key=len, reverse=True)

        # 3) spouse relations
        for m in RE_SPOUSE.finditer(text):
            # take some left/right context around spouse keyword
            start, end = m.start(), m.end()
            left = text[max(0, start - 120):start]
            right = text[end:min(len(text), end + 120)]

            a = _pick_longest_match(candidates, left)
            b = _pick_longest_match(candidates, right)

            if a and b and a != b:
                self._relationships.append(Relationship(
                    from_id=name_to_person[a].id,
                    to_id=name_to_person[b].id,
                    type="spouse_of",
                    confidence=0.90
                ))

        # 4) parent relations
        # patterns like: "A là con của B và C"
        for m in RE_CHILD_OF.finditer(text):
            start, end = m.start(), m.end()
            left = text[max(0, start - 140):start]
            right = text[end:min(len(text), end + 180)]

            child = _pick_longest_match(candidates, left)
            if not child:
                continue

            # pick up to 2 parents in right
            parents = []
            for cand in candidates:
                if cand in right and cand != child:
                    parents.append(cand)
                if len(parents) >= 2:
                    break

            for par in parents:
                self._relationships.append(Relationship(
                    from_id=name_to_person[par].id,
                    to_id=name_to_person[child].id,
                    type="parent_of",
                    confidence=0.85
                ))

        # 5) build final JSON
        people = list(self._people_by_key.values())
        data = {
            "people": [asdict(p) for p in people],
            "relationships": [asdict(r) for r in self._relationships],
        }
        return data