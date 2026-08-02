"""CLI — classify corpus Phả ký into labeling tiers (A / B / skip)."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from label_studio_pipeline.corpus_store import load_json, tree_dir
from label_studio_pipeline.pha_ky_assessment import PhaKyAssessmentConfig, assess_pha_ky

DEFAULT_CORPUS_DIR = Path("data/vgp_corpus")
DEFAULT_GOLD_DIR = Path("data/gold_labels")

TIER_A_MIN_SCORE = 70.0
TIER_A_MIN_RELATION_CUES = 5
TIER_B_MIN_SCORE = 45.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify_pha_ky_style(text: str) -> str:
    """Heuristic prose style for tier reporting."""
    if len(text) < 200:
        return "too_short"

    lowered = text.lower()
    narrative_markers = sum(
        bool(re.search(pattern, lowered))
        for pattern in (
            r"lời nói đầu",
            r"nguyên tiền",
            r"sinh hạ",
            r"hạ sinh",
            r"kết duyên",
            r"lập gia thất",
            r"con thứ",
            r"đời thứ",
            r"thuỷ tổ|thủy tổ",
            r"ông cố",
            r"bà cố",
            r"sinh được",
        )
    )
    meta_markers = sum(
        bool(re.search(pattern, lowered))
        for pattern in (
            r"được đưa lên gia phả",
            r"liên hệ",
            r"email",
            r"mobile",
            r"người đăng ký",
            r"người ghi",
        )
    )
    list_markers = sum(
        bool(re.search(pattern, text, re.MULTILINE))
        for pattern in (r"^\s*\d+\.", r"^\s*[-–]", r"^\s*\+")
    )

    if narrative_markers >= 3:
        return "narrative_rich"
    if narrative_markers >= 1:
        return "narrative_mixed"
    if meta_markers >= 2 and narrative_markers <= 1:
        return "meta_intro"
    if list_markers >= 3:
        return "list_like"
    return "sparse"


def _has_encoding_issue(text: str) -> bool:
    sample = text[:800]
    return any(marker in sample for marker in ("Ã", "Ñ", "Ð", "Ư", "Ê")) and "ă" not in sample[:200]


def _load_gold_stats(gold_dir: Path, tree_id: int) -> dict[str, Any]:
    path = gold_dir / str(tree_id) / "gold.stats.json"
    if not path.is_file():
        return {}
    return load_json(path) or {}


def run_select_tiers(
    *,
    corpus_dir: Path,
    gold_dir: Path,
    config: PhaKyAssessmentConfig,
    tier_a_min_score: float,
    tier_a_min_cues: int,
    tier_b_min_score: float,
) -> dict[str, Any]:
    log = logging.getLogger(__name__)
    tier_a: list[dict[str, Any]] = []
    tier_b: list[dict[str, Any]] = []
    tier_skip: list[dict[str, Any]] = []

    tree_dirs = sorted(
        (path for path in corpus_dir.iterdir() if path.is_dir() and path.name.isdigit()),
        key=lambda path: int(path.name),
    )

    for tree_path in tree_dirs:
        tree_id = int(tree_path.name)
        pha_ky_path = tree_path / "pha_ky.txt"
        pha_he_path = tree_path / "pha_he.json"
        if not pha_ky_path.is_file() or not pha_he_path.is_file():
            tier_skip.append({"tree_id": tree_id, "tier": "skip", "reasons": ["missing_artifacts"]})
            continue

        text = pha_ky_path.read_text(encoding="utf-8", errors="replace")
        pha_he = load_json(pha_he_path) or {}
        meta = load_json(tree_path / "meta.json") or {}
        assessment = assess_pha_ky(text, tree_id=tree_id, pha_he=pha_he, meta=meta, config=config)
        gold = _load_gold_stats(gold_dir, tree_id)
        style = classify_pha_ky_style(text)

        record = {
            "tree_id": tree_id,
            "lineage_name": meta.get("lineage_name") or meta.get("title"),
            "style": style,
            "score": assessment.score,
            "suitable": assessment.suitable,
            "char_count": assessment.metrics.get("char_count", len(text)),
            "relation_cue_hits": assessment.metrics.get("relation_cue_hits", 0),
            "pha_he_node_count": assessment.metrics.get("pha_he_node_count", 0),
            "diagram_overlap_ratio": assessment.metrics.get("diagram_overlap", {}).get("overlap_ratio", 0),
            "gold_entity_count": gold.get("entity_count", 0),
            "gold_relation_count": gold.get("relation_count", 0),
            "encoding_issue": _has_encoding_issue(text),
            "skip_reasons": assessment.skip_reasons,
            "warnings": assessment.warnings,
        }

        if record["encoding_issue"]:
            record["skip_reasons"] = list(record["skip_reasons"]) + ["encoding_issue"]
            tier_skip.append({**record, "tier": "skip"})
            continue

        is_tier_a = (
            assessment.suitable
            and assessment.score >= tier_a_min_score
            and record["relation_cue_hits"] >= tier_a_min_cues
            and style in ("narrative_rich", "narrative_mixed")
        )
        is_tier_b = assessment.suitable and assessment.score >= tier_b_min_score and not is_tier_a

        if is_tier_a:
            record["tier"] = "A"
            tier_a.append(record)
            log.debug("tree_id=%s tier A score=%.1f", tree_id, assessment.score)
        elif is_tier_b:
            record["tier"] = "B"
            tier_b.append(record)
        else:
            tier_skip.append({**record, "tier": "skip"})

    tier_a.sort(key=lambda item: (-item["gold_relation_count"], -item["score"]))
    tier_b.sort(key=lambda item: (-item["score"], -item["relation_cue_hits"]))

    return {
        "generated_at": _now_iso(),
        "corpus_dir": str(corpus_dir),
        "criteria": {
            "tier_a": {
                "suitable": True,
                "min_score": tier_a_min_score,
                "min_relation_cues": tier_a_min_cues,
                "styles": ["narrative_rich", "narrative_mixed"],
            },
            "tier_b": {"suitable": True, "min_score": tier_b_min_score},
        },
        "counts": {
            "tier_a": len(tier_a),
            "tier_b": len(tier_b),
            "skip": len(tier_skip),
            "total": len(tier_a) + len(tier_b) + len(tier_skip),
        },
        "tier_a": tier_a,
        "tier_b": tier_b,
        "_tier_skip_full": tier_skip,
        "tier_skip_sample": tier_skip[:50],
    }


def _write_tier_files(corpus_dir: Path, summary: dict[str, Any]) -> None:
    corpus_dir.mkdir(parents=True, exist_ok=True)

    def _pack(tier: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "tier": tier,
            "generated_at": summary["generated_at"],
            "criteria": summary["criteria"].get(f"tier_{tier.lower()}", summary["criteria"]),
            "selected_tree_ids": [row["tree_id"] for row in rows],
            "selected_count": len(rows),
            "trees": rows,
        }

    (corpus_dir / "tier_a_trees.json").write_text(
        json.dumps(_pack("A", summary["tier_a"]), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (corpus_dir / "tier_b_trees.json").write_text(
        json.dumps(_pack("B", summary["tier_b"]), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (corpus_dir / "tier_summary.json").write_text(
        json.dumps({**summary, "tier_skip": summary.get("tier_skip_sample")}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    skip_rows = summary.get("_tier_skip_full") or []
    (corpus_dir / "tier_skip.json").write_text(
        json.dumps(
            {
                "generated_at": summary["generated_at"],
                "skip_count": len(skip_rows),
                "trees": skip_rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Select Phả ký labeling tiers A/B from corpus.")
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--gold-dir", type=Path, default=DEFAULT_GOLD_DIR)
    parser.add_argument("--min-chars", type=int, default=200)
    parser.add_argument("--max-chars", type=int, default=12_000)
    parser.add_argument("--tier-a-min-score", type=float, default=TIER_A_MIN_SCORE)
    parser.add_argument("--tier-a-min-cues", type=int, default=TIER_A_MIN_RELATION_CUES)
    parser.add_argument("--tier-b-min-score", type=float, default=TIER_B_MIN_SCORE)
    parser.add_argument(
        "--no-diagram-overlap",
        action="store_true",
        help="Do not require diagram name overlap during assessment.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    config = PhaKyAssessmentConfig(
        min_chars=args.min_chars,
        max_chars=args.max_chars,
        require_diagram_overlap=not args.no_diagram_overlap,
    )

    summary = run_select_tiers(
        corpus_dir=args.corpus_dir,
        gold_dir=args.gold_dir,
        config=config,
        tier_a_min_score=args.tier_a_min_score,
        tier_a_min_cues=args.tier_a_min_cues,
        tier_b_min_score=args.tier_b_min_score,
    )
    _write_tier_files(args.corpus_dir, summary)

    print(
        json.dumps(
            {
                "tier_a": summary["counts"]["tier_a"],
                "tier_b": summary["counts"]["tier_b"],
                "skip": summary["counts"]["skip"],
                "files": {
                    "tier_a": str(args.corpus_dir / "tier_a_trees.json"),
                    "tier_b": str(args.corpus_dir / "tier_b_trees.json"),
                    "summary": str(args.corpus_dir / "tier_summary.json"),
                },
                "tier_a_top": [
                    {
                        "tree_id": row["tree_id"],
                        "score": row["score"],
                        "gold_rel": row["gold_relation_count"],
                        "style": row["style"],
                    }
                    for row in summary["tier_a"][:10]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
