"""CLI — generate synthetic Phả ký + gold labels from pha_he diagrams."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from label_studio_pipeline.corpus_store import load_json, tree_dir
from label_studio_pipeline.synthetic_pha_ky import (
    export_synthetic_tree,
    select_synthetic_candidates_from_corpus,
)

DEFAULT_CORPUS_DIR = Path("data/vgp_corpus")
DEFAULT_OUTPUT_DIR = Path("data/synthetic_pha_ky")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_generate(
    *,
    corpus_dir: Path,
    output_dir: Path,
    tree_ids: list[int],
    max_nodes: int,
) -> dict:
    log = logging.getLogger(__name__)
    exported: list[dict] = []
    errors: list[dict] = []

    for tree_id in tree_ids:
        log.info("Generating synthetic pha_ky tree_id=%s", tree_id)
        try:
            base = tree_dir(corpus_dir, tree_id)
            pha_he_path = base / "pha_he.json"
            if not pha_he_path.is_file():
                errors.append({"tree_id": tree_id, "error": "missing_pha_he"})
                continue
            pha_he = load_json(pha_he_path) or {}
            meta = load_json(base / "meta.json") or {}
            metadata = export_synthetic_tree(
                tree_id=tree_id,
                pha_he=pha_he,
                meta=meta,
                output_dir=output_dir,
                max_nodes=max_nodes,
            )
            exported.append(metadata)
        except Exception as exc:
            log.exception("tree_id=%s: %s", tree_id, exc)
            errors.append({"tree_id": tree_id, "error": str(exc)})

    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_docs = []
    for tree_path in sorted(output_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 0):
        if not tree_path.is_dir() or not tree_path.name.isdigit():
            continue
        training_path = tree_path / "gold.training.json"
        if training_path.is_file():
            dataset_docs.append(json.loads(training_path.read_text(encoding="utf-8")))

    dataset = {
        "version": 1,
        "source": "synthetic_from_pha_he",
        "generated_at": _now_iso(),
        "doc_count": len(dataset_docs),
        "documents": dataset_docs,
    }
    (output_dir / "dataset.json").write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "exported_count": len(exported),
        "error_count": len(errors),
        "output_dir": str(output_dir),
        "tree_ids": [item["tree_id"] for item in exported],
        "exported": exported,
        "errors": errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate synthetic Phả ký from pha_he diagrams.")
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--tree-id", type=int, action="append", dest="tree_ids")
    parser.add_argument(
        "--auto-select",
        action="store_true",
        help="Select diagram-heavy trees with poor real Phả ký (default when no --tree-id).",
    )
    parser.add_argument("--min-nodes", type=int, default=20)
    parser.add_argument("--max-relation-cues", type=int, default=2)
    parser.add_argument("--limit", type=int, default=30, help="Max trees for --auto-select.")
    parser.add_argument("--max-nodes", type=int, default=500, help="Cap nodes/relations per tree.")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    _configure_logging(args.verbose)

    if args.tree_ids:
        tree_ids = args.tree_ids
    else:
        tree_ids = select_synthetic_candidates_from_corpus(
            args.corpus_dir,
            min_nodes=args.min_nodes,
            max_relation_cues=args.max_relation_cues,
            limit=args.limit,
        )

    if not tree_ids:
        print("No tree_ids to generate.", file=sys.stderr)
        sys.exit(2)

    summary = run_generate(
        corpus_dir=args.corpus_dir,
        output_dir=args.output_dir,
        tree_ids=tree_ids,
        max_nodes=args.max_nodes,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
