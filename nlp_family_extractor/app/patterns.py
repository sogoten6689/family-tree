from __future__ import annotations
import re

# Regex to catch Vietnamese capitalized names (heuristic)
# - 2 to 5 tokens, each token starts with a capital letter
NAME_CAPS = re.compile(
    r"\b([A-ZÀ-Ỹ][a-zà-ỹ\.]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ\.]+){1,4})\b"
)

# Catch names with title: Ông/Bà/Cụ/Anh/Chị ...
NAME_WITH_TITLE = re.compile(
    r"\b(Ông|Bà|Cụ|Anh|Chị|Chú|Cô|Bác|Cậu|Dì|Mợ|Thím|Dượng)\s+([A-ZÀ-Ỹ][\wÀ-ỹ\.]+(?:\s+[A-ZÀ-Ỹ][\wÀ-ỹ\.]+){0,4})"
)

# Pattern for relationship / event
RE_BIRTH = re.compile(r"\b(sinh|sn|sinh năm)\b", re.IGNORECASE)
RE_DEATH = re.compile(r"\b(mất|qua đời|từ trần)\b", re.IGNORECASE)

RE_CHILD_OF = re.compile(r"\b(là con của|con của)\b", re.IGNORECASE)
RE_SPOUSE = re.compile(r"\b(lấy|kết hôn với|kết hôn|cưới)\b", re.IGNORECASE)
RE_IS_SPOUSE = re.compile(r"\b(vợ của|chồng của|phối ngẫu của)\b", re.IGNORECASE)
RE_HAVE_CHILD = re.compile(r"\b(có con|sinh được con|gồm các con)\b", re.IGNORECASE)
RE_FATHER_LABEL = re.compile(r"\b(cha|bố|ba)\b", re.IGNORECASE)
RE_MOTHER_LABEL = re.compile(r"\b(mẹ|má|mẫu thân)\b", re.IGNORECASE)
RE_SIBLING = re.compile(r"\b(anh em|chị em|anh chị em|là anh của|là chị của|là em của)\b", re.IGNORECASE)
RE_SENTENCE_SPLIT = re.compile(r"[\n\.!?;]+")