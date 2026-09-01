"""CLI for Firecrawl source discovery."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from source_discovery.map_source import DEFAULT_OUTPUT, run_map_all
from source_discovery.registry import write_registry
from source_discovery.score_samples import run_score_all


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Discover genealogy sources via Firecrawl.")
    sub = parser.add_subparsers(dest="command", required=True)

    map_parser = sub.add_parser("map", help="Map seed URLs and filter genealogy links.")
    map_parser.add_argument("--source-id", action="append", dest="source_ids")
    map_parser.add_argument("--track", choices=["hannom", "quoc_ngu"])
    map_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    map_parser.add_argument("-v", "--verbose", action="store_true")

    score_parser = sub.add_parser("score", help="Scrape samples and score feasibility.")
    score_parser.add_argument("--source-id", action="append", dest="source_ids")
    score_parser.add_argument("--track", choices=["hannom", "quoc_ngu"])
    score_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    score_parser.add_argument("--samples", type=int, default=None)
    score_parser.add_argument("-v", "--verbose", action="store_true")

    reg_parser = sub.add_parser("registry", help="Rebuild sources_registry.json.")
    reg_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)

    all_parser = sub.add_parser("run-all", help="Map → score → registry.")
    all_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    all_parser.add_argument("--samples", type=int, default=5)
    all_parser.add_argument("-v", "--verbose", action="store_true")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    _configure_logging(getattr(args, "verbose", False))

    if args.command == "map":
        summary = run_map_all(
            output_dir=args.output_dir,
            source_ids=args.source_ids,
            track=args.track,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if summary["error_count"]:
            sys.exit(1)
    elif args.command == "score":
        summary = run_score_all(
            discovery_dir=args.output_dir,
            source_ids=args.source_ids,
            track=args.track,
            sample_limit=args.samples,
        )
        write_registry(discovery_dir=args.output_dir)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if summary["error_count"]:
            sys.exit(1)
    elif args.command == "registry":
        registry = write_registry(discovery_dir=args.output_dir)
        print(json.dumps(registry, ensure_ascii=False, indent=2))
    elif args.command == "run-all":
        run_map_all(output_dir=args.output_dir)
        summary = run_score_all(discovery_dir=args.output_dir, sample_limit=args.samples)
        registry = write_registry(discovery_dir=args.output_dir)
        print(json.dumps({"score": summary, "registry_sources": len(registry["sources"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
