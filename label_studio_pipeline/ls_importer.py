"""Label Studio project setup and pre-annotation import."""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from label_studio_sdk import LabelStudio

from label_studio_pipeline.gemini_extractor import ExtractionResult

logger = logging.getLogger(__name__)

LABEL_STUDIO_CONFIG = """\
<View>
  <Header value="Gia phả — NER &amp; Relation Extraction"/>
  <Relations name="relation" toName="text">
    <Relation value="FATHER_OF"/>
    <Relation value="MOTHER_OF"/>
    <Relation value="SPOUSE"/>
  </Relations>
  <Labels name="label" toName="text">
    <Label value="PER_NAME" background="#FFA726"/>
    <Label value="GENERATION" background="#66BB6A"/>
    <Label value="DATE" background="#42A5F5"/>
    <Label value="ORDER" background="#AB47BC"/>
    <Label value="LOC" background="#EF5350"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>
"""

ENTITY_LABEL_CONTROL = "label"
RELATION_CONTROL = "relation"
TEXT_OBJECT = "text"


@dataclass(frozen=True)
class LabelStudioConfig:
    url: str
    api_key: str
    project_id: Optional[int] = None
    project_title: str = "Family Tree NER+RE"
    model_version: str = "gemini-preannotation"


@dataclass(frozen=True)
class SpanMatch:
    text: str
    start: int
    end: int


def _new_region_id(prefix: str = "ent") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _find_span(text: str, needle: str, used_ranges: list[tuple[int, int]]) -> Optional[SpanMatch]:
    """
    Locate ``needle`` in ``text`` and return the first non-overlapping span.

    Tries exact match first, then whitespace-collapsed fuzzy match.
    """
    if not needle:
        return None

    candidates: list[tuple[int, int, str]] = []

    start = 0
    while True:
        idx = text.find(needle, start)
        if idx == -1:
            break
        candidates.append((idx, idx + len(needle), needle))
        start = idx + 1

    if not candidates:
        collapsed_text = _collapse_spaces(text)
        collapsed_needle = _collapse_spaces(needle)
        if collapsed_needle and collapsed_needle in collapsed_text:
            pos = 0
            while True:
                idx = collapsed_text.find(collapsed_needle, pos)
                if idx == -1:
                    break
                original = _map_collapsed_span_to_original(text, idx, len(collapsed_needle))
                if original is not None:
                    candidates.append(original)
                pos = idx + 1

    for start_idx, end_idx, matched in candidates:
        if any(not (end_idx <= used_start or start_idx >= used_end) for used_start, used_end in used_ranges):
            continue
        return SpanMatch(text=matched, start=start_idx, end=end_idx)

    return None


def _map_collapsed_span_to_original(
    text: str,
    collapsed_start: int,
    collapsed_length: int,
) -> Optional[tuple[int, int, str]]:
    """Map a span in whitespace-collapsed text back to original offsets."""
    collapsed_chars: list[str] = []
    index_map: list[int] = []

    i = 0
    while i < len(text):
        if text[i].isspace():
            if collapsed_chars and collapsed_chars[-1] != " ":
                collapsed_chars.append(" ")
                index_map.append(i)
            while i < len(text) and text[i].isspace():
                i += 1
            continue
        collapsed_chars.append(text[i])
        index_map.append(i)
        i += 1

    collapsed = "".join(collapsed_chars)
    if collapsed_start < 0 or collapsed_start + collapsed_length > len(collapsed):
        return None

    orig_start = index_map[collapsed_start]
    end_pos = collapsed_start + collapsed_length - 1
    orig_end = index_map[end_pos] + 1
    return orig_start, orig_end, text[orig_start:orig_end]


def _build_label_region(
    *,
    region_id: str,
    start: int,
    end: int,
    span_text: str,
    label: str,
    score: float = 0.85,
) -> dict[str, Any]:
    return {
        "id": region_id,
        "from_name": ENTITY_LABEL_CONTROL,
        "to_name": TEXT_OBJECT,
        "type": "labels",
        "value": {
            "start": start,
            "end": end,
            "text": span_text,
            "labels": [label],
            "score": score,
        },
    }


def _build_relation_region(
    *,
    from_id: str,
    to_id: str,
    relation_type: str,
) -> dict[str, Any]:
    return {
        "from_name": RELATION_CONTROL,
        "to_name": TEXT_OBJECT,
        "type": "relation",
        "direction": "right",
        "labels": [relation_type],
        "from_id": from_id,
        "to_id": to_id,
    }


def convert_to_label_studio_predictions(
    source_text: str,
    extraction: ExtractionResult,
    *,
    model_version: str = "gemini-preannotation",
) -> dict[str, Any]:
    """
    Convert Gemini entities/relations into Label Studio pre-annotation format.

    Entity spans are resolved against ``source_text`` with exact/fuzzy matching.
    """
    result: list[dict[str, Any]] = []
    used_ranges: list[tuple[int, int]] = []
    text_to_region_id: dict[str, str] = {}

    for entity in extraction["entities"]:
        entity_text = entity["text"]
        label = entity["label"]

        if entity_text in text_to_region_id:
            region_id = text_to_region_id[entity_text]
            logger.debug("Reusing region for duplicate entity text: %s", entity_text)
        else:
            match = _find_span(source_text, entity_text, used_ranges)
            if match is None:
                logger.warning("Could not locate entity span in source text: %r", entity_text)
                continue

            region_id = _new_region_id()
            used_ranges.append((match.start, match.end))
            text_to_region_id[entity_text] = region_id
            result.append(
                _build_label_region(
                    region_id=region_id,
                    start=match.start,
                    end=match.end,
                    span_text=match.text,
                    label=label,
                )
            )

    for relation in extraction["relations"]:
        head_id = text_to_region_id.get(relation["head"])
        tail_id = text_to_region_id.get(relation["tail"])
        if head_id is None or tail_id is None:
            logger.warning(
                "Skipping relation %s: missing span for head=%r tail=%r",
                relation["type"],
                relation["head"],
                relation["tail"],
            )
            continue

        result.append(
            _build_relation_region(
                from_id=head_id,
                to_id=tail_id,
                relation_type=relation["type"],
            )
        )

    logger.info(
        "Built Label Studio prediction: label_regions=%d relation_regions=%d",
        sum(1 for item in result if item.get("type") == "labels"),
        sum(1 for item in result if item.get("type") == "relation"),
    )

    return {
        "model_version": model_version,
        "score": 0.85,
        "result": result,
    }


def build_task_payload(
    *,
    text: str,
    source_url: str,
    title: str,
    extraction: ExtractionResult,
    model_version: str,
    tree_id: int | None = None,
    pha_he_url: str | None = None,
) -> dict[str, Any]:
    """Build a single Label Studio task with embedded predictions."""
    prediction = convert_to_label_studio_predictions(
        text,
        extraction,
        model_version=model_version,
    )
    data: dict[str, Any] = {
        "text": text,
        "source_url": source_url,
        "title": title,
    }
    if tree_id is not None:
        data["tree_id"] = tree_id
    if pha_he_url:
        data["pha_he_url"] = pha_he_url
    return {
        "data": data,
        "predictions": [prediction],
    }


def get_or_create_client(config: LabelStudioConfig) -> LabelStudio:
    logger.info("Connecting to Label Studio at %s", config.url)
    return LabelStudio(base_url=config.url, api_key=config.api_key)


def get_or_create_project(client: LabelStudio, config: LabelStudioConfig) -> Any:
    """Return an existing project by ID or create a new one."""
    if config.project_id is not None:
        logger.info("Using existing Label Studio project id=%s", config.project_id)
        return client.projects.get(id=config.project_id)

    logger.info("Creating Label Studio project: %s", config.project_title)
    project = client.projects.create(
        title=config.project_title,
        label_config=LABEL_STUDIO_CONFIG,
        description="Pre-annotated Vietnamese genealogy NER + relation extraction",
    )
    client.projects.validate_label_config(id=project.id, label_config=LABEL_STUDIO_CONFIG)
    logger.info("Created project id=%s", project.id)
    return project


def import_task_with_predictions(
    client: LabelStudio,
    project_id: int,
    task_payload: dict[str, Any],
) -> dict[str, Any]:
    """Import one pre-annotated task into Label Studio."""
    logger.info("Importing task into project id=%s", project_id)
    response = client.projects.import_tasks(
        id=project_id,
        request=[task_payload],
        return_task_ids=True,
    )
    payload = sdk_response_to_dict(response)
    logger.info("Import response: %s", payload)
    return payload


def sdk_response_to_dict(obj: Any) -> Any:
    """Convert label-studio-sdk response objects to JSON-serializable data."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(key): sdk_response_to_dict(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [sdk_response_to_dict(item) for item in obj]

    model_dump = getattr(obj, "model_dump", None)
    if callable(model_dump):
        return sdk_response_to_dict(model_dump())

    legacy_dict = getattr(obj, "dict", None)
    if callable(legacy_dict):
        try:
            return sdk_response_to_dict(legacy_dict())
        except TypeError:
            pass

    if hasattr(obj, "__dict__"):
        return sdk_response_to_dict(
            {key: value for key, value in obj.__dict__.items() if not key.startswith("_")}
        )

    return str(obj)
