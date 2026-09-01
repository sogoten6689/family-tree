"""CLI — export stratified review corpus to data/review_corpus/quoc_ngu/."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from label_studio_pipeline.pilot_file import resolve_tree_ids
from label_studio_pipeline.review_corpus import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PILOT_FILE,
    DEFAULT_SOURCE_DIR,
    export_review_corpus,
)


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export stratified VGP trees for offline review (pha_ky + pha_he + images).",
    )
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--pilot-file", type=Path, default=DEFAULT_PILOT_FILE)
    parser.add_argument("--tree-id", type=int, action="append", dest="tree_ids")
    parser.add_argument(
        "--include-images",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Download XemHinhAnh gallery (default: true).",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    _configure_logging(args.verbose)

    tree_ids = resolve_tree_ids(
        corpus_dir=args.source_dir,
        pilot_file=args.pilot_file,
        tree_ids=args.tree_ids,
    )
    if not tree_ids:
        print("No tree_ids to export.", file=sys.stderr)
        sys.exit(2)

    summary = export_review_corpus(
        tree_ids,
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        include_images=args.include_images,
        pilot_file=args.pilot_file,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
