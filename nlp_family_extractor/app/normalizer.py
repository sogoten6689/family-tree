from __future__ import annotations
import re
from typing import Optional

TITLE_WORDS = {
    "ông", "bà", "cụ", "anh", "chị", "chú", "cô", "bác", "cậu", "mợ", "dì", "thím", "dượng"
}

GENDER_HINT_M = {"ông", "anh", "chú", "bác", "cậu", "dượng"}
GENDER_HINT_F = {"bà", "chị", "cô", "dì", "mợ", "thím"}

def normalize_text(text: str) -> str:
    # normalize spaces + basic punctuation
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n+\s*", "\n", text).strip()
    return text

def normalize_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\s+", " ", name)
    # remove title from name
    parts = name.split()
    if parts and parts[0].lower() in TITLE_WORDS:
        name = " ".join(parts[1:])
    return name.strip(" ,.;:-()[]{}\"'")

def infer_gender_from_title(raw_name: str) -> Optional[str]:
    parts = raw_name.strip().split()
    if not parts:
        return None
    first = parts[0].lower()
    if first in GENDER_HINT_M:
        return "M"
    if first in GENDER_HINT_F:
        return "F"
    return None

def find_year(text: str) -> Optional[int]:
    m = re.search(r"\b(18|19|20)\d{2}\b", text)
    return int(m.group()) if m else None