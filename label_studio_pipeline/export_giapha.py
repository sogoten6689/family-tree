"""CLI — export gia phả folders to data/gia_pha/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from label_studio_pipeline.corpus_store import load_json, load_pilot_trees
from label_studio_pipeline.giapha_export import DEFAULT_EXPORT_DIR, DEFAULT_LABELS_DIR, DEFAULT_SOURCE_DIR, export_trees


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export each gia phả to data/gia_pha/{tree_id}/ with metadata.json, pha_ky.txt, pha_he.json.",
    )
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR)
    parser.add_argument("--labels-dir", type=Path, default=DEFAULT_LABELS_DIR)
    parser.add_argument("--pilot-file", type=Path, default=None)
    parser.add_argument("--tree-id", type=int, action="append", dest="tree_ids")
    parser.add_argument("--no-labels", action="store_true", help="Skip labels/ subfolder.")
    parser.add_argument("--all-valid", action="store_true", help="Export all valid trees in source-dir.")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.tree_ids:
        tree_ids = args.tree_ids
    elif args.all_valid:
        from label_studio_pipeline.corpus_store import list_valid_tree_ids

        tree_ids = list_valid_tree_ids(args.source_dir)
    else:
        pilot_file = args.pilot_file or (args.source_dir / "labeled_trees.json")
        data = load_json(pilot_file) if pilot_file.is_file() else None
        if data and isinstance(data.get("selected_tree_ids"), list):
            tree_ids = [int(x) for x in data["selected_tree_ids"]]
        else:
            tree_ids = load_pilot_trees(args.source_dir)

    if not tree_ids:
        print("No tree_ids to export.", file=sys.stderr)
        sys.exit(2)

    summary = export_trees(
        tree_ids,
        source_dir=args.source_dir,
        export_dir=args.export_dir,
        labels_dir=None if args.no_labels else args.labels_dir,
        include_labels=not args.no_labels,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
