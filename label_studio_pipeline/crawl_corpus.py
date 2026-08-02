"""CLI — crawl tree_id range 100–200 into local corpus."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from label_studio_pipeline.corpus_store import (
    DEFAULT_PILOT_LIMIT,
    list_valid_tree_ids,
    select_batch_from_corpus,
    select_pilot_trees,
)
from label_studio_pipeline.tree_crawler import crawl_tree

DEFAULT_CORPUS_DIR = Path("data/vgp_corpus")
DEFAULT_START = 100
DEFAULT_END = 200


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_crawl(
    *,
    start: int,
    end: int,
    corpus_dir: Path,
    delay: float,
    timeout: float,
    pilot_limit: int,
    skip_unchanged: bool,
    exclude_tree_ids: list[int] | None = None,
    pilot_output: str = "pilot_trees.json",
    batch_limit: int = 0,
    batch_min_tree_id: int | None = None,
    batch_output: str = "batch_trees.json",
) -> dict:
    log = logging.getLogger(__name__)
    corpus_dir.mkdir(parents=True, exist_ok=True)

    summary: dict = {
        "start": start,
        "end": end,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "saved": [],
        "skipped_unchanged": [],
        "skipped_empty": [],
        "errors": [],
    }

    for tree_id in range(start, end + 1):
        try:
            result = crawl_tree(
                tree_id,
                corpus_root=corpus_dir,
                timeout=timeout,
                skip_unchanged=skip_unchanged,
            )
            bucket = {
                "tree_id": tree_id,
                "reason": result.reason,
                "pha_ky_chars": result.pha_ky_chars,
                "pha_he_nodes": result.pha_he_nodes,
            }
            if result.status == "saved":
                summary["saved"].append(bucket)
            elif result.status == "skipped_unchanged":
                summary["skipped_unchanged"].append(bucket)
            elif result.status == "skipped_empty":
                summary["skipped_empty"].append(bucket)
            else:
                summary["errors"].append({**bucket, "status": result.status})
        except Exception as exc:  # pragma: no cover - network safety
            log.exception("tree_id=%s failed", tree_id)
            summary["errors"].append({"tree_id": tree_id, "error": str(exc)})

        if delay > 0:
            time.sleep(delay)

    excluded = set(exclude_tree_ids or [])
    pilot = select_pilot_trees(
        corpus_dir,
        start=start,
        end=end,
        limit=pilot_limit,
        exclude=excluded,
        output_name=pilot_output,
    )
    summary["pilot"] = pilot

    if batch_limit > 0:
        batch_exclude = excluded | set(pilot.get("selected_tree_ids", []))
        batch = select_batch_from_corpus(
            corpus_dir,
            limit=batch_limit,
            exclude=batch_exclude,
            min_tree_id=batch_min_tree_id,
            output_name=batch_output,
        )
        summary["batch"] = batch
        log.info("Batch selected=%d target=%d", batch.get("selected_count", 0), batch_limit)

    summary_path = corpus_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log.info(
        "Crawl done saved=%d skipped_unchanged=%d skipped_empty=%d errors=%d pilot=%d",
        len(summary["saved"]),
        len(summary["skipped_unchanged"]),
        len(summary["skipped_empty"]),
        len(summary["errors"]),
        pilot.get("selected_count", 0),
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Crawl vietnamgiapha tree_id range into local corpus.")
    parser.add_argument("--start", type=int, default=DEFAULT_START, help="Start tree_id (inclusive).")
    parser.add_argument("--end", type=int, default=DEFAULT_END, help="End tree_id (inclusive).")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_CORPUS_DIR,
        help="Corpus output directory.",
    )
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between trees (seconds).")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout per request.")
    parser.add_argument(
        "--pilot-limit",
        type=int,
        default=DEFAULT_PILOT_LIMIT,
        help="Number of pilot trees to select after crawl.",
    )
    parser.add_argument(
        "--pilot-output",
        default="pilot_trees.json",
        help="Filename for pilot selection under output-dir.",
    )
    parser.add_argument(
        "--batch-limit",
        type=int,
        default=0,
        help="If >0, also write batch_trees.json with N additional valid trees.",
    )
    parser.add_argument(
        "--batch-min-tree-id",
        type=int,
        default=None,
        help="Minimum tree_id for batch selection (e.g. 201).",
    )
    parser.add_argument(
        "--batch-output",
        default="batch_trees.json",
        help="Filename for batch selection under output-dir.",
    )
    parser.add_argument(
        "--exclude-tree-id",
        type=int,
        action="append",
        dest="exclude_tree_ids",
        help="Exclude tree_id from pilot/batch selection (repeatable).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-save even when content_hash unchanged.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    _configure_logging(args.verbose)
    if args.start > args.end:
        print("--start must be <= --end", file=sys.stderr)
        sys.exit(2)

    summary = run_crawl(
        start=args.start,
        end=args.end,
        corpus_dir=args.output_dir,
        delay=args.delay,
        timeout=args.timeout,
        pilot_limit=args.pilot_limit,
        skip_unchanged=not args.force,
        exclude_tree_ids=args.exclude_tree_ids,
        pilot_output=args.pilot_output,
        batch_limit=args.batch_limit,
        batch_min_tree_id=args.batch_min_tree_id,
        batch_output=args.batch_output,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
