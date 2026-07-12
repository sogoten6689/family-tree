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

NUMBER_WORD = r"(?:một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười|\d+)"

TITLE_PATTERN = re.compile(
    r"^(ông|bà|cụ|anh|chị|chú|cô|bác|cậu|dì|mợ|thím|dượng)\s+",
    re.IGNORECASE,
)


def clean_evidence(text: str) -> str:
    text = re.sub(r"\s+", " ", text)

    # Fix title bị dính với tên: bàTrần -> bà Trần
    text = re.sub(
        r"\b(ông|bà|cụ|anh|chị|chú|cô|bác|cậu|dì|mợ|thím|dượng)(?=[A-ZÀ-Ỹ])",
        r"\1 ",
        text,
        flags=re.IGNORECASE,
    )

    # Fix keyword bị dính với từ sau
    text = re.sub(r"\bcủa(?=[A-ZÀ-Ỹ])", "của ", text)
    text = re.sub(r"\bvới(?=[A-ZÀ-Ỹ])", "với ", text)
    text = re.sub(r"\blà(?=[A-ZÀ-Ỹ])", "là ", text)

    # Fix một số lỗi evidence hay gặp
    text = text.replace("bàTrần", "bà Trần")
    text = text.replace("ôngNguyễn", "ông Nguyễn")
    text = text.replace("củaNguyễn", "của Nguyễn")
    text = text.replace("vớiNguyễn", "với Nguyễn")
    text = text.replace("kết hônvới", "kết hôn với")

    return text.strip(" .,:;!?\"'")


def clean_person_name(name: str) -> str:
    name = name.strip(" .,:;!?\"'")
    name = TITLE_PATTERN.sub("", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()


class ParentChildRule:
    name = "parent_child_rule"

    def __init__(self) -> None:
        # A là cha/bố/ba/thân phụ của B
        self.father_pattern = re.compile(
            rf"{PERSON}\s+là\s+"
            rf"(?:cha ruột|bố ruột|thân phụ|phụ thân|cha|bố|ba)"
            rf"\s+của\s+{PERSON}",
        )

        # A là mẹ/má/thân mẫu của B
        self.mother_pattern = re.compile(
            rf"{PERSON}\s+là\s+"
            rf"(?:mẹ ruột|thân mẫu|mẫu thân|mẹ|má)"
            rf"\s+của\s+{PERSON}",
        )

        # B là con của A và C
        # B là con trai/con gái/trưởng nam/con út của A
        self.child_of_pattern = re.compile(
            rf"{PERSON}\s+là\s+"
            rf"(?:con trai|con gái|con ruột|trưởng nam|trưởng nữ|con cả|con út|con thứ(?:\s+\w+)?|con)"
            rf"\s+của\s+{PERSON}(?:\s+và\s+{PERSON})?",
        )

        # A và B có con là C
        # A và B có các con là C, D
        # A và B có hai người con là C và D
        self.have_child_pattern = re.compile(
            rf"{PERSON}\s+và\s+{PERSON}\s+có\s+"
            rf"(?:các\s+|những\s+)?"
            rf"(?:(?:{NUMBER_WORD})\s+)?"
            rf"(?:người\s+)?con\s*"
            rf"(?:là|gồm|bao gồm|:)\s+(.+)",
        )

        # A có con là B
        # A có hai người con là B và C
        self.single_parent_have_child_pattern = re.compile(
            rf"{PERSON}\s+có\s+"
            rf"(?:các\s+|những\s+)?"
            rf"(?:(?:{NUMBER_WORD})\s+)?"
            rf"(?:người\s+)?con\s*"
            rf"(?:là|gồm|bao gồm|:)\s+(.+)",
        )

        # A và B sinh được C
        # A và B sinh được hai người con là C và D
        # A và B sinh ra C và D
        # A và B hạ sinh C
        self.pair_parent_born_children_pattern = re.compile(
            rf"{PERSON}\s+và\s+{PERSON}\s+"
            rf"(?:sinh\s+(?:được|ra|hạ)|hạ\s+sinh)\s+"
            rf"(?:(?:{NUMBER_WORD})\s+)?"
            rf"(?:người\s+)?"
            rf"(?:con\s*)?"
            rf"(?:là|:)?\s*(.+)",
        )

        # A sinh ra B
        # A sinh được B và C
        # A hạ sinh B
        self.single_parent_born_children_pattern = re.compile(
            rf"{PERSON}\s+"
            rf"(?:sinh\s+(?:được|ra|hạ)|hạ\s+sinh)\s+"
            rf"(?:(?:{NUMBER_WORD})\s+)?"
            rf"(?:người\s+)?"
            rf"(?:con\s*)?"
            rf"(?:là|:)?\s*(.+)",
        )

    def extract(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        results.extend(self._extract_father(sentence))
        results.extend(self._extract_mother(sentence))
        results.extend(self._extract_child_of(sentence))

        pair_child_results: List[ExtractedRelation] = []
        pair_child_results.extend(self._extract_have_child(sentence))
        pair_child_results.extend(self._extract_pair_parent_born_children(sentence))

        results.extend(pair_child_results)

        # Nếu câu đã match dạng "A và B có con/sinh được C",
        # thì không chạy single-parent rule nữa để tránh relation rác.
        if not pair_child_results:
            results.extend(self._extract_single_parent_have_child(sentence))
            results.extend(self._extract_single_parent_born_children(sentence))

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

    def _extract_pair_parent_born_children(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        for match in self.pair_parent_born_children_pattern.finditer(sentence):
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
                        rule_name="pair_parent_born_children_pattern",
                        confidence=0.9,
                    )
                )

                results.append(
                    ExtractedRelation(
                        source_person=parent_2,
                        relation_type="parent_of",
                        target_person=child,
                        evidence=evidence,
                        rule_name="pair_parent_born_children_pattern",
                        confidence=0.9,
                    )
                )

        return results

    def _extract_single_parent_born_children(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        for match in self.single_parent_born_children_pattern.finditer(sentence):
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
                        rule_name="single_parent_born_children_pattern",
                        confidence=0.85,
                    )
                )

        return results

    def _split_people_list(self, text: str) -> List[str]:
        text = clean_evidence(text)

        # Cắt phần mô tả dư phía sau nếu có.
        text = re.split(
            r"\s+(?:sinh năm|mất năm|quê|ở|hiện|sau này|là|gồm|bao gồm)\s+",
            text,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        # Ưu tiên bắt tên người bằng regex PERSON.
        matched_people = re.findall(PERSON, text)

        if matched_people:
            people = [clean_person_name(person) for person in matched_people]
        else:
            text = re.sub(r"\s+và\s+", ",", text)
            text = re.sub(r"\s*,\s*", ",", text)
            people = [clean_person_name(part) for part in text.split(",")]

        unique_people: List[str] = []
        seen = set()

        for person in people:
            if not person or len(person.split()) < 2:
                continue

            if person in seen:
                continue

            seen.add(person)
            unique_people.append(person)

        return unique_people

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