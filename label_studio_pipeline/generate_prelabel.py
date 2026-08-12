"""CLI — generate diagram+rule pre-labels (no Gemini) and optionally import to Label Studio."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from label_studio_pipeline.corpus_store import load_json, tree_dir
from label_studio_pipeline.cross_check import build_cross_check
from label_studio_pipeline.gold_builder import build_gold_extraction
from label_studio_pipeline.import_registry import is_tree_imported, mark_tree_imported
from label_studio_pipeline.ls_importer import (
    LabelStudioConfig,
    build_task_payload,
    get_or_create_client,
    get_or_create_project,
    import_task_with_predictions,
    sdk_response_to_dict,
)
from label_studio_pipeline.pilot_file import resolve_tree_ids

DEFAULT_CORPUS_DIR = Path("data/vgp_corpus")
DEFAULT_OUTPUT_DIR = Path("data/prelabels")
PRELABEL_MODEL_VERSION = "prelabel-v1-diagram-rule"
PACKAGE_DIR = Path(__file__).resolve().parent


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _load_env(env_file: Path) -> None:
    if env_file.is_file():
        load_dotenv(env_file)
    else:
        load_dotenv()


def _env_int(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else None


def _read_tree_corpus(corpus_dir: Path, tree_id: int) -> tuple[str, dict, dict]:
    base = tree_dir(corpus_dir, tree_id)
    pha_ky_path = base / "pha_ky.txt"
    if not pha_ky_path.is_file():
        raise FileNotFoundError(f"Missing pha_ky.txt for tree_id={tree_id}")
    text = pha_ky_path.read_text(encoding="utf-8")
    meta = load_json(base / "meta.json") or {}
    pha_he = load_json(base / "pha_he.json") or {}
    return text, meta, pha_he


def run_generate_prelabel(
    *,
    corpus_dir: Path,
    output_dir: Path,
    tree_ids: list[int],
    cross_check: bool,
    import_ls: bool,
    dry_run: bool,
    skip_imported: bool,
    force_tree_ids: set[int],
) -> dict:
    log = logging.getLogger(__name__)
    summary: dict = {
        "source": PRELABEL_MODEL_VERSION,
        "trees": [],
        "imported": [],
        "skipped": [],
        "already_imported": [],
        "errors": [],
    }
    task_payloads: list[tuple[int, dict]] = []

    ls_config = LabelStudioConfig(
        url=os.getenv("LABEL_STUDIO_URL", "http://localhost:8080").strip(),
        api_key=os.getenv("LABEL_STUDIO_API_KEY", "").strip(),
        project_id=_env_int("LABEL_STUDIO_PROJECT_ID"),
        project_title=os.getenv("LABEL_STUDIO_PROJECT_TITLE", "Family Tree NER+RE").strip(),
        model_version=PRELABEL_MODEL_VERSION,
    )

    for tree_id in tree_ids:
        log.info("Pre-labeling tree_id=%s", tree_id)
        try:
            if skip_imported and tree_id not in force_tree_ids and is_tree_imported(
                output_dir,
                tree_id,
                corpus_dir=corpus_dir,
            ):
                log.info("Skipping tree_id=%s — already imported", tree_id)
                summary["already_imported"].append({"tree_id": tree_id, "reason": "already_imported"})
                continue

            text, meta, pha_he = _read_tree_corpus(corpus_dir, tree_id)
            if not text.strip():
                summary["skipped"].append({"tree_id": tree_id, "reason": "empty_pha_ky"})
                continue

            empty_gemini: dict = {"entities": [], "relations": []}
            extraction, stats = build_gold_extraction(text, pha_he, empty_gemini)
            stats["source"] = PRELABEL_MODEL_VERSION

            out_tree = output_dir / str(tree_id)
            out_tree.mkdir(parents=True, exist_ok=True)
            (out_tree / "pha_ky.entities.json").write_text(
                json.dumps(extraction, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (out_tree / "prelabel.stats.json").write_text(
                json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            source_url = str(meta.get("pha_ky_url") or "")
            title = str(meta.get("lineage_name") or meta.get("title") or f"tree_{tree_id}")
            pha_he_url = str(meta.get("pha_he_url") or pha_he.get("source_url") or "")

            task_payload = build_task_payload(
                text=text,
                source_url=source_url,
                title=title,
                extraction=extraction,
                model_version=ls_config.model_version,
                tree_id=tree_id,
                pha_he_url=pha_he_url,
            )
            (out_tree / "pha_ky.ls_task.json").write_text(
                json.dumps(task_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            tree_summary = {
                "tree_id": tree_id,
                "text_length": len(text),
                **stats,
                "prediction_regions": len(task_payload["predictions"][0]["result"]),
            }

            if cross_check:
                cross = build_cross_check(extraction, pha_he)
                (out_tree / "cross_check.json").write_text(
                    json.dumps(cross, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                tree_summary["cross_check"] = cross

            summary["trees"].append(tree_summary)
            task_payloads.append((tree_id, task_payload))
        except (FileNotFoundError, ValueError) as exc:
            log.error("tree_id=%s: %s", tree_id, exc)
            summary["errors"].append({"tree_id": tree_id, "error": str(exc)})

    if dry_run or not import_ls:
        summary["dry_run"] = dry_run
        summary["import_ls"] = import_ls
        summary["output_dir"] = str(output_dir)
        return summary

    if not ls_config.api_key:
        raise ValueError("LABEL_STUDIO_API_KEY is required for --import-ls")

    client = get_or_create_client(ls_config)
    project = get_or_create_project(client, ls_config)
    summary["project_id"] = project.id

    for tree_id, task_payload in task_payloads:
        response = import_task_with_predictions(client, project.id, task_payload)
        summary["imported"].append(response)
        ls_task_ids: list[int] = []
        if isinstance(response, dict):
            raw_ids = response.get("task_ids") or response.get("ids") or []
            if isinstance(raw_ids, list):
                ls_task_ids = [int(x) for x in raw_ids if str(x).isdigit()]
        mark_tree_imported(
            output_dir,
            tree_id=tree_id,
            project_id=project.id,
            corpus_dir=corpus_dir,
            source="generate_prelabel",
            ls_task_ids=ls_task_ids,
        )

    summary["output_dir"] = str(output_dir)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate diagram+rule pre-labels without Gemini and optionally import to Label Studio.",
    )
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for pre-label JSON outputs (default: data/prelabels).",
    )
    parser.add_argument("--tree-id", type=int, action="append", dest="tree_ids")
    parser.add_argument(
        "--pilot-file",
        type=Path,
        default=None,
        help="JSON with tree_ids.all or selected_tree_ids (e.g. stratified_sample.json).",
    )
    parser.add_argument("--cross-check", action="store_true", help="Write cross_check.json per tree.")
    parser.add_argument("--import-ls", action="store_true", help="Import tasks with predictions into Label Studio.")
    parser.add_argument("--dry-run", action="store_true", help="Generate files only; skip LS import even with --import-ls.")
    parser.add_argument(
        "--skip-imported",
        action="store_true",
        help="Skip trees already recorded in import_registry.json.",
    )
    parser.add_argument(
        "--force",
        type=int,
        action="append",
        dest="force_tree_ids",
        help="Re-process these tree_ids even when --skip-imported.",
    )
    parser.add_argument("--env-file", type=Path, default=PACKAGE_DIR / ".env")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    _configure_logging(args.verbose)
    _load_env(args.env_file)

    tree_ids = resolve_tree_ids(
        corpus_dir=args.corpus_dir,
        pilot_file=args.pilot_file,
        tree_ids=args.tree_ids,
    )
    if not tree_ids:
        print("No tree_ids to process.", file=sys.stderr)
        sys.exit(2)

    try:
        summary = run_generate_prelabel(
            corpus_dir=args.corpus_dir,
            output_dir=args.output_dir,
            tree_ids=tree_ids,
            cross_check=args.cross_check,
            import_ls=args.import_ls,
            dry_run=args.dry_run,
            skip_imported=args.skip_imported,
            force_tree_ids=set(args.force_tree_ids or []),
        )
    except Exception as exc:
        logging.getLogger(__name__).exception("generate_prelabel failed: %s", exc)
        sys.exit(1)

    print(json.dumps(sdk_response_to_dict(summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
