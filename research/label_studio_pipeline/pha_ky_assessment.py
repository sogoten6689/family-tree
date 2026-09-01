"""Assess Phả ký quality before Gemini / Label Studio labeling."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any

from label_studio_pipeline.cross_check import collect_diagram_names

RELATION_CUE_PATTERN = re.compile(
    r"(?i)\b("
    r"sinh|hạ sinh|đẻ|con thứ|người thứ|con trai|con gái|"
    r"con\b|vợ|chồng|phối|lập gia thất|"
    r"đời thứ|đời\s+\d+|thế hệ|"
    r"cha\b|mẹ\b|ông\b|bà\b|"
    r"lấy vợ|lấy chồng|hôn phối"
    r")\b",
    flags=re.UNICODE,
)

GENERATION_CUE_PATTERN = re.compile(
    r"(?i)(đời thứ\s*\d+|đời\s+\d+|thế hệ\s*\d+)",
    flags=re.UNICODE,
)

BOILERPLATE_LINE_PATTERN = re.compile(
    r"(?i)("
    r"việt nam gia phả|vietnamgiapha|bản quyền|copyright|"
    r"photocopy|photo copy|trang web|website|đăng nhập|"
    r"click vào|nhấn vào|http://|https://|www\.|"
    r"cập nhật sau|đang cập nhật|"
    r"gia phả được (?:lập|sao|photo)|"
    r"nguồn:|source:"
    r")",
    flags=re.UNICODE,
)

SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?…])\s+|\n+")


@dataclass(frozen=True)
class PhaKyAssessmentConfig:
    """Thresholds for deciding whether Phả ký is worth sending to Gemini."""

    min_chars: int = 200
    max_chars: int = 12_000
    ideal_min_chars: int = 400
    ideal_max_chars: int = 6_000
    min_pha_he_nodes: int = 1
    min_relation_cue_hits: int = 1
    min_labeled_sentence_count: int = 1
    min_diagram_overlap_ratio: float = 0.08
    require_diagram_overlap: bool = True
    min_diagram_names_for_overlap: int = 3
    max_boilerplate_line_ratio: float = 0.45
    min_score: float = 45.0


@dataclass
class PhaKyAssessment:
    tree_id: int | None
    suitable: bool
    score: float
    skip_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _split_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in SENTENCE_SPLIT_PATTERN.split(text) if part.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def _count_relation_cues(text: str) -> int:
    return len(RELATION_CUE_PATTERN.findall(text))


def _count_labeled_sentences(text: str) -> int:
    return sum(1 for sentence in _split_sentences(text) if RELATION_CUE_PATTERN.search(sentence))


def _boilerplate_line_ratio(text: str) -> float:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return 0.0
    noisy = sum(1 for line in lines if BOILERPLATE_LINE_PATTERN.search(line))
    return noisy / len(lines)


def _length_score(char_count: int, config: PhaKyAssessmentConfig) -> float:
    if char_count < config.min_chars or char_count > config.max_chars:
        return 0.0
    if config.ideal_min_chars <= char_count <= config.ideal_max_chars:
        return 100.0
    if char_count < config.ideal_min_chars:
        span = max(config.ideal_min_chars - config.min_chars, 1)
        return 40.0 + 60.0 * (char_count - config.min_chars) / span
    span = max(config.max_chars - config.ideal_max_chars, 1)
    return max(20.0, 100.0 - 80.0 * (char_count - config.ideal_max_chars) / span)


def _diagram_overlap(text: str, pha_he: dict[str, Any]) -> dict[str, Any]:
    diagram_names = collect_diagram_names(pha_he)
    if not diagram_names:
        return {
            "diagram_name_count": 0,
            "matched_name_count": 0,
            "overlap_ratio": 0.0,
            "matched_sample": [],
        }

    lowered_text = unicodedata.normalize("NFC", text.lower())
    matched: list[str] = []
    for name in diagram_names:
        if len(name) < 2:
            continue
        if name in lowered_text:
            matched.append(name)
            continue
        if len(name) >= 4 and any(token in lowered_text for token in name.split() if len(token) >= 3):
            matched.append(name)

    ratio = len(matched) / len(diagram_names)
    return {
        "diagram_name_count": len(diagram_names),
        "matched_name_count": len(matched),
        "overlap_ratio": round(ratio, 4),
        "matched_sample": matched[:15],
    }


def assess_pha_ky(
    text: str,
    *,
    tree_id: int | None = None,
    pha_he: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    config: PhaKyAssessmentConfig | None = None,
) -> PhaKyAssessment:
    """
    Score Phả ký prose for NER+RE labeling suitability.

    Returns ``suitable=False`` when hard skip rules fail (Gemini should not run).
    """
    cfg = config or PhaKyAssessmentConfig()
    pha_he = pha_he or {}
    meta = meta or {}

    stripped = text.strip()
    char_count = len(stripped)
    relation_cue_hits = _count_relation_cues(stripped)
    labeled_sentence_count = _count_labeled_sentences(stripped)
    generation_cue_hits = len(GENERATION_CUE_PATTERN.findall(stripped))
    boilerplate_ratio = _boilerplate_line_ratio(stripped)
    pha_he_nodes = int(pha_he.get("node_count") or meta.get("pha_he_node_count") or 0)
    overlap = _diagram_overlap(stripped, pha_he)

    length_score = _length_score(char_count, cfg)
    cue_score = min(100.0, relation_cue_hits * 20.0)
    sentence_score = min(100.0, labeled_sentence_count * 25.0)
    overlap_score = min(100.0, overlap["overlap_ratio"] * 100.0 * 1.2)
    boilerplate_score = max(0.0, 100.0 - boilerplate_ratio * 200.0)
    diagram_score = min(100.0, pha_he_nodes * 2.0) if pha_he_nodes else 0.0

    score = round(
        length_score * 0.20
        + cue_score * 0.25
        + sentence_score * 0.20
        + overlap_score * 0.20
        + boilerplate_score * 0.10
        + diagram_score * 0.05,
        2,
    )

    skip_reasons: list[str] = []
    warnings: list[str] = []

    if char_count < cfg.min_chars:
        skip_reasons.append(f"pha_ky_too_short:{char_count}<{cfg.min_chars}")
    if char_count > cfg.max_chars:
        skip_reasons.append(f"pha_ky_too_long:{char_count}>{cfg.max_chars}")
    if pha_he_nodes < cfg.min_pha_he_nodes:
        skip_reasons.append(f"pha_he_nodes_too_few:{pha_he_nodes}<{cfg.min_pha_he_nodes}")
    if relation_cue_hits < cfg.min_relation_cue_hits:
        skip_reasons.append(
            f"relation_cues_insufficient:{relation_cue_hits}<{cfg.min_relation_cue_hits}",
        )
    if labeled_sentence_count < cfg.min_labeled_sentence_count:
        skip_reasons.append(
            f"labeled_sentences_insufficient:{labeled_sentence_count}<{cfg.min_labeled_sentence_count}",
        )
    if boilerplate_ratio > cfg.max_boilerplate_line_ratio:
        skip_reasons.append(
            f"boilerplate_ratio_high:{boilerplate_ratio:.2f}>{cfg.max_boilerplate_line_ratio:.2f}",
        )
    if (
        cfg.require_diagram_overlap
        and overlap["diagram_name_count"] >= cfg.min_diagram_names_for_overlap
        and overlap["overlap_ratio"] < cfg.min_diagram_overlap_ratio
    ):
        skip_reasons.append(
            "diagram_name_overlap_low:"
            f"{overlap['overlap_ratio']:.2f}<{cfg.min_diagram_overlap_ratio:.2f}",
        )

    if char_count > cfg.ideal_max_chars and char_count <= cfg.max_chars:
        warnings.append(f"pha_ky_long:{char_count}")
    if generation_cue_hits == 0:
        warnings.append("no_generation_cue")
    if overlap["diagram_name_count"] == 0:
        warnings.append("diagram_has_no_names")

    if not skip_reasons and score < cfg.min_score:
        skip_reasons.append(f"score_below_min:{score}<{cfg.min_score}")

    suitable = not skip_reasons

    metrics = {
        "char_count": char_count,
        "sentence_count": len(_split_sentences(stripped)),
        "relation_cue_hits": relation_cue_hits,
        "generation_cue_hits": generation_cue_hits,
        "labeled_sentence_count": labeled_sentence_count,
        "boilerplate_line_ratio": round(boilerplate_ratio, 4),
        "pha_he_node_count": pha_he_nodes,
        "diagram_overlap": overlap,
        "score_breakdown": {
            "length": round(length_score, 2),
            "relation_cues": round(cue_score, 2),
            "labeled_sentences": round(sentence_score, 2),
            "diagram_overlap": round(overlap_score, 2),
            "boilerplate": round(boilerplate_score, 2),
            "diagram_size": round(diagram_score, 2),
        },
        "lineage_name": meta.get("lineage_name") or meta.get("title"),
    }

    return PhaKyAssessment(
        tree_id=tree_id,
        suitable=suitable,
        score=score,
        skip_reasons=skip_reasons,
        warnings=warnings,
        metrics=metrics,
    )
