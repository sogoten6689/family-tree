"""CLI — bootstrap import registry from existing gemini_labels artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from label_studio_pipeline.corpus_store import load_json
from label_studio_pipeline.import_registry import bootstrap_registry

DEFAULT_CORPUS_DIR = Path("data/vgp_corpus")
DEFAULT_LABELS_DIR = Path("data/gemini_labels")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap Label Studio import registry.")
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--labels-dir", type=Path, default=DEFAULT_LABELS_DIR)
    parser.add_argument(
        "--pilot-file",
        type=Path,
        default=None,
        help="JSON with selected_tree_ids to mark imported (default: labeled_trees.json).",
    )
    parser.add_argument("--project-id", type=int, default=3)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    pilot_file = args.pilot_file or (args.corpus_dir / "labeled_trees.json")
    tree_ids: list[int] | None = None
    if pilot_file.is_file():
        data = load_json(pilot_file)
        if data and isinstance(data.get("selected_tree_ids"), list):
            tree_ids = [int(x) for x in data["selected_tree_ids"]]

    summary = bootstrap_registry(
        args.labels_dir,
        corpus_dir=args.corpus_dir,
        tree_ids=tree_ids,
        project_id=args.project_id,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
