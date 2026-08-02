"""CLI — assess Phả ký suitability before Gemini labeling."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from label_studio_pipeline.corpus_store import load_json, load_pilot_trees, tree_dir
from label_studio_pipeline.pha_ky_assessment import PhaKyAssessmentConfig, assess_pha_ky

DEFAULT_CORPUS_DIR = Path("data/vgp_corpus")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _resolve_tree_ids(corpus_dir: Path, pilot_file: Path | None, tree_ids: list[int] | None) -> list[int]:
    if tree_ids:
        return tree_ids
    pilot_path = pilot_file or (corpus_dir / "pilot_trees.json")
    data = load_json(pilot_path) if pilot_path.is_file() else None
    if data and isinstance(data.get("selected_tree_ids"), list):
        return [int(x) for x in data["selected_tree_ids"]]
    return load_pilot_trees(corpus_dir)


def run_assess(
    *,
    corpus_dir: Path,
    tree_ids: list[int],
    config: PhaKyAssessmentConfig,
    write_files: bool,
    output_file: Path | None,
) -> dict:
    log = logging.getLogger(__name__)
    results: list[dict] = []
    suitable_ids: list[int] = []

    for tree_id in tree_ids:
        base = tree_dir(corpus_dir, tree_id)
        pha_ky_path = base / "pha_ky.txt"
        if not pha_ky_path.is_file():
            log.warning("tree_id=%s missing pha_ky.txt", tree_id)
            results.append({"tree_id": tree_id, "suitable": False, "skip_reasons": ["missing_pha_ky"]})
            continue

        text = pha_ky_path.read_text(encoding="utf-8")
        meta = load_json(base / "meta.json") or {}
        pha_he = load_json(base / "pha_he.json") or {}
        assessment = assess_pha_ky(
            text,
            tree_id=tree_id,
            pha_he=pha_he,
            meta=meta,
            config=config,
        )
        payload = assessment.to_dict()
        results.append(payload)

        if write_files:
            (base / "pha_ky.assessment.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

        if assessment.suitable:
            suitable_ids.append(tree_id)
            log.info("tree_id=%s suitable score=%.1f", tree_id, assessment.score)
        else:
            log.info(
                "tree_id=%s SKIP score=%.1f reasons=%s",
                tree_id,
                assessment.score,
                ",".join(assessment.skip_reasons),
            )

    summary = {
        "assessed_count": len(results),
        "suitable_count": len(suitable_ids),
        "skipped_count": len(results) - len(suitable_ids),
        "suitable_tree_ids": suitable_ids,
        "results": results,
        "config": {
            "min_chars": config.min_chars,
            "max_chars": config.max_chars,
            "min_score": config.min_score,
            "require_diagram_overlap": config.require_diagram_overlap,
        },
    }

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        labelable = {
            "source": "assess_pha_ky",
            "selected_tree_ids": suitable_ids,
            "selected_count": len(suitable_ids),
            "assessments": {str(item["tree_id"]): item for item in results if item.get("tree_id") is not None},
        }
        output_file.write_text(json.dumps(labelable, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary["labelable_file"] = str(output_file)

    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assess Phả ký before Gemini / Label Studio.")
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--pilot-file", type=Path, default=None)
    parser.add_argument("--tree-id", type=int, action="append", dest="tree_ids")
    parser.add_argument("--min-chars", type=int, default=200)
    parser.add_argument("--max-chars", type=int, default=12_000)
    parser.add_argument("--min-score", type=float, default=45.0)
    parser.add_argument(
        "--no-diagram-overlap",
        action="store_true",
        help="Do not require diagram name overlap with Phả ký.",
    )
    parser.add_argument(
        "--write-files",
        action="store_true",
        help="Write pha_ky.assessment.json under each tree corpus dir.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write labelable_trees.json with suitable tree_ids.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    _configure_logging(args.verbose)

    tree_ids = _resolve_tree_ids(args.corpus_dir, args.pilot_file, args.tree_ids)
    if not tree_ids:
        print("No tree_ids. Pass --tree-id or --pilot-file.", file=sys.stderr)
        sys.exit(2)

    config = PhaKyAssessmentConfig(
        min_chars=args.min_chars,
        max_chars=args.max_chars,
        min_score=args.min_score,
        require_diagram_overlap=not args.no_diagram_overlap,
    )

    summary = run_assess(
        corpus_dir=args.corpus_dir,
        tree_ids=tree_ids,
        config=config,
        write_files=args.write_files,
        output_file=args.output,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
