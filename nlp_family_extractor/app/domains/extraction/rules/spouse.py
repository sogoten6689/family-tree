from __future__ import annotations

import re
from typing import List

from app.domains.extraction.schemas import ExtractedRelation
from app.domains.extraction.rules.patterns import PERSON_NAME


TITLE_PATTERN = re.compile(
    r"^(ông|bà|cụ|anh|chị|chú|cô|bác|cậu|dì|mợ|thím|dượng)\s+",
    re.IGNORECASE,
)


def clean_name(name: str) -> str:
    name = name.strip(" .,:;!?\"'")
    name = TITLE_PATTERN.sub("", name)
    return name.strip()


class SpouseRule:
    name = "spouse_rule"

    def __init__(self) -> None:
        self.patterns = [
            re.compile(
                rf"{PERSON_NAME}\s+kết hôn với\s+{PERSON_NAME}",
                re.IGNORECASE,
            ),
            re.compile(
                rf"{PERSON_NAME}\s+lấy\s+{PERSON_NAME}",
                re.IGNORECASE,
            ),
            re.compile(
                rf"{PERSON_NAME}\s+cưới\s+{PERSON_NAME}",
                re.IGNORECASE,
            ),
            re.compile(
                rf"{PERSON_NAME}\s+là\s+vợ\s+của\s+{PERSON_NAME}",
                re.IGNORECASE,
            ),
            re.compile(
                rf"{PERSON_NAME}\s+là\s+chồng\s+của\s+{PERSON_NAME}",
                re.IGNORECASE,
            ),
        ]

    def extract(self, sentence: str) -> List[ExtractedRelation]:
        results: List[ExtractedRelation] = []

        for pattern in self.patterns:
            for match in pattern.finditer(sentence):
                source = clean_name(match.group(1))
                target = clean_name(match.group(2))
                evidence = match.group(0)

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

        return results