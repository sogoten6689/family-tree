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

NUMBER_WORD = r"(?:một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười|\d+)"

TITLE_PATTERN = re.compile(
    r"^(ông|bà|cụ|anh|chị|chú|cô|bác|cậu|dì|mợ|thím|dượng)\s+",
    re.IGNORECASE,
)


def clean_evidence(text: str) -> str:
    text = re.sub(r"\s+", " ", text)

    text = re.sub(
        r"\b(ông|bà|cụ|anh|chị|chú|cô|bác|cậu|dì|mợ|thím|dượng)(?=[A-ZÀ-Ỹ])",
        r"\1 ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(r"\bcủa\s*([A-ZÀ-Ỹ])", r"của \1", text)
    text = re.sub(r"\bvới\s*([A-ZÀ-Ỹ])", r"với \1", text)
    text = re.sub(r"\blà\s*([A-ZÀ-Ỹ])", r"là \1", text)

    text = text.replace("kết hônvới", "kết hôn với")
    text = text.replace("bàTrần", "bà Trần")
    text = text.replace("ôngNguyễn", "ông Nguyễn")

    return text.strip(" .,:;!?\"'")


def clean_person_name(name: str) -> str:
    name = name.strip(" .,:;!?\"'")
    name = TITLE_PATTERN.sub("", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()


class SpouseChildrenRule:
    """
    Extract relations from sentences like:

    Nguyễn Văn Bình kết hôn với Lê Thị Hoa, sinh được Nguyễn Văn Nam.
    Nguyễn Văn Bình lấy Lê Thị Hoa và có con là Nguyễn Văn Nam.
    Nguyễn Văn Bình là chồng của Lê Thị Hoa, sinh được Nguyễn Văn Nam.

    Output:
    - spouse_of, both directions
    - parent_of, from both parents to each child
    """

    name = "spouse_children_rule"

    def __init__(self) -> None:
        spouse_verb = r"(?:kết\s+hôn\s+với|thành\s+hôn\s+với|lấy|cưới)"

        children_connector = (
            rf"(?:"
            rf"sinh\s+(?:được|ra|hạ)"
            rf"|hạ\s+sinh"
            rf"|có\s+"
            rf"(?:các\s+|những\s+)?"
            rf"(?:(?:{NUMBER_WORD})\s+)?"
            rf"(?:người\s+)?con\s*"
            rf"(?:là|gồm|bao gồm|:)"
            rf")"
        )

        # A kết hôn với B, sinh được C và D.
        # A lấy B và có con là C.
        self.spouse_verb_children_pattern = re.compile(
            rf"{PERSON}\s+{spouse_verb}\s+{PERSON}"
            rf"\s*,?\s*(?:và\s+)?"
            rf"{children_connector}\s+(.+)",
        )

        # A là chồng của B, sinh được C.
        # A là vợ của B và có con là C.
        self.spouse_label_children_pattern = re.compile(
            rf"{PERSON}\s+là\s+(?:chồng|vợ)\s+của\s+{PERSON}"
            rf"\s*,?\s*(?:và\s+)?"
            rf"{children_connector}\s+(.+)",
        )

    def extract(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        results.extend(
            self._extract_from_pattern(
                sentence=sentence,
                pattern=self.spouse_verb_children_pattern,
                rule_name="spouse_verb_children_pattern",
            )
        )

        results.extend(
            self._extract_from_pattern(
                sentence=sentence,
                pattern=self.spouse_label_children_pattern,
                rule_name="spouse_label_children_pattern",
            )
        )

        return self._deduplicate(results)

    def _extract_from_pattern(
        self,
        sentence: str,
        pattern: re.Pattern,
        rule_name: str,
    ) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        for match in pattern.finditer(sentence):
            spouse_1 = clean_person_name(match.group(1))
            spouse_2 = clean_person_name(match.group(2))
            children_text = match.group(3)
            evidence = clean_evidence(match.group(0))

            children = self._split_people_list(children_text)

            results.extend(
                self._make_spouse_relations(
                    spouse_1=spouse_1,
                    spouse_2=spouse_2,
                    evidence=evidence,
                    rule_name=rule_name,
                )
            )

            for child in children:
                results.extend(
                    self._make_parent_relations(
                        parent_1=spouse_1,
                        parent_2=spouse_2,
                        child=child,
                        evidence=evidence,
                        rule_name=rule_name,
                    )
                )

        return results

    def _make_spouse_relations(
        self,
        spouse_1: str,
        spouse_2: str,
        evidence: str,
        rule_name: str,
    ) -> List[ExtractedRelation]:
        if not spouse_1 or not spouse_2 or spouse_1 == spouse_2:
            return []

        return [
            ExtractedRelation(
                source_person=spouse_1,
                relation_type="spouse_of",
                target_person=spouse_2,
                evidence=evidence,
                rule_name=rule_name,
                confidence=0.9,
            ),
            ExtractedRelation(
                source_person=spouse_2,
                relation_type="spouse_of",
                target_person=spouse_1,
                evidence=evidence,
                rule_name=rule_name,
                confidence=0.9,
            ),
        ]

    def _make_parent_relations(
        self,
        parent_1: str,
        parent_2: str,
        child: str,
        evidence: str,
        rule_name: str,
    ) -> List[ExtractedRelation]:
        if not child:
            return []

        relations: List[ExtractedRelation] = []

        if parent_1 and parent_1 != child:
            relations.append(
                ExtractedRelation(
                    source_person=parent_1,
                    relation_type="parent_of",
                    target_person=child,
                    evidence=evidence,
                    rule_name=rule_name,
                    confidence=0.9,
                )
            )

        if parent_2 and parent_2 != child:
            relations.append(
                ExtractedRelation(
                    source_person=parent_2,
                    relation_type="parent_of",
                    target_person=child,
                    evidence=evidence,
                    rule_name=rule_name,
                    confidence=0.9,
                )
            )

        return relations

    def _split_people_list(self, text: str) -> List[str]:
        text = clean_evidence(text)

        # Xóa phần định lượng ở đầu:
        # "hai người con là Nguyễn Văn Nam..." -> "Nguyễn Văn Nam..."
        # "2 người con là Nguyễn Văn Nam..." -> "Nguyễn Văn Nam..."
        text = re.sub(
            rf"^(?:(?:{NUMBER_WORD})\s+)?(?:người\s+)?con\s*(?:là|gồm|bao gồm|:)?\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # Cắt phần mô tả dư phía sau nếu có.
        text = re.split(
            r"\s+(?:sinh năm|mất năm|quê|ở|hiện|sau này|là)\s+",
            text,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        # Chuẩn hóa danh sách tên.
        text = re.sub(r"\s+và\s+", ",", text)
        text = re.sub(r"\s*,\s*", ",", text)

        parts = [clean_person_name(part) for part in text.split(",")]

        people: List[str] = []
        seen = set()

        for person in parts:
            if not person or len(person.split()) < 2:
                continue

            # Tránh nhận nhầm các cụm mô tả không phải tên người.
            if re.search(
                r"\b(con|người con|hai người con|ba người con|một người con)\b",
                person,
                flags=re.IGNORECASE,
            ):
                continue

            if person in seen:
                continue

            seen.add(person)
            people.append(person)

        return people

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