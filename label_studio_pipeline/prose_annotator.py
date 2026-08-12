"""Prose-based NER+RE for human-quality genealogy annotation (no LLM API)."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from label_studio_pipeline.cross_check import normalize_person_name
from label_studio_pipeline.gemini_extractor import Entity, ExtractionResult, Relation
from label_studio_pipeline.gold_builder import build_gold_extraction
from label_studio_pipeline.ls_importer import SpanMatch, _find_span

# Common Vietnamese surnames — frozenset for O(1) lookup (no catastrophic regex backtracking)
_SURNAMES = frozenset(
    {
        "nguyễn", "nguyên", "trần", "trấn", "lê", "phạm", "pham", "hoàng", "huỳnh", "hồng",
        "phan", "vũ", "vu", "võ", "đặng", "dặng", "bùi", "đỗ", "hồ", "ngô", "dương", "lý",
        "đinh", "đoàn", "doãn", "thái", "tạ", "mai", "trương", "trinh", "phùng", "thân",
        "hà", "đào", "châu", "triệu", "hứa", "tôn", "mạc", "đặng", "la",
    }
)

_HONORIFIC_PREFIX = re.compile(r"^(?:Ông|Bà|Cụ|ông|bà|cụ)\s+", re.IGNORECASE)

GENERATION_LINE_PATTERN = re.compile(
    r"(?:[Đđ]ời|đời)\s+thứ\s+(\d+)\s*[:\-]?\s*\n?\s*([^\n\.:;]+)",
    re.IGNORECASE | re.UNICODE,
)

LOC_PATTERN = re.compile(
    r"(?:xã|huyện|tỉnh|thành phố|tp\.?|làng|thôn|phường|quận|tổ|đội)\s+[A-ZÀ-Ỹa-zà-ỹ0-9\s\-]+|"
    r"\b(?:Đồng Tháp|Thái Bình|Nghệ An|Hà Tĩnh|Hải Dương|Quảng Nam|Quảng Ngãi|"
    r"Thanh Hóa|Hà Tây|Hà Nam|Bình Định|Hưng Yên|Hải Phòng|Nam Định|"
    r"Tây Ninh|Đà Nẵng|Hà Nội|Sài Gòn|TP\.?\s*HCM)\b",
    re.IGNORECASE | re.UNICODE,
)

# False-positive name/LOC fragments
_STOP_NAME_FRAGMENTS = frozenset(
    {
        "nhà trần",
        "nhà hồ",
        "nhà minh",
        "nhà lê",
        "quân minh",
        "quân ngô",
        "thế kỷ",
        "đất nước",
        "dòng họ",
        "họ nguyễn",
        "họ trần",
        "họ thái",
        "họ doãn",
        "họ tạ",
        "họ nguyễn",
        "nguồn gốc",
        "tổ tiên",
        "con cháu",
        "người con",
        "người di cư",
        "dòng họ thái",
        "dòng họ nguyễn",
        "dòng họ trần",
    }
)

_MIDDLE_NAME_PARTS = frozenset({"văn", "thị", "ngọc", "đức", "công", "minh", "hữu"})

_BAD_NAME_TOKENS = frozenset(
    {
        "đến",
        "có",
        "sinh",
        "sống",
        "là",
        "theo",
        "từ",
        "nay",
        "còn",
        "vẫn",
        "hiện",
        "trong",
        "suốt",
        "năm",
        "đời",
        "người",
        "con",
        "ông",
        "bà",
        "cụ",
        "lưu",
        "lại",
        "lúc",
        "nào",
        "được",
        "tên",
        "biết",
        "những",
        "nét",
        "suy",
        "yếu",
        "chiếm",
        "ngôi",
        "quân",
        "minh",
        "nhà",
        "hồ",
        "trần",
        "lý",
        "gì",
        "vào",
        "hiểu",
        "ở",
        "khi",
        "mạc",
        "di",
        "cư",
        "trấn",
        "huyện",
        "đây",
        "và",
        "phó",
        "tấn",
        "quốc",
        "công",
        "thiên",
        "quốc",
    }
)

FATHER_CUE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"(?P<parent>[^,\n\.;]{2,60}?)\s+có\s+con\s+cả\s+là\s+(?:Ông|Bà|ông|bà|cụ\s+)?(?P<child>[^,\n\.;]{2,60})",
            re.IGNORECASE | re.UNICODE,
        ),
        "FATHER_OF",
    ),
    (
        re.compile(
            r"(?P<parent>[^,\n\.;]{2,60}?)\s+có\s+(?:\d+\s+)?(?:người\s+)?con(?:\s+trai|\s+gái)?(?:\s+là|\s*:)\s*(?P<children>[^\n\.]+)",
            re.IGNORECASE | re.UNICODE,
        ),
        "FATHER_OF",
    ),
    (
        re.compile(
            r"(?P<parent>[^,\n\.;]{2,60}?)\s+sinh(?:\s+được|\s+ra)?\s+(?:Ông|Bà|ông|bà|cụ\s+)?(?P<child>[^,\n\.;]{2,60})",
            re.IGNORECASE | re.UNICODE,
        ),
        "FATHER_OF",
    ),
    (
        re.compile(
            r"(?P<child>[^,\n\.;]{2,60}?)\s+là\s+con(?:\s+cả|\s+thứ\s+\w+)?\s+của\s+(?:Ông|Bà|ông|bà|cụ\s+)?(?P<parent>[^,\n\.;]{2,60})",
            re.IGNORECASE | re.UNICODE,
        ),
        "FATHER_OF",
    ),
    (
        re.compile(
            r"(?P<parent>[^,\n\.;]{2,60}?)\s+hạ\s+sinh\s+(?:Ông|Bà|ông|bà|cụ\s+)?(?P<child>[^,\n\.;]{2,60})",
            re.IGNORECASE | re.UNICODE,
        ),
        "MOTHER_OF",
    ),
]

SPOUSE_CUE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"(?P<a>[^,\n\.;]{2,60}?)\s+(?:lập\s+gia\s+thất|hôn\s+phối|kết\s+hôn)\s+(?:với\s+)?(?:bà|ông|Bà|Ông\s+)?(?P<b>[^,\n\.;]{2,60})",
        re.IGNORECASE | re.UNICODE,
    ),
    re.compile(
        r"(?P<a>[^,\n\.;]{2,60}?)\s+lấy\s+(?:vợ|chồng)\s+(?:là\s+)?(?:bà|ông|Bà|Ông\s+)?(?P<b>[^,\n\.;]{2,60})",
        re.IGNORECASE | re.UNICODE,
    ),
    re.compile(
        r"(?P<a>[^,\n\.;]{2,60}?)\s+(?:lấy|cưới)\s+(?:bà|ông|Bà|Ông\s+)?(?P<b>[^,\n\.;]{2,60})\s+làm\s+(?:vợ|chồng)",
        re.IGNORECASE | re.UNICODE,
    ),
]

CHILD_LIST_SPLIT = re.compile(r"[;,]\s*|\s+và\s+", re.UNICODE)


def _normalize_key(value: str) -> str:
    return unicodedata.normalize("NFC", value.strip().casefold())


def _tokenize_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-zÀ-ỹÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴàáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]+", text)


def _is_surname(token: str) -> bool:
    return _normalize_key(token) in _SURNAMES


def _is_name_token(token: str, idx: int) -> bool:
    if idx == 0:
        return _is_surname(token) and (token[0].isupper() or token.isupper())
    key = _normalize_key(token)
    if key in _BAD_NAME_TOKENS:
        return False
    if token[0].isupper() or token.isupper():
        return True
    if key in _MIDDLE_NAME_PARTS:
        return True
    return len(token) >= 2 and token.islower()


def _name_from_tokens(tokens: list[str], start: int) -> str | None:
    if start >= len(tokens) or not _is_surname(tokens[start]):
        return None
    if not _is_name_token(tokens[start], 0):
        return None
    # Surname + Thị/Văn + up to 3 given tokens (e.g. Thái Thị Hồ Thu)
    max_len = 5
    end = start + 1
    while end < len(tokens) and end - start < max_len:
        if not _is_name_token(tokens[end], end - start):
            break
        end += 1
    if end - start < 2:
        return None
    return " ".join(tokens[start:end])


def _should_scan_segment(segment: str) -> bool:
    s = segment.strip()
    if not s or len(s) > 120:
        return False
    if _HONORIFIC_PREFIX.match(s):
        return True
    if re.search(r"\bcó\s+(?:\d+\s+)?(?:người\s+)?con\b", s, re.IGNORECASE):
        return True
    if re.search(r"\bcon cả là\b", s, re.IGNORECASE):
        return True
    if ";" in s:
        return True
    words = _tokenize_words(s)
    if len(words) <= 6 and words and _is_surname(words[0]):
        return True
    return False


def _candidate_names_from_segment(segment: str) -> list[str]:
    """Left-to-right greedy names; do not restart at surname mid-name (e.g. Hồ in Thái Thị Hồ Thu)."""
    segment = _HONORIFIC_PREFIX.sub("", segment.strip())
    segment = re.split(r"\s*\(", segment)[0].strip()
    tokens = _tokenize_words(segment)
    names: list[str] = []
    idx = 0
    while idx < len(tokens):
        # Skip restarting when previous token is a middle-name part
        if idx > 0 and _normalize_key(tokens[idx - 1]) in _MIDDLE_NAME_PARTS:
            idx += 1
            continue
        name = _name_from_tokens(tokens, idx)
        if name and _is_plausible_name(name):
            names.append(name)
            idx += len(name.split())
        else:
            idx += 1
    return names


def _candidate_names_from_text(text: str) -> list[str]:
    names: list[str] = []
    for line in text.splitlines():
        for part in re.split(r"[;,]", line):
            if not _should_scan_segment(part):
                continue
            names.extend(_candidate_names_from_segment(part))
    return names


def _clean_name(raw: str) -> str:
    name = raw.strip()
    name = name.split("\n")[0].strip()
    name = re.sub(r"^[\(\[\{]+|[\)\]\}\.]+$", "", name).strip()
    name = re.sub(r"^(?:Ông|Bà|Cụ|ông|bà|cụ)\s+", "", name, flags=re.IGNORECASE).strip()
    return name


def _is_plausible_name(name: str) -> bool:
    cleaned = _clean_name(name)
    if len(cleaned) < 3 or len(cleaned) > 40:
        return False
    if "\n" in cleaned:
        return False
    key = _normalize_key(cleaned)
    if key in _STOP_NAME_FRAGMENTS:
        return False
    tokens = cleaned.split()
    if len(tokens) < 2 or not _is_surname(tokens[0]):
        return False
    if len(tokens) > 5:
        return False
    if any(_normalize_key(tok) in _BAD_NAME_TOKENS for tok in tokens[1:]):
        return False
    if sum(ch.isdigit() for ch in cleaned) > len(cleaned) // 3:
        return False
    return True


def _resolve_name_in_text(
    text: str,
    candidate: str,
    used_ranges: list[tuple[int, int]],
    *,
    from_diagram: bool = False,
) -> SpanMatch | None:
    cleaned = _clean_name(candidate)
    if not from_diagram and not _is_plausible_name(cleaned):
        return None
    if from_diagram and len(cleaned) < 2:
        return None
    variants = [cleaned, cleaned.title(), cleaned.upper()]
    if " " in cleaned:
        # Try without honorific middle words sometimes duplicated
        parts = cleaned.split()
        if len(parts) >= 3:
            variants.append(" ".join(parts[:3]))
    seen: set[str] = set()
    for variant in variants:
        if variant in seen:
            continue
        seen.add(variant)
        match = _find_span(text, variant, used_ranges)
        if match is not None:
            return match
    return None


def _diagram_name_candidates(pha_he: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for node in pha_he.get("nodes", []):
        if not isinstance(node, dict) or node.get("is_spouse_row"):
            continue
        raw = node.get("name")
        if isinstance(raw, str) and raw.strip():
            names.append(raw.strip())
    return names


def _extract_prose_names(text: str, pha_he: dict[str, Any]) -> list[Entity]:
    entities: list[Entity] = []
    used_ranges: list[tuple[int, int]] = []
    seen: set[tuple[str, str]] = set()

    candidates: list[tuple[str, bool]] = []
    for name in _diagram_name_candidates(pha_he):
        candidates.append((name, True))
    for name in _candidate_names_from_text(text):
        candidates.append((name, False))

    for _, raw_name in GENERATION_LINE_PATTERN.findall(text):
        candidates.append((raw_name, False))

    for candidate, from_diagram in candidates:
        span = _resolve_name_in_text(text, candidate, used_ranges, from_diagram=from_diagram)
        if span is None:
            continue
        key = (_normalize_key(span.text), "PER_NAME")
        if key in seen:
            continue
        seen.add(key)
        used_ranges.append((span.start, span.end))
        entities.append({"text": span.text, "label": "PER_NAME"})

    return entities


def _extract_loc_entities(text: str, used_ranges: list[tuple[int, int]]) -> list[Entity]:
    entities: list[Entity] = []
    seen: set[str] = set()
    for match in LOC_PATTERN.finditer(text):
        span_text = match.group(0).strip()
        key = _normalize_key(span_text)
        if key in seen:
            continue
        span = _find_span(text, span_text, used_ranges)
        if span is None:
            continue
        seen.add(key)
        used_ranges.append((span.start, span.end))
        entities.append({"text": span.text, "label": "LOC"})
    return entities


def _last_name_in_fragment(fragment: str) -> str | None:
    """Pick the last plausible person name from a relation cue fragment."""
    candidates = _candidate_names_from_segment(fragment)
    return candidates[-1] if candidates else None


def _best_name_match(text: str, fragment: str, per_names: set[str]) -> str | None:
    cleaned = _clean_name(fragment)
    if not cleaned:
        return None
    for name in per_names:
        if _normalize_key(name) == _normalize_key(cleaned):
            return name
    picked = _last_name_in_fragment(fragment)
    if picked:
        for name in per_names:
            if _normalize_key(name) == _normalize_key(picked):
                return name
        span = _resolve_name_in_text(text, picked, [])
        if span is not None:
            for name in per_names:
                if _normalize_key(name) == _normalize_key(span.text):
                    return name
            return span.text
    return None


def _extract_generation_chain_relations(text: str, per_names: set[str]) -> list[Relation]:
    """Link consecutive 'Đời thứ N' entries as FATHER_OF when names resolve."""
    generations: list[tuple[int, str]] = []
    for gen_str, raw_name in GENERATION_LINE_PATTERN.findall(text):
        name = _best_name_match(text, raw_name, per_names)
        if name:
            generations.append((int(gen_str), name))

    if len(generations) < 2:
        return []

    generations.sort(key=lambda x: x[0])
    relations: list[Relation] = []
    seen: set[tuple[str, str, str]] = set()
    for idx in range(len(generations) - 1):
        _, parent = generations[idx]
        _, child = generations[idx + 1]
        if parent == child:
            continue
        key = ("FATHER_OF", parent, child)
        if key in seen:
            continue
        seen.add(key)
        relations.append(
            {
                "type": "FATHER_OF",
                "head": parent,
                "tail": child,
                "head_label": "PER_NAME",
                "tail_label": "PER_NAME",
            }
        )
    return relations


def _extract_cue_relations(text: str, per_names: set[str]) -> list[Relation]:
    relations: list[Relation] = []
    seen: set[tuple[str, str, str]] = set()

    for pattern, rel_type in FATHER_CUE_PATTERNS:
        for match in pattern.finditer(text):
            groups = match.groupdict()
            parent_raw = groups.get("parent") or ""
            child_raw = groups.get("child") or groups.get("children") or ""
            parent = _best_name_match(text, parent_raw, per_names)
            if not parent:
                continue

            child_names: list[str] = []
            if "children" in groups and groups["children"]:
                for part in CHILD_LIST_SPLIT.split(groups["children"]):
                    child = _best_name_match(text, part, per_names)
                    if child:
                        child_names.append(child)
            else:
                child = _best_name_match(text, child_raw, per_names)
                if child:
                    child_names.append(child)

            for child in child_names:
                if not child or parent == child:
                    continue
                key = (rel_type, parent, child)
                if key in seen:
                    continue
                seen.add(key)
                relations.append(
                    {
                        "type": rel_type,
                        "head": parent,
                        "tail": child,
                        "head_label": "PER_NAME",
                        "tail_label": "PER_NAME",
                    }
                )

    for pattern in SPOUSE_CUE_PATTERNS:
        for match in pattern.finditer(text):
            a = _best_name_match(text, match.group("a"), per_names)
            b = _best_name_match(text, match.group("b"), per_names)
            if not a or not b or a == b:
                continue
            key = ("SPOUSE", a, b)
            if key in seen:
                continue
            seen.add(key)
            relations.append(
                {
                    "type": "SPOUSE",
                    "head": a,
                    "tail": b,
                    "head_label": "PER_NAME",
                    "tail_label": "PER_NAME",
                }
            )
    return relations


def _merge_entities(*groups: list[Entity]) -> list[Entity]:
    merged: list[Entity] = []
    seen: set[tuple[str, str]] = set()
    for group in groups:
        for entity in group:
            key = (_normalize_key(entity["text"]), entity["label"])
            if key in seen:
                continue
            seen.add(key)
            merged.append(entity)
    return merged


def _merge_relations(*groups: list[Relation]) -> list[Relation]:
    merged: list[Relation] = []
    seen: set[tuple[str, str, str]] = set()
    for group in groups:
        for relation in group:
            key = (relation["type"], relation["head"], relation["tail"])
            if key in seen:
                continue
            seen.add(key)
            merged.append(relation)
    return merged


def _filter_relations(relations: list[Relation], per_names: set[str]) -> list[Relation]:
    kept: list[Relation] = []
    for relation in relations:
        if relation["head"] not in per_names or relation["tail"] not in per_names:
            continue
        kept.append(relation)
    return kept


def _filter_false_date_entities(entities: list[Entity], text: str) -> list[Entity]:
    """Drop DATE spans that are clearly demographic counts, not years."""
    kept: list[Entity] = []
    for entity in entities:
        if entity["label"] != "DATE":
            kept.append(entity)
            continue
        span = entity["text"]
        if re.fullmatch(r"\d{4}", span):
            # Find context after the number
            pos = text.find(span)
            if pos >= 0:
                after = text[pos + len(span) : pos + len(span) + 12].lower()
                if any(token in after for token in (" hộ", " nhân", " vị", " đạo", " tập")):
                    continue
        kept.append(entity)
    return kept


def _dedupe_per_vs_loc(entities: list[Entity], text: str) -> list[Entity]:
    """Drop PER_NAME when the same span is a known place phrase."""
    known_places = {
        "thái bình", "hà tây", "hà nội", "nghệ an", "thanh hóa", "quảng nam", "hải dương",
        "hải phòng", "hà tĩnh", "quảng ngãi", "bình định", "hưng yên", "hà nam", "đồng tháp",
        "thái lan", "hà tiên", "thái nguyên", "sài gòn", "tp hcm", "hồ chí minh",
    }
    kept: list[Entity] = []
    for entity in entities:
        if entity["label"] == "PER_NAME" and _normalize_key(entity["text"]) in known_places:
            continue
        kept.append(entity)
    return kept


def build_human_review_extraction(
    text: str,
    pha_he: dict[str, Any],
) -> tuple[ExtractionResult, dict[str, Any]]:
    """
    Build human-review-quality extraction from prose + pha_he + rules.

    Layers:
    1. Diagram + regex baseline (gold_builder, empty Gemini)
    2. Prose PER_NAME + LOC
    3. Generation-chain + cue-based relations
    """
    baseline, base_stats = build_gold_extraction(text, pha_he, {"entities": [], "relations": []})

    prose_names = _extract_prose_names(text, pha_he)
    used_ranges = [
        (match.start, match.end)
        for entity in baseline["entities"]
        if (match := _find_span(text, entity["text"], [])) is not None
    ]
    loc_entities = _extract_loc_entities(text, used_ranges)

    entities = _merge_entities(baseline["entities"], prose_names, loc_entities)
    entities = _filter_false_date_entities(entities, text)
    entities = _dedupe_per_vs_loc(entities, text)

    per_names = {entity["text"] for entity in entities if entity["label"] == "PER_NAME"}
    gen_relations = _extract_generation_chain_relations(text, per_names)
    cue_relations = _extract_cue_relations(text, per_names)
    relations = _merge_relations(baseline["relations"], gen_relations, cue_relations)
    relations = _filter_relations(relations, per_names)

    diagram_name_set = {normalize_person_name(n) for n in _diagram_name_candidates(pha_he)}
    matched_per = sum(
        1
        for entity in entities
        if entity["label"] == "PER_NAME" and normalize_person_name(entity["text"]) in diagram_name_set
    )

    stats = {
        **base_stats,
        "entity_count": len(entities),
        "relation_count": len(relations),
        "per_name_count": len(per_names),
        "diagram_backed_per_name": matched_per,
        "prose_name_count": len(prose_names),
        "loc_count": len(loc_entities),
        "generation_relations": len(gen_relations),
        "cue_relations": len(cue_relations),
        "source": "human_review_v1_prose",
    }
    return {"entities": entities, "relations": relations}, stats
