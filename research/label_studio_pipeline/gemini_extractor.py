"""LLM extraction via Google Gemini API."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from label_studio_pipeline.prompts import DEFAULT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

EntityLabel = Literal["PER_NAME", "GENERATION", "DATE", "ORDER", "LOC"]
RelationType = Literal["FATHER_OF", "MOTHER_OF", "SPOUSE"]

ALLOWED_ENTITY_LABELS: frozenset[str] = frozenset(
    {"PER_NAME", "GENERATION", "DATE", "ORDER", "LOC"}
)
ALLOWED_RELATION_TYPES: frozenset[str] = frozenset(
    {"FATHER_OF", "MOTHER_OF", "SPOUSE"}
)


class Entity(TypedDict):
    text: str
    label: EntityLabel


class Relation(TypedDict):
    type: RelationType
    head: str
    tail: str
    head_label: str
    tail_label: str


class ExtractionResult(TypedDict):
    entities: list[Entity]
    relations: list[Relation]


class GeminiExtractionError(Exception):
    """Raised when Gemini call or JSON parsing fails."""


@dataclass(frozen=True)
class GeminiConfig:
    api_key: str
    model_name: str = "gemini-2.0-flash"
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    temperature: float = 0.1


def _strip_json_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_json_payload(raw: str) -> dict[str, Any]:
    cleaned = _strip_json_fence(raw)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise GeminiExtractionError(f"Invalid JSON from Gemini: {exc}") from exc

    if not isinstance(payload, dict):
        raise GeminiExtractionError("Gemini output must be a JSON object")
    return payload


def _normalize_entities(raw_entities: Any) -> list[Entity]:
    if not isinstance(raw_entities, list):
        raise GeminiExtractionError("'entities' must be an array")

    entities: list[Entity] = []
    for idx, item in enumerate(raw_entities):
        if not isinstance(item, dict):
            logger.warning("Skipping entity[%d]: not an object", idx)
            continue

        text = str(item.get("text", "")).strip()
        label = str(item.get("label", "")).strip().upper()
        if not text:
            logger.warning("Skipping entity[%d]: empty text", idx)
            continue
        if label not in ALLOWED_ENTITY_LABELS:
            logger.warning("Skipping entity[%d]: unknown label %r", idx, label)
            continue

        entities.append({"text": text, "label": label})  # type: ignore[typeddict-item]

    return entities


def _normalize_relations(raw_relations: Any) -> list[Relation]:
    if not isinstance(raw_relations, list):
        raise GeminiExtractionError("'relations' must be an array")

    relations: list[Relation] = []
    for idx, item in enumerate(raw_relations):
        if not isinstance(item, dict):
            logger.warning("Skipping relation[%d]: not an object", idx)
            continue

        rel_type = str(item.get("type", "")).strip().upper()
        head = str(item.get("head", "")).strip()
        tail = str(item.get("tail", "")).strip()
        head_label = str(item.get("head_label", "PER_NAME")).strip().upper()
        tail_label = str(item.get("tail_label", "PER_NAME")).strip().upper()

        if rel_type not in ALLOWED_RELATION_TYPES:
            logger.warning("Skipping relation[%d]: unknown type %r", idx, rel_type)
            continue
        if not head or not tail:
            logger.warning("Skipping relation[%d]: empty head/tail", idx)
            continue

        relations.append(
            {
                "type": rel_type,  # type: ignore[typeddict-item]
                "head": head,
                "tail": tail,
                "head_label": head_label,
                "tail_label": tail_label,
            }
        )

    return relations


def normalize_extraction(payload: dict[str, Any]) -> ExtractionResult:
    """Validate and normalize raw Gemini JSON."""
    entities = _normalize_entities(payload.get("entities", []))
    relations = _normalize_relations(payload.get("relations", []))
    return {"entities": entities, "relations": relations}


def extract_genealogy_entities(
    text: str,
    config: GeminiConfig,
) -> ExtractionResult:
    """
    Send genealogy prose to Gemini and parse entities/relations JSON.

    Raises ``GeminiExtractionError`` on API or parse failures.
    """
    if not config.api_key:
        raise GeminiExtractionError("GEMINI_API_KEY is not set")

    logger.info("Calling Gemini model=%s (input_chars=%d)", config.model_name, len(text))

    try:
        genai.configure(api_key=config.api_key)
        model = genai.GenerativeModel(
            model_name=config.model_name,
            system_instruction=config.system_prompt,
        )
        response = model.generate_content(
            text,
            generation_config=genai.types.GenerationConfig(
                temperature=config.temperature,
                response_mime_type="application/json",
            ),
        )
    except google_exceptions.GoogleAPIError as exc:
        raise GeminiExtractionError(f"Gemini API error: {exc}") from exc
    except Exception as exc:  # pragma: no cover - SDK surface varies by version
        raise GeminiExtractionError(f"Gemini request failed: {exc}") from exc

    raw_text = (response.text or "").strip()
    if not raw_text:
        raise GeminiExtractionError("Gemini returned empty response")

    logger.debug("Gemini raw response (first 500 chars): %s", raw_text[:500])

    try:
        payload = _parse_json_payload(raw_text)
        result = normalize_extraction(payload)
    except GeminiExtractionError:
        raise
    except Exception as exc:
        raise GeminiExtractionError(f"Failed to normalize Gemini output: {exc}") from exc

    logger.info(
        "Gemini extraction OK: entities=%d relations=%d",
        len(result["entities"]),
        len(result["relations"]),
    )
    return result
