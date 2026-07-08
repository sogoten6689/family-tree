from __future__ import annotations

import re
from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

from app.domains.extraction.normalizer import (
    find_year,
    infer_gender_from_title,
    normalize_name,
    normalize_text,
)
from app.domains.extraction.sentence_splitter import split_sentences
from app.domains.extraction.rules.patterns import (
    NAME_CAPS,
    NAME_WITH_TITLE,
    RE_BIRTH,
    RE_CHILD_OF,
    RE_DEATH,
    RE_FATHER_LABEL,
    RE_HAVE_CHILD,
    RE_IS_SPOUSE,
    RE_MOTHER_LABEL,
    RE_SIBLING,
    RE_SPOUSE,
    RE_SENTENCE_SPLIT,
)
from app.models import Person, Relationship

from app.domains.extraction.schemas import ExtractedRelation
from app.domains.extraction.rules.spouse import SpouseRule
from app.domains.extraction.rules.parent_child import ParentChildRule


def _pick_longest_match(candidates: List[str], chunk: str) -> Optional[str]:
    hits = [c for c in candidates if c and c in chunk]
    if not hits:
        return None
    return max(hits, key=len)


def _split_sentences(text: str) -> List[str]:
    # Backward-compatible wrapper.
    return split_sentences(text)


class FamilyExtractor:
    """
    MVP rule-based extractor (moved under app/domains/extraction).

    Notes:
    - This refactor keeps extraction behavior as-is to avoid breaking the pipeline.
    - Next phase can replace the internal logic with independent rule modules.
    """

    def __init__(self, id_prefix: str = "P") -> None:
        self.id_prefix = id_prefix
        self._next_id = 1
        self._people_by_key: Dict[Tuple[str, Optional[int]], Person] = {}
        self._name_index: Dict[str, List[Tuple[Tuple[str, Optional[int]], Person]]] = {}
        self._relationships: List[Relationship] = []
        self._relationship_keys = set()

    def _new_id(self) -> str:
        pid = f"{self.id_prefix}{self._next_id:03d}"
        self._next_id += 1
        return pid

    def _get_or_create(
        self, full_name: str, birth_year: Optional[int] = None, gender: Optional[str] = None
    ) -> Person:
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

    def _add_relationship(
        self, from_id: str, to_id: str, rel_type: str, confidence: float = 0.8
    ) -> None:
        if not from_id or not to_id or from_id == to_id:
            return

        key = (from_id, to_id, rel_type)
        if key in self._relationship_keys:
            return

        self._relationship_keys.add(key)
        self._relationships.append(
            Relationship(from_id=from_id, to_id=to_id, type=rel_type, confidence=confidence)
        )

    def _names_with_positions(self, sentence: str, candidates: List[str]) -> List[Tuple[str, int]]:
        hits: List[Tuple[str, int]] = []
        for name in candidates:
            idx = sentence.find(name)
            if idx != -1:
                hits.append((name, idx))
        hits.sort(key=lambda x: x[1])
        return hits

    def _extract_sentence_relations(
        self,
        text: str,
        candidates: List[str],
        name_to_person: Dict[str, Person],
    ) -> None:
        sentences = _split_sentences(text)

        for sentence in sentences:
            names_pos = self._names_with_positions(sentence, candidates)
            names_in_order = [n for n, _ in names_pos]

            # Spouse patterns: "A kết hôn với B", "A là vợ/chồng của B"
            if (RE_SPOUSE.search(sentence) or RE_IS_SPOUSE.search(sentence)) and len(names_in_order) >= 2:
                a, b = names_in_order[0], names_in_order[1]
                self._add_relationship(name_to_person[a].id, name_to_person[b].id, "spouse_of", 0.92)
                self._add_relationship(name_to_person[b].id, name_to_person[a].id, "spouse_of", 0.92)

            # Child-of patterns: "X là con của Y [và Z]"
            for m in RE_CHILD_OF.finditer(sentence):
                idx = m.start()
                left = [n for n, p in names_pos if p < idx]
                right = [n for n, p in names_pos if p > idx]
                if not left or not right:
                    continue

                child = left[-1]
                for parent in right[:2]:
                    self._add_relationship(name_to_person[parent].id, name_to_person[child].id, "parent_of", 0.9)

            # Have-child patterns: "A và B có con là C, D"
            for m in RE_HAVE_CHILD.finditer(sentence):
                idx = m.start()
                left = [n for n, p in names_pos if p < idx]
                right = [n for n, p in names_pos if p > idx]
                if not left or not right:
                    continue

                parents = left[-2:] if len(left) >= 2 else left[-1:]
                children = right[:4]
                for parent in parents:
                    for child in children:
                        if parent != child:
                            self._add_relationship(name_to_person[parent].id, name_to_person[child].id, "parent_of", 0.88)

            # Father/mother label patterns: "X, cha là Y", "X, mẹ là Z"
            if len(names_in_order) >= 2:
                child = names_in_order[0]
                for m in RE_FATHER_LABEL.finditer(sentence):
                    idx = m.start()
                    right_names = [n for n, p in names_pos if p > idx]
                    if right_names:
                        parent = right_names[0]
                        self._add_relationship(name_to_person[parent].id, name_to_person[child].id, "parent_of", 0.87)

                for m in RE_MOTHER_LABEL.finditer(sentence):
                    idx = m.start()
                    right_names = [n for n, p in names_pos if p > idx]
                    if right_names:
                        parent = right_names[0]
                        self._add_relationship(name_to_person[parent].id, name_to_person[child].id, "parent_of", 0.87)

            # Sibling patterns
            if RE_SIBLING.search(sentence) and len(names_in_order) >= 2:
                for i in range(len(names_in_order) - 1):
                    a = names_in_order[i]
                    b = names_in_order[i + 1]
                    self._add_relationship(name_to_person[a].id, name_to_person[b].id, "sibling_of", 0.75)
                    self._add_relationship(name_to_person[b].id, name_to_person[a].id, "sibling_of", 0.75)

    def _all_candidate_names(self, text: str) -> List[Tuple[str, Optional[str]]]:
        out: List[Tuple[str, Optional[str]]] = []

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
        uniq: List[Tuple[str, Optional[str]]] = []
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
        normalized_candidates: List[Tuple[str, Optional[str]]] = []
        for raw, g in raw_candidates:
            name = normalize_name(raw)
            if len(name.split()) < 2:
                continue
            normalized_candidates.append((name, g))

        # create initial persons without birth_year
        name_to_person: Dict[str, Person] = {}
        for name, g in normalized_candidates:
            p = self._get_or_create(name, None, g)
            name_to_person[name] = p

        # extract birth/death year near name (simple window)
        for name, _ in normalized_candidates:
            m = re.search(rf"{re.escape(name)}(.{{0,80}})", text)
            if not m:
                continue
            window = m.group(0)

            if RE_BIRTH.search(window):
                y = find_year(window)
                if y:
                    old = name_to_person[name]
                    p = self._get_or_create(name, y, old.gender)
                    p.death_year = old.death_year or p.death_year
                    name_to_person[name] = p

            if RE_DEATH.search(window):
                y = find_year(window)
                if y:
                    name_to_person[name].death_year = y

        candidates = sorted(set(name_to_person.keys()), key=len, reverse=True)

        # spouse relations (global window heuristic)
        for m in RE_SPOUSE.finditer(text):
            start, end = m.start(), m.end()
            left = text[max(0, start - 120) : start]
            right = text[end : min(len(text), end + 120)]

            a = _pick_longest_match(candidates, left)
            b = _pick_longest_match(candidates, right)

            if a and b and a != b:
                self._add_relationship(name_to_person[a].id, name_to_person[b].id, "spouse_of", 0.9)
                self._add_relationship(name_to_person[b].id, name_to_person[a].id, "spouse_of", 0.9)

        # parent relations (global window heuristic)
        for m in RE_CHILD_OF.finditer(text):
            start, end = m.start(), m.end()
            left = text[max(0, start - 140) : start]
            right = text[end : min(len(text), end + 180)]

            child = _pick_longest_match(candidates, left)
            if not child:
                continue

            parents: List[str] = []
            for cand in candidates:
                if cand in right and cand != child:
                    parents.append(cand)
                if len(parents) >= 2:
                    break

            for par in parents:
                self._add_relationship(name_to_person[par].id, name_to_person[child].id, "parent_of", 0.85)

        # richer sentence-level extraction
        self._extract_sentence_relations(text, candidates, name_to_person)

        people = list(self._people_by_key.values())
        return {
            "people": [asdict(p) for p in people],
            "relationships": [asdict(r) for r in self._relationships],
        }

class RuleBasedRelationExtractor:
    """
    New modular rule-based relation extractor.

    This extractor runs independent rule modules such as:
    - SpouseRule
    - ParentChildRule
    - SiblingRule later

    It returns ExtractedRelation objects instead of full people/tree output.
    """

    def __init__(self) -> None:
        self.rules = [
            SpouseRule(),
            ParentChildRule(),
            # SiblingRule(),  # bật sau khi implement sibling.py
        ]

    def extract_relations(self, text: str) -> List[ExtractedRelation]:
        normalized_text = normalize_text(text)
        sentences = split_sentences(normalized_text)

        relations: List[ExtractedRelation] = []

        for sentence in sentences:
            for rule in self.rules:
                relations.extend(rule.extract(sentence))

        return self._deduplicate(relations)

    def _deduplicate(self, relations: List[ExtractedRelation]) -> List[ExtractedRelation]:
        seen = set()
        unique: List[ExtractedRelation] = []

        for relation in relations:
            key = (
                relation.source_person,
                relation.relation_type,
                relation.target_person,
            )

            if key in seen:
                continue

            seen.add(key)
            unique.append(relation)

        return unique

