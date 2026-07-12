from __future__ import annotations

import re
from typing import List

from app.domains.extraction.schemas import ExtractedRelation


NAME_CORE = r"[A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){1,4}"

TITLE = (
    r"(?:Ông|Bà|Cụ|Anh|Chị|Chú|Cô|Bác|Cậu|Dì|Mợ|Thím|Dượng|"
    r"ông|bà|cụ|anh|chị|chú|cô|bác|cậu|dì|mợ|thím|dượng)"
)

PERSON = rf"((?:{TITLE}\s+)?{NAME_CORE})"


TITLE_PATTERN = re.compile(
    r"^(ông|bà|cụ|anh|chị|chú|cô|bác|cậu|dì|mợ|thím|dượng)\s+",
    re.IGNORECASE,
)


def clean_person_name(name: str) -> str:
    name = name.strip(" .,:;!?\"'")
    name = TITLE_PATTERN.sub("", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def clean_evidence(text: str) -> str:
    text = re.sub(r"\s+", " ", text)

    text = re.sub(
        r"\b(ông|bà|cụ|anh|chị|chú|cô|bác|cậu|dì|mợ|thím|dượng)(?=[A-ZÀ-Ỹ])",
        r"\1 ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(r"\bcủa(?=[A-ZÀ-Ỹ])", "của ", text)
    text = re.sub(r"\blà(?=[A-ZÀ-Ỹ])", "là ", text)

    return text.strip(" .,:;!?\"'")


class GrandparentRule:
    name = "grandparent_rule"

    def __init__(self) -> None:
        # A là ông nội/ông ngoại/ông của B
        self.grandfather_pattern = re.compile(
            rf"{PERSON}\s+là\s+(?:ông nội|ông ngoại|ông)\s+của\s+{PERSON}"
        )

        # A là bà nội/bà ngoại/bà của B
        self.grandmother_pattern = re.compile(
            rf"{PERSON}\s+là\s+(?:bà nội|bà ngoại|bà)\s+của\s+{PERSON}"
        )

        # B là cháu nội/cháu ngoại/cháu của A
        self.grandchild_pattern = re.compile(
            rf"{PERSON}\s+là\s+(?:cháu nội|cháu ngoại|cháu)\s+của\s+{PERSON}"
        )

    def extract(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        results.extend(self._extract_grandfather(sentence))
        results.extend(self._extract_grandmother(sentence))
        results.extend(self._extract_grandchild(sentence))

        return self._deduplicate(results)

    def _extract_grandfather(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        for match in self.grandfather_pattern.finditer(sentence):
            grandparent = clean_person_name(match.group(1))
            grandchild = clean_person_name(match.group(2))
            evidence = clean_evidence(match.group(0))

            results.append(
                ExtractedRelation(
                    source_person=grandparent,
                    relation_type="grandparent_of",
                    target_person=grandchild,
                    evidence=evidence,
                    rule_name="grandfather_pattern",
                    confidence=0.9,
                )
            )

        return results

    def _extract_grandmother(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        for match in self.grandmother_pattern.finditer(sentence):
            grandparent = clean_person_name(match.group(1))
            grandchild = clean_person_name(match.group(2))
            evidence = clean_evidence(match.group(0))

            results.append(
                ExtractedRelation(
                    source_person=grandparent,
                    relation_type="grandparent_of",
                    target_person=grandchild,
                    evidence=evidence,
                    rule_name="grandmother_pattern",
                    confidence=0.9,
                )
            )

        return results

    def _extract_grandchild(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        for match in self.grandchild_pattern.finditer(sentence):
            grandchild = clean_person_name(match.group(1))
            grandparent = clean_person_name(match.group(2))
            evidence = clean_evidence(match.group(0))

            results.append(
                ExtractedRelation(
                    source_person=grandparent,
                    relation_type="grandparent_of",
                    target_person=grandchild,
                    evidence=evidence,
                    rule_name="grandchild_pattern",
                    confidence=0.9,
                )
            )

        return results

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