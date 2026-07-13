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


def clean_evidence(text: str) -> str:
    text = re.sub(r"\s+", " ", text)

    # Fix chữ thường dính chữ hoa:
    # vớiLê -> với Lê
    # ThịHoa -> Thị Hoa
    # ôngNguyễn -> ông Nguyễn
    text = re.sub(r"(?<=[a-zà-ỹ])(?=[A-ZÀ-Ỹ])", " ", text)

    # Fix title bị dính với tên
    text = re.sub(
        r"\b(ông|bà|cụ|anh|chị|chú|cô|bác|cậu|dì|mợ|thím|dượng)\s*(?=[A-ZÀ-Ỹ])",
        r"\1 ",
        text,
        flags=re.IGNORECASE,
    )

    # Fix keyword bị dính với tên sau
    text = re.sub(r"\bcủa\s*([A-ZÀ-Ỹ])", r"của \1", text)
    text = re.sub(r"\bvới\s*([A-ZÀ-Ỹ])", r"với \1", text)
    text = re.sub(r"\blà\s*([A-ZÀ-Ỹ])", r"là \1", text)

    # Fix một số cụm hay gặp
    text = text.replace("kết hônvới", "kết hôn với")
    text = text.replace("bàTrần", "bà Trần")
    text = text.replace("ôngNguyễn", "ông Nguyễn")

    return text.strip(" .,:;!?\"'")


def clean_name(name: str) -> str:
    name = name.strip(" .,:;!?\"'")

    # Cắt phần dư sau tên.
    # Ví dụ: "Phạm Văn Hùng và có" -> "Phạm Văn Hùng"
    name = re.split(
        r"\s+(?:và\s+có|và\s+sinh|sinh\s+được|sinh\s+ra|có\s+con)\b",
        name,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]

    name = TITLE_PATTERN.sub("", name)
    name = re.sub(r"\s+", " ", name)

    return name.strip()


class SpouseRule:
    name = "spouse_rule"

    def __init__(self) -> None:
        # Không dùng re.IGNORECASE ở đây,
        # vì nó có thể làm PERSON ăn nhầm chữ thường như "và có".
        self.patterns = [
            re.compile(
                rf"{PERSON}\s+kết\s+hôn\s+với\s+{PERSON}",
            ),
            re.compile(
                rf"{PERSON}\s+thành\s+hôn\s+với\s+{PERSON}",
            ),
            re.compile(
                rf"{PERSON}\s+lấy\s+{PERSON}",
            ),
            re.compile(
                rf"{PERSON}\s+cưới\s+{PERSON}",
            ),
            re.compile(
                rf"{PERSON}\s+là\s+vợ\s+của\s+{PERSON}",
            ),
            re.compile(
                rf"{PERSON}\s+là\s+chồng\s+của\s+{PERSON}",
            ),
        ]

    def extract(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        for pattern in self.patterns:
            for match in pattern.finditer(sentence):
                source = clean_name(match.group(1))
                target = clean_name(match.group(2))
                evidence = clean_evidence(match.group(0))

                if not source or not target or source == target:
                    continue

                results.append(
                    ExtractedRelation(
                        source_person=source,
                        relation_type="spouse_of",
                        target_person=target,
                        evidence=evidence,
                        rule_name=self.name,
                        confidence=0.95,
                    )
                )

                results.append(
                    ExtractedRelation(
                        source_person=target,
                        relation_type="spouse_of",
                        target_person=source,
                        evidence=evidence,
                        rule_name=self.name,
                        confidence=0.95,
                    )
                )

        return self._deduplicate(results)

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