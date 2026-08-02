"""Compare Gemini NER output with pha_he structured names."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from label_studio_pipeline.gemini_extractor import ExtractionResult


def _normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFC", value.lower().strip())
    text = re.sub(r"\s+", " ", text)
    for prefix in ("ông ", "bà ", "cụ ", "ông cố ", "bà cố "):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    text = re.sub(r"\s*\+\s*.*$", "", text)
    text = re.sub(r"\s*\([^)]*\)\s*$", "", text)
    return text.strip()


def _collect_diagram_names(pha_he: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for node in pha_he.get("nodes", []):
        if not isinstance(node, dict):
            continue
        for key in ("name", "label"):
            raw = node.get(key)
            if isinstance(raw, str) and raw.strip():
                normalized = _normalize_name(raw)
                if len(normalized) >= 2:
                    names.add(normalized)
                parts = re.split(r"\s*\+\s*", raw)
                for part in parts:
                    part_norm = _normalize_name(part)
                    if len(part_norm) >= 2:
                        names.add(part_norm)
    return names


def build_cross_check(
    extraction: ExtractionResult,
    pha_he: dict[str, Any],
) -> dict[str, Any]:
    """Build a simple overlap report between PER_NAME entities and diagram names."""
    diagram_names = _collect_diagram_names(pha_he)
    entity_names = [
        entity["text"]
        for entity in extraction.get("entities", [])
        if entity.get("label") == "PER_NAME"
    ]

    matched: list[str] = []
    unmatched: list[str] = []
    for name in entity_names:
        norm = _normalize_name(name)
        if norm in diagram_names:
            matched.append(name)
        else:
            fuzzy = any(norm in d or d in norm for d in diagram_names if len(norm) >= 3)
            if fuzzy:
                matched.append(name)
            else:
                unmatched.append(name)

    return {
        "diagram_node_count": int(pha_he.get("node_count") or 0),
        "diagram_name_count": len(diagram_names),
        "entity_per_name_count": len(entity_names),
        "matched_count": len(matched),
        "unmatched_count": len(unmatched),
        "matched_sample": matched[:20],
        "unmatched_sample": unmatched[:20],
    }
