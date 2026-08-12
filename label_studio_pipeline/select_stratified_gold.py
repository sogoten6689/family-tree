"""Select stratified gold corpus (S1–S4) for human review and evaluation."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from label_studio_pipeline.corpus_store import load_json

DEFAULT_TIER_SUMMARY = Path("data/vgp_corpus/tier_summary.json")
DEFAULT_GOLD_DIR = Path("data/gold_labels")
DEFAULT_OUTPUT = Path("data/gold_labels/stratified_sample.json")

S1_COUNT = 8
S2_COUNT = 7
S3_COUNT = 5
S4_COUNT = 5
DOUBLE_ANNOTATION_COUNT = 5


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _load_gold_relation_count(gold_dir: Path, tree_id: int) -> int:
    stats_path = gold_dir / str(tree_id) / "gold.stats.json"
    if not stats_path.is_file():
        return 0
    stats = load_json(stats_path) or {}
    return int(stats.get("relation_count") or 0)


def _enrich_entry(entry: dict, gold_dir: Path) -> dict:
    tree_id = int(entry["tree_id"])
    relation_count = entry.get("gold_relation_count")
    if relation_count is None:
        relation_count = _load_gold_relation_count(gold_dir, tree_id)
    return {
        **entry,
        "tree_id": tree_id,
        "gold_relation_count": int(relation_count or 0),
    }


def _pick_unique(candidates: list[dict], count: int, used: set[int]) -> list[dict]:
    picked: list[dict] = []
    for item in candidates:
        tree_id = int(item["tree_id"])
        if tree_id in used:
            continue
        picked.append(item)
        used.add(tree_id)
        if len(picked) >= count:
            break
    return picked


def _fill_from_pool(
    pool: list[dict],
    *,
    count: int,
    used: set[int],
    predicate,
) -> list[dict]:
    filtered = [item for item in pool if predicate(item) and int(item["tree_id"]) not in used]
    return _pick_unique(filtered, count, used)


def select_stratified(
    tier_a: list[dict],
    *,
    gold_dir: Path,
) -> dict:
    enriched = [_enrich_entry(item, gold_dir) for item in tier_a]
    used: set[int] = set()

    s1_pool = sorted(
        [item for item in enriched if item["gold_relation_count"] >= 5],
        key=lambda item: (-item["gold_relation_count"], -float(item.get("score") or 0)),
    )
    s1 = _pick_unique(s1_pool, S1_COUNT, used)
    for item in s1:
        item["stratum"] = "S1"
        item["split"] = "train"
        item["review_priority"] = 1

    s2 = _fill_from_pool(
        enriched,
        count=S2_COUNT,
        used=used,
        predicate=lambda item: 2 <= item["gold_relation_count"] <= 4 and float(item.get("score") or 0) >= 75,
    )
    if len(s2) < S2_COUNT:
        extra = _fill_from_pool(
            sorted(enriched, key=lambda item: (-float(item.get("score") or 0), -item["gold_relation_count"])),
            count=S2_COUNT - len(s2),
            used=used,
            predicate=lambda item: item["gold_relation_count"] >= 1 and float(item.get("score") or 0) >= 70,
        )
        s2.extend(extra)
    for item in s2:
        item["stratum"] = "S2"
        item["split"] = "train"
        item["review_priority"] = 2

    s3_pool = sorted(
        [
            item
            for item in enriched
            if item.get("encoding_issue")
            or item.get("style") == "narrative_mixed"
            or float(item.get("diagram_overlap_ratio") or 1) < 0.15
        ],
        key=lambda item: (
            0 if item.get("encoding_issue") else 1,
            float(item.get("diagram_overlap_ratio") or 0),
        ),
    )
    s3 = _pick_unique(s3_pool, S3_COUNT, used)
    if len(s3) < S3_COUNT:
        extra = _fill_from_pool(
            sorted(enriched, key=lambda item: float(item.get("diagram_overlap_ratio") or 0)),
            count=S3_COUNT - len(s3),
            used=used,
            predicate=lambda item: float(item.get("diagram_overlap_ratio") or 1) < 0.3,
        )
        s3.extend(extra)
    for item in s3:
        item["stratum"] = "S3"
        item["split"] = "train"
        item["review_priority"] = 3

    s4_pool = sorted(
        [item for item in s1_pool if int(item["tree_id"]) not in used],
        key=lambda item: (-item["gold_relation_count"], -float(item.get("score") or 0)),
    )
    s4 = _pick_unique(s4_pool, S4_COUNT, used)
    if len(s4) < S4_COUNT:
        extra = _fill_from_pool(
            sorted(enriched, key=lambda item: (-float(item.get("score") or 0), -item["char_count"])),
            count=S4_COUNT - len(s4),
            used=used,
            predicate=lambda item: float(item.get("score") or 0) >= 80,
        )
        s4.extend(extra)
    for item in s4:
        item["stratum"] = "S4"
        item["split"] = "test"
        item["review_priority"] = 1

    all_selected = s1 + s2 + s3 + s4
    double_candidates = sorted(
        [item for item in all_selected if item["stratum"] in {"S1", "S4"}],
        key=lambda item: (0 if item["stratum"] == "S4" else 1, -item["gold_relation_count"]),
    )[:DOUBLE_ANNOTATION_COUNT]
    double_ids = {int(item["tree_id"]) for item in double_candidates}

    documents: list[dict] = []
    for item in all_selected:
        tree_id = int(item["tree_id"])
        documents.append(
            {
                "doc_id": f"vgp_{tree_id}",
                "tree_id": tree_id,
                "stratum": item["stratum"],
                "split": item["split"],
                "review_priority": item["review_priority"],
                "double_annotation": tree_id in double_ids,
                "lineage_name": item.get("lineage_name"),
                "style": item.get("style"),
                "score": item.get("score"),
                "char_count": item.get("char_count"),
                "relation_cue_hits": item.get("relation_cue_hits"),
                "gold_relation_count": item["gold_relation_count"],
                "diagram_overlap_ratio": item.get("diagram_overlap_ratio"),
                "encoding_issue": bool(item.get("encoding_issue")),
                "gold_source": "auto_gold_pending_review",
            }
        )

    review_queue = sorted(documents, key=lambda item: (item["review_priority"], -item["gold_relation_count"]))

    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol": "stratified_gold_v1",
        "counts": {
            "S1": len(s1),
            "S2": len(s2),
            "S3": len(s3),
            "S4": len(s4),
            "total": len(documents),
            "double_annotation": len(double_ids),
        },
        "tree_ids": {
            "S1": [int(x["tree_id"]) for x in s1],
            "S2": [int(x["tree_id"]) for x in s2],
            "S3": [int(x["tree_id"]) for x in s3],
            "S4": [int(x["tree_id"]) for x in s4],
            "double_annotation": sorted(double_ids),
            "all": [int(x["tree_id"]) for x in all_selected],
        },
        "documents": documents,
        "review_queue": review_queue,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Select stratified gold sample for human review.")
    parser.add_argument("--tier-summary", type=Path, default=DEFAULT_TIER_SUMMARY)
    parser.add_argument("--gold-dir", type=Path, default=DEFAULT_GOLD_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    _configure_logging(args.verbose)

    summary = load_json(args.tier_summary)
    if not summary:
        print(f"Missing tier summary: {args.tier_summary}", file=sys.stderr)
        sys.exit(2)

    tier_a = summary.get("tier_a") or []
    if not tier_a:
        print("No tier_a entries in tier summary.", file=sys.stderr)
        sys.exit(2)

    result = select_stratified(tier_a, gold_dir=args.gold_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
