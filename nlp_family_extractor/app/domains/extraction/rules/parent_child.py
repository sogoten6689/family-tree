from __future__ import annotations

import re
from typing import List, Optional

from app.domains.extraction.schemas import ExtractedRelation


NAME_CORE = r"[A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){1,4}"

TITLE = (
    r"(?:Ông|Bà|Cụ|Anh|Chị|Chú|Cô|Bác|Cậu|Dì|Mợ|Thím|Dượng|"
    r"ông|bà|cụ|anh|chị|chú|cô|bác|cậu|dì|mợ|thím|dượng)"
)

PERSON = rf"((?:{TITLE}\s+)?{NAME_CORE})"


def clean_evidence(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" .,:;!?\"'")



TITLE_PATTERN = re.compile(
    r"^(ông|bà|cụ|anh|chị|chú|cô|bác|cậu|dì|mợ|thím|dượng)\s+",
    re.IGNORECASE,
)


def clean_person_name(name: str) -> str:
    name = name.strip(" .,:;!?\"'")
    name = TITLE_PATTERN.sub("", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()


class ParentChildRule:
    name = "parent_child_rule"

    def __init__(self) -> None:
        self.father_pattern = re.compile(
            rf"{PERSON}\s+là\s+(?:cha|bố|ba|thân phụ)\s+của\s+{PERSON}",
        )

        self.mother_pattern = re.compile(
            rf"{PERSON}\s+là\s+(?:mẹ|má|thân mẫu|mẫu thân)\s+của\s+{PERSON}",
        )

        self.child_of_pattern = re.compile(
            rf"{PERSON}\s+là\s+con\s+của\s+{PERSON}(?:\s+và\s+{PERSON})?",
        )

        self.have_child_pattern = re.compile(
            rf"{PERSON}\s+và\s+{PERSON}\s+có\s+con\s+là\s+(.+)",
        )

        self.single_parent_have_child_pattern = re.compile(
            rf"{PERSON}\s+có\s+con\s+là\s+(.+)",
        )

    def extract(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        results.extend(self._extract_father(sentence))
        results.extend(self._extract_mother(sentence))
        results.extend(self._extract_child_of(sentence))

        have_child_results = self._extract_have_child(sentence)
        results.extend(have_child_results)

    # Nếu câu đã match dạng "A và B có con là C",
    # thì không chạy rule "A có con là C" nữa để tránh relation rác.
        if not have_child_results:
            results.extend(self._extract_single_parent_have_child(sentence))

        return self._deduplicate(results)

    def _extract_father(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        for match in self.father_pattern.finditer(sentence):
            parent = clean_person_name(match.group(1))
            child = clean_person_name(match.group(2))
            evidence = clean_evidence(match.group(0))

            results.append(
                ExtractedRelation(
                    source_person=parent,
                    relation_type="parent_of",
                    target_person=child,
                    evidence=evidence,
                    rule_name="father_pattern",
                    confidence=0.95,
                )
            )

        return results

    def _extract_mother(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        for match in self.mother_pattern.finditer(sentence):
            parent = clean_person_name(match.group(1))
            child = clean_person_name(match.group(2))
            evidence = clean_evidence(match.group(0))

            results.append(
                ExtractedRelation(
                    source_person=parent,
                    relation_type="parent_of",
                    target_person=child,
                    evidence=evidence,
                    rule_name="mother_pattern",
                    confidence=0.95,
                )
            )

        return results

    def _extract_child_of(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        for match in self.child_of_pattern.finditer(sentence):
            child = clean_person_name(match.group(1))
            parent_1 = clean_person_name(match.group(2))
            parent_2 = self._safe_clean_group(match, 3)
            evidence = clean_evidence(match.group(0))

            results.append(
                ExtractedRelation(
                    source_person=parent_1,
                    relation_type="parent_of",
                    target_person=child,
                    evidence=evidence,
                    rule_name="child_of_pattern",
                    confidence=0.9,
                )
            )

            if parent_2:
                results.append(
                    ExtractedRelation(
                        source_person=parent_2,
                        relation_type="parent_of",
                        target_person=child,
                        evidence=evidence,
                        rule_name="child_of_pattern",
                        confidence=0.9,
                    )
                )

        return results

    def _extract_have_child(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        for match in self.have_child_pattern.finditer(sentence):
            parent_1 = clean_person_name(match.group(1))
            parent_2 = clean_person_name(match.group(2))
            children_text = match.group(3)
            evidence = clean_evidence(match.group(0))

            children = self._split_people_list(children_text)

            for child in children:
                results.append(
                    ExtractedRelation(
                        source_person=parent_1,
                        relation_type="parent_of",
                        target_person=child,
                        evidence=evidence,
                        rule_name="have_child_pattern",
                        confidence=0.9,
                    )
                )

                results.append(
                    ExtractedRelation(
                        source_person=parent_2,
                        relation_type="parent_of",
                        target_person=child,
                        evidence=evidence,
                        rule_name="have_child_pattern",
                        confidence=0.9,
                    )
                )

        return results

    def _extract_single_parent_have_child(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        for match in self.single_parent_have_child_pattern.finditer(sentence):
            parent = clean_person_name(match.group(1))
            children_text = match.group(2)
            evidence = clean_evidence(match.group(0))

            children = self._split_people_list(children_text)

            for child in children:
                results.append(
                    ExtractedRelation(
                        source_person=parent,
                        relation_type="parent_of",
                        target_person=child,
                        evidence=evidence,
                        rule_name="single_parent_have_child_pattern",
                        confidence=0.85,
                    )
                )

        return results

    def _split_people_list(self, text: str) -> List[str]:
        text = clean_evidence(text)

        # Cắt phần mô tả dư phía sau nếu có.
        text = re.split(
            r"\s+(?:sinh năm|quê|ở|hiện|là|gồm|bao gồm)\s+",
            text,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        text = re.sub(r"\s+và\s+", ",", text)
        text = re.sub(r"\s*,\s*", ",", text)

        parts = [clean_person_name(part) for part in text.split(",")]

        return [
            part
            for part in parts
            if part and len(part.split()) >= 2
        ]

    def _safe_clean_group(self, match: re.Match, index: int) -> Optional[str]:
        try:
            value = match.group(index)
        except IndexError:
            return None

        if not value:
            return None

        return clean_person_name(value)

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