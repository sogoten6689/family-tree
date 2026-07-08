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

    # Fix title bị dính với tên: bàNguyễn -> bà Nguyễn
    text = re.sub(
        r"\b(ông|bà|cụ|anh|chị|chú|cô|bác|cậu|dì|mợ|thím|dượng)(?=[A-ZÀ-Ỹ])",
        r"\1 ",
        text,
        flags=re.IGNORECASE,
    )

    # Fix keyword bị dính với tên.
    text = re.sub(r"\bcủa(?=[A-ZÀ-Ỹ])", "của ", text)
    text = re.sub(r"\bvới(?=[A-ZÀ-Ỹ])", "với ", text)
    text = re.sub(r"\blà(?=[A-ZÀ-Ỹ])", "là ", text)

    return text.strip(" .,:;!?\"'")


class SiblingRule:
    name = "sibling_rule"

    def __init__(self) -> None:
        # Case 1:
        # Nguyễn Văn Bình và Nguyễn Thị Lan là anh em.
        # Nguyễn Văn Bình và Nguyễn Thị Lan là anh chị em ruột.
        self.pair_sibling_pattern = re.compile(
            rf"{PERSON}\s+và\s+{PERSON}\s+là\s+"
            rf"(?:anh em|chị em|anh chị em|anh em ruột|chị em ruột|anh chị em ruột)"
        )

        # Case 2:
        # Nguyễn Văn Bình là anh trai của Nguyễn Thị Lan.
        # Nguyễn Thị Lan là em gái của Nguyễn Văn Bình.
        self.direct_sibling_pattern = re.compile(
            rf"{PERSON}\s+là\s+"
            rf"(?:anh trai|chị gái|em trai|em gái|anh|chị|em)"
            rf"(?:\s+ruột)?\s+của\s+{PERSON}"
        )

    def extract(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        results.extend(self._extract_pair_sibling(sentence))
        results.extend(self._extract_direct_sibling(sentence))

        return self._deduplicate(results)

    def _extract_pair_sibling(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        for match in self.pair_sibling_pattern.finditer(sentence):
            person_1 = clean_person_name(match.group(1))
            person_2 = clean_person_name(match.group(2))
            evidence = clean_evidence(match.group(0))

            results.extend(
                self._make_bidirectional_sibling(
                    person_1=person_1,
                    person_2=person_2,
                    evidence=evidence,
                    rule_name="pair_sibling_pattern",
                    confidence=0.9,
                )
            )

        return results

    def _extract_direct_sibling(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        for match in self.direct_sibling_pattern.finditer(sentence):
            person_1 = clean_person_name(match.group(1))
            person_2 = clean_person_name(match.group(2))
            evidence = clean_evidence(match.group(0))

            results.extend(
                self._make_bidirectional_sibling(
                    person_1=person_1,
                    person_2=person_2,
                    evidence=evidence,
                    rule_name="direct_sibling_pattern",
                    confidence=0.9,
                )
            )

        return results

    def _make_bidirectional_sibling(
        self,
        person_1: str,
        person_2: str,
        evidence: str,
        rule_name: str,
        confidence: float,
    ) -> List[ExtractedRelation]:
        if not person_1 or not person_2 or person_1 == person_2:
            return []

        return [
            ExtractedRelation(
                source_person=person_1,
                relation_type="sibling_of",
                target_person=person_2,
                evidence=evidence,
                rule_name=rule_name,
                confidence=confidence,
            ),
            ExtractedRelation(
                source_person=person_2,
                relation_type="sibling_of",
                target_person=person_1,
                evidence=evidence,
                rule_name=rule_name,
                confidence=confidence,
            ),
        ]

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