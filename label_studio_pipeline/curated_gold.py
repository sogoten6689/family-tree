"""Curated gold spans for short / clear Phả ký (manual quality)."""

from __future__ import annotations

from typing import Any

from label_studio_pipeline.gemini_extractor import ExtractionResult
from label_studio_pipeline.ls_importer import _find_span

# Manual review notes live in data/gold_labels/LABELING_ANALYSIS.md


def _add_entity(
    text: str,
    entities: list[dict],
    used: list[tuple[int, int]],
    needle: str,
    label: str,
) -> str | None:
    match = _find_span(text, needle, used)
    if match is None:
        return None
    used.append((match.start, match.end))
    entities.append({"text": match.text, "label": label})
    return match.text


def _add_rel(
    relations: list[dict],
    rel_type: str,
    head: str | None,
    tail: str | None,
    seen: set[tuple[str, str, str]],
) -> None:
    if not head or not tail or head == tail:
        return
    key = (rel_type, head, tail)
    if key in seen:
        return
    seen.add(key)
    relations.append(
        {
            "type": rel_type,
            "head": head,
            "tail": tail,
            "head_label": "PER_NAME",
            "tail_label": "PER_NAME",
        }
    )


def curated_extraction_321(text: str) -> ExtractionResult:
    """Gold for Thái - Đồng Tháp (tree 321) — short, relation-complete."""
    entities: list[dict] = []
    used: list[tuple[int, int]] = []

    loc = _add_entity(text, entities, used, "Đồng Tháp", "LOC")
    gen = _add_entity(text, entities, used, "đời thứ 7", "GENERATION")
    _ = loc, gen

    for order in ("con cả",):
        # two occurrences
        while _add_entity(text, entities, used, order, "ORDER"):
            pass

    names = [
        "Thái Văn keo",
        "Thái Văn Lâu",
        "Thái Văn Tô",
        "Thái Văn Hữu",
        "Thái Văn Ngãi",
        "Thái Văn Xiêm",
        "Thái Văn Lương",
        "Thái Văn Nhân",
        "Thái Văn Hưng",
        "Thái Văn Đê",
        "Thái Thị Hồ Thu",
    ]
    resolved: dict[str, str] = {}
    for name in names:
        got = _add_entity(text, entities, used, name, "PER_NAME")
        if got:
            resolved[name] = got

    relations: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    keo = resolved.get("Thái Văn keo")
    lau = resolved.get("Thái Văn Lâu")
    to = resolved.get("Thái Văn Tô")
    huu = resolved.get("Thái Văn Hữu")
    ngai = resolved.get("Thái Văn Ngãi")
    xiem = resolved.get("Thái Văn Xiêm")
    luong = resolved.get("Thái Văn Lương")
    nhan = resolved.get("Thái Văn Nhân")
    hung = resolved.get("Thái Văn Hưng")
    de = resolved.get("Thái Văn Đê")
    thu = resolved.get("Thái Thị Hồ Thu")

    _add_rel(relations, "FATHER_OF", keo, lau, seen)
    _add_rel(relations, "FATHER_OF", keo, to, seen)
    _add_rel(relations, "FATHER_OF", to, huu, seen)
    _add_rel(relations, "FATHER_OF", to, ngai, seen)
    _add_rel(relations, "FATHER_OF", to, xiem, seen)
    _add_rel(relations, "FATHER_OF", huu, luong, seen)
    _add_rel(relations, "FATHER_OF", ngai, nhan, seen)
    _add_rel(relations, "FATHER_OF", xiem, hung, seen)
    _add_rel(relations, "FATHER_OF", xiem, de, seen)
    _add_rel(relations, "FATHER_OF", xiem, thu, seen)

    return {"entities": entities, "relations": relations}


def curated_extraction_1622(text: str) -> ExtractionResult:
    """Gold for HOÀNG - Hải Dương (tree 1622, S4) — clear SPOUSE + parent cues."""
    entities: list[dict] = []
    used: list[tuple[int, int]] = []

    for loc in ("Cao An", "Cẩm Giàng", "Hải Dương"):
        _add_entity(text, entities, used, loc, "LOC")

    for gen in ("đời thứ 7", "đời I", "đời II", "đời III", "Đời 4", "Đời 5"):
        _add_entity(text, entities, used, gen, "GENERATION")

    for date in ("1886", "1969", "1885", "1962", "1913", "2001"):
        _add_entity(text, entities, used, date, "DATE")

    names = [
        "Hoàng Húy Tức",
        "Phạm Thị Còi",
        "Hoàng Văn Ánh",
        "Phạm Thị Sáo",
        "Tức",  # only if standalone — skip if already covered
    ]
    resolved: dict[str, str] = {}
    for name in ("Hoàng Húy Tức", "Phạm Thị Còi", "Hoàng Văn Ánh", "Phạm Thị Sáo"):
        got = _add_entity(text, entities, used, name, "PER_NAME")
        if got:
            resolved[name] = got

    # short mention "Tức" in "con trai tên là Tức" — optional PER if distinct span
    _add_entity(text, entities, used, "Tức", "PER_NAME")

    relations: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    tuc = resolved.get("Hoàng Húy Tức")
    coi = resolved.get("Phạm Thị Còi")
    anh = resolved.get("Hoàng Văn Ánh")
    sao = resolved.get("Phạm Thị Sáo")
    _add_rel(relations, "SPOUSE", tuc, coi, seen)
    _add_rel(relations, "FATHER_OF", tuc, anh, seen)
    _add_rel(relations, "MOTHER_OF", coi, anh, seen)
    _add_rel(relations, "SPOUSE", anh, sao, seen)

    return {"entities": entities, "relations": relations}


CURATED_BUILDERS: dict[int, Any] = {
    321: curated_extraction_321,
    1622: curated_extraction_1622,
}


def try_curated_extraction(tree_id: int, text: str) -> ExtractionResult | None:
    builder = CURATED_BUILDERS.get(tree_id)
    if builder is None:
        return None
    return builder(text)
