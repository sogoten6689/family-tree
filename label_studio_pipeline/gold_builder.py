"""Build validated gold NER+RE annotations from Phả ký, pha_he, and Gemini."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from label_studio_pipeline.cross_check import normalize_person_name
from label_studio_pipeline.gemini_extractor import ExtractionResult, Entity, Relation
from label_studio_pipeline.ls_importer import (
    SpanMatch,
    _find_span,
    convert_to_label_studio_predictions,
)

DATE_PATTERN = re.compile(
    r"\b(?:năm\s+)?(?:\d{4}|\d{1,2}/\d{1,2}/\d{4})\b",
    re.IGNORECASE,
)
GENERATION_PATTERN = re.compile(
    r"(?:đời|Đời)\s+(?:thứ\s+)?(?:\d+|[IVXLC]+)|"
    r"[Đđ]ệ\s+(?:tam|nhất|nhì|ba|tư|ngũ|lục|thất|bát|cửu|\d+)\s+(?:đời|thế\s+kỷ)",
    re.IGNORECASE,
)
ORDER_PATTERN = re.compile(
    r"(?:con|người)\s+thứ\s+(?:nhất|nhì|ba|tư|năm|sáu|bảy|tám|chín|mười|\d+|"
    r"trưởng|hai|ba)|con\s+(?:trai|gái)\s+trưởng",
    re.IGNORECASE,
)

LS_RELATION_MAP = {
    "parent_of": "FATHER_OF",
    "mother_of": "MOTHER_OF",
    "spouse_of": "SPOUSE",
}


def _normalize_key(value: str) -> str:
    return unicodedata.normalize("NFC", value.strip().casefold())


def _name_variants(name: str) -> list[str]:
    variants = [name.strip()]
    if name != name.title():
        variants.append(name.title())
    if name != name.upper():
        variants.append(name.upper())
    return variants


def _collect_resolved_spans(
    text: str,
    entities: list[Entity],
) -> tuple[list[Entity], dict[str, SpanMatch]]:
    """Keep entities that resolve to non-overlapping spans in ``text``."""
    kept: list[Entity] = []
    span_by_text: dict[str, SpanMatch] = {}
    used_ranges: list[tuple[int, int]] = []

    for entity in entities:
        entity_text = entity["text"]
        if entity_text in span_by_text:
            kept.append(entity)
            continue

        match: SpanMatch | None = None
        for variant in _name_variants(entity_text):
            match = _find_span(text, variant, used_ranges)
            if match is not None:
                break
        if match is None:
            continue

        used_ranges.append((match.start, match.end))
        span_by_text[entity_text] = match
        kept.append({"text": match.text, "label": entity["label"]})

    return kept, span_by_text


def _extract_rule_entities(text: str, used_ranges: list[tuple[int, int]]) -> list[Entity]:
    """High-precision regex entities for DATE / GENERATION / ORDER."""
    found: list[Entity] = []
    seen: set[str] = set()

    for pattern, label in (
        (DATE_PATTERN, "DATE"),
        (GENERATION_PATTERN, "GENERATION"),
        (ORDER_PATTERN, "ORDER"),
    ):
        for match in pattern.finditer(text):
            span_text = match.group(0)
            key = _normalize_key(span_text)
            if key in seen:
                continue
            span = _find_span(text, span_text, used_ranges)
            if span is None:
                continue
            seen.add(key)
            used_ranges.append((span.start, span.end))
            found.append({"text": span.text, "label": label})
    return found


def _diagram_names(pha_he: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for node in pha_he.get("nodes", []):
        if not isinstance(node, dict):
            continue
        raw = node.get("name")
        if isinstance(raw, str) and raw.strip():
            names.add(normalize_person_name(raw))
    return names


def _build_pha_he_entities(text: str, pha_he: dict[str, Any]) -> tuple[list[Entity], dict[int, str]]:
    """Add PER_NAME spans for diagram nodes that appear in Phả ký."""
    entities: list[Entity] = []
    node_text: dict[int, str] = {}
    used_ranges: list[tuple[int, int]] = []

    for node in pha_he.get("nodes", []):
        if not isinstance(node, dict) or node.get("is_spouse_row"):
            continue
        name = node.get("name")
        node_id = node.get("node_id")
        if not isinstance(name, str) or not name.strip() or node_id is None:
            continue

        match: SpanMatch | None = None
        for variant in _name_variants(name):
            match = _find_span(text, variant, used_ranges)
            if match is not None:
                break
        if match is None:
            continue

        used_ranges.append((match.start, match.end))
        entities.append({"text": match.text, "label": "PER_NAME"})
        node_text[int(node_id)] = match.text

    return entities, node_text


def _map_diagram_relation(rel: dict[str, Any]) -> str | None:
    rel_type = str(rel.get("type") or "").lower()
    if rel_type == "spouse_of":
        return "SPOUSE"
    if rel_type != "parent_of":
        return None
    side = str(rel.get("side") or "").lower()
    if side == "mid":
        return "MOTHER_OF"
    return "FATHER_OF"


def _build_pha_he_relations(
    pha_he: dict[str, Any],
    node_text: dict[int, str],
) -> list[Relation]:
    relations: list[Relation] = []
    seen: set[tuple[str, str, str]] = set()

    for rel in pha_he.get("relationships", []):
        if not isinstance(rel, dict):
            continue
        ls_type = _map_diagram_relation(rel)
        if ls_type is None:
            continue
        head = node_text.get(int(rel.get("from_id", -1)))
        tail = node_text.get(int(rel.get("to_id", -1)))
        if not head or not tail:
            continue
        key = (ls_type, head, tail)
        if key in seen:
            continue
        seen.add(key)
        relations.append(
            {
                "type": ls_type,
                "head": head,
                "tail": tail,
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


def build_gold_extraction(
    text: str,
    pha_he: dict[str, Any],
    gemini_extraction: ExtractionResult,
) -> tuple[ExtractionResult, dict[str, Any]]:
    """
    Build validated gold extraction.

    Strategy:
    - Resolve Gemini entities to exact spans (drop unmatched).
    - Add diagram-backed PER_NAME + relations when names appear in Phả ký.
    - Add regex DATE / GENERATION / ORDER spans.
    - Keep Gemini relations only when both endpoints are present.
    """
    gemini_entities, gemini_spans = _collect_resolved_spans(text, gemini_extraction.get("entities", []))
    pha_he_entities, node_text = _build_pha_he_entities(text, pha_he)

    used_ranges = [(span.start, span.end) for span in gemini_spans.values()]
    used_ranges.extend(
        (match.start, match.end)
        for entity in pha_he_entities
        if (match := _find_span(text, entity["text"], used_ranges)) is not None
    )
    rule_entities = _extract_rule_entities(text, used_ranges)

    entities = _merge_entities(gemini_entities, pha_he_entities, rule_entities)
    per_names = {entity["text"] for entity in entities if entity["label"] == "PER_NAME"}

    diagram_relations = _build_pha_he_relations(pha_he, node_text)
    gemini_relations = _filter_relations(gemini_extraction.get("relations", []), per_names)
    relations = _merge_relations(diagram_relations, gemini_relations)

    diagram_name_set = _diagram_names(pha_he)
    matched_per = sum(
        1 for entity in entities if entity["label"] == "PER_NAME" and normalize_person_name(entity["text"]) in diagram_name_set
    )

    stats = {
        "entity_count": len(entities),
        "relation_count": len(relations),
        "per_name_count": len(per_names),
        "diagram_backed_per_name": matched_per,
        "gemini_entities_in": len(gemini_extraction.get("entities", [])),
        "gemini_relations_in": len(gemini_extraction.get("relations", [])),
        "pha_he_node_matches": len(node_text),
        "rule_entity_count": len(rule_entities),
    }
    return {"entities": entities, "relations": relations}, stats


def build_gold_ls_result(
    text: str,
    extraction: ExtractionResult,
    *,
    model_version: str = "gold-v1",
) -> list[dict[str, Any]]:
    """Convert gold extraction to Label Studio annotation ``result`` list."""
    prediction = convert_to_label_studio_predictions(
        text,
        extraction,
        model_version=model_version,
    )
    return prediction["result"]


def to_training_record(
    *,
    tree_id: int,
    text: str,
    extraction: ExtractionResult,
    source_url: str = "",
    title: str = "",
) -> dict[str, Any]:
    """Export one document in training JSON format."""
    _, span_by_text = _collect_resolved_spans(text, extraction["entities"])
    entity_index: dict[str, int] = {}
    entities_out: list[dict[str, Any]] = []

    for idx, entity in enumerate(extraction["entities"]):
        span = span_by_text.get(entity["text"])
        if span is None:
            continue
        entity_index[entity["text"]] = len(entities_out)
        entities_out.append(
            {
                "start": span.start,
                "end": span.end,
                "label": entity["label"],
                "text": span.text,
            }
        )

    relations_out: list[dict[str, Any]] = []
    for relation in extraction["relations"]:
        head_idx = entity_index.get(relation["head"])
        tail_idx = entity_index.get(relation["tail"])
        if head_idx is None or tail_idx is None:
            continue
        relations_out.append(
            {
                "type": relation["type"],
                "head": head_idx,
                "tail": tail_idx,
            }
        )

    return {
        "doc_id": f"vgp_{tree_id}",
        "tree_id": tree_id,
        "title": title,
        "source_url": source_url,
        "text": text,
        "entities": entities_out,
        "relations": relations_out,
    }
