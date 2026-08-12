"""CLI — build validated gold labels and submit to Label Studio."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from label_studio_pipeline.corpus_store import load_json, tree_dir
from label_studio_pipeline.gold_builder import build_gold_extraction, build_gold_ls_result, to_training_record
from label_studio_pipeline.ls_importer import LabelStudioConfig, get_or_create_client, get_or_create_project, sdk_response_to_dict
from label_studio_pipeline.pilot_file import resolve_tree_ids

DEFAULT_CORPUS_DIR = Path("data/vgp_corpus")
DEFAULT_LABELS_DIR = Path("data/gemini_labels")
DEFAULT_GOLD_DIR = Path("data/gold_labels")
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


def _read_pha_ky_text(corpus_dir: Path, tree_id: int, pha_ky_file: str | None) -> str:
    if pha_ky_file:
        return Path(pha_ky_file).read_text(encoding="utf-8")
    base = tree_dir(corpus_dir, tree_id)
    return (base / "pha_ky.txt").read_text(encoding="utf-8")


def _resolve_tree_ids(
    *,
    corpus_dir: Path,
    labels_dir: Path,
    tree_ids: list[int] | None,
    limit: int | None,
    pilot_file: Path | None,
    no_gemini: bool,
) -> list[int]:
    if tree_ids:
        resolved = tree_ids
    elif pilot_file and pilot_file.is_file():
        resolved = resolve_tree_ids(corpus_dir=corpus_dir, pilot_file=pilot_file)
    else:
        resolved = sorted(
            int(path.name)
            for path in labels_dir.iterdir()
            if path.is_dir() and path.name.isdigit() and (path / "pha_ky.entities.json").is_file()
        )
    if limit is not None:
        return resolved[:limit]
    return resolved


def _load_ls_task_index(client, project_id: int) -> dict[int, tuple[int, bool]]:
    """Map tree_id → (task_id, has_annotation)."""
    index: dict[int, tuple[int, bool]] = {}
    for task in client.tasks.list(project=project_id, page_size=500):
        data = task.data or {}
        tree_id = data.get("tree_id")
        if tree_id is None:
            continue
        index[int(tree_id)] = (int(task.id), bool(task.annotations))
    return index


def run_submit_gold(
    *,
    corpus_dir: Path,
    labels_dir: Path,
    gold_dir: Path,
    tree_ids: list[int],
    submit_ls: bool,
    dry_run: bool,
    pha_ky_file: str | None = None,
    skip_existing_annotations: bool = False,
    no_gemini: bool = False,
) -> dict:
    log = logging.getLogger(__name__)
    summary: dict = {"trees": [], "submitted": [], "skipped": [], "errors": []}
    training_records: list[dict] = []

    ls_config = LabelStudioConfig(
        url=os.getenv("LABEL_STUDIO_URL", "http://localhost:8080").strip(),
        api_key=os.getenv("LABEL_STUDIO_API_KEY", "").strip(),
        project_id=_env_int("LABEL_STUDIO_PROJECT_ID"),
        project_title=os.getenv("LABEL_STUDIO_PROJECT_TITLE", "Family Tree NER+RE").strip(),
    )

    client = None
    project = None
    ls_task_index: dict[int, tuple[int, bool]] = {}
    if submit_ls and not dry_run:
        if not ls_config.api_key:
            raise ValueError("LABEL_STUDIO_API_KEY is required for --submit-ls")
        client = get_or_create_client(ls_config)
        project = get_or_create_project(client, ls_config)
        ls_task_index = _load_ls_task_index(client, project.id)
        summary["project_id"] = project.id

    for tree_id in tree_ids:
        log.info("Building gold for tree_id=%s", tree_id)
        try:
            if no_gemini:
                gemini_extraction: dict = {"entities": [], "relations": []}
            else:
                gemini_path = labels_dir / str(tree_id) / "pha_ky.entities.json"
                if not gemini_path.is_file():
                    summary["skipped"].append({"tree_id": tree_id, "reason": "missing_gemini_entities"})
                    continue
                gemini_extraction = json.loads(gemini_path.read_text(encoding="utf-8"))
            text = _read_pha_ky_text(corpus_dir, tree_id, pha_ky_file if tree_ids == [tree_id] else None)
            meta = load_json(tree_dir(corpus_dir, tree_id) / "meta.json") or {}
            pha_he = load_json(tree_dir(corpus_dir, tree_id) / "pha_he.json") or {}

            if not text.strip():
                summary["skipped"].append({"tree_id": tree_id, "reason": "empty_pha_ky"})
                continue

            gold_extraction, stats = build_gold_extraction(text, pha_he, gemini_extraction)
            if stats["entity_count"] == 0:
                summary["skipped"].append({"tree_id": tree_id, "reason": "empty_gold", "stats": stats})
                continue

            ls_result = build_gold_ls_result(text, gold_extraction)
            training = to_training_record(
                tree_id=tree_id,
                text=text,
                extraction=gold_extraction,
                source_url=str(meta.get("pha_ky_url") or ""),
                title=str(meta.get("lineage_name") or meta.get("title") or f"tree_{tree_id}"),
            )

            out_dir = gold_dir / str(tree_id)
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "gold.entities.json").write_text(
                json.dumps(gold_extraction, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (out_dir / "gold.stats.json").write_text(
                json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            annotation_payload = {
                "result": ls_result,
                "ground_truth": True,
                "was_cancelled": False,
                "lead_time": 0.0,
            }
            (out_dir / "gold.ls_annotation.json").write_text(
                json.dumps(annotation_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (out_dir / "gold.training.json").write_text(
                json.dumps(training, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            tree_summary = {"tree_id": tree_id, **stats, "training_entities": len(training["entities"])}
            summary["trees"].append(tree_summary)
            training_records.append(training)

            if submit_ls and not dry_run and client is not None and project is not None:
                task_info = ls_task_index.get(tree_id)
                if task_info is None:
                    summary["errors"].append({"tree_id": tree_id, "error": "ls_task_not_found"})
                    continue
                task_id, has_annotation = task_info
                if skip_existing_annotations and has_annotation:
                    summary["skipped"].append({"tree_id": tree_id, "reason": "already_annotated"})
                    continue
                response = client.annotations.create(
                    id=task_id,
                    result=ls_result,
                    ground_truth=True,
                    was_cancelled=False,
                    lead_time=0.0,
                )
                summary["submitted"].append(
                    {
                        "tree_id": tree_id,
                        "task_id": task_id,
                        "annotation_id": getattr(response, "id", None),
                    }
                )
        except Exception as exc:
            log.exception("tree_id=%s failed: %s", tree_id, exc)
            summary["errors"].append({"tree_id": tree_id, "error": str(exc)})

    gold_dir.mkdir(parents=True, exist_ok=True)
    dataset_docs: list[dict] = []
    for tree_path in sorted(gold_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 0):
        if not tree_path.is_dir() or not tree_path.name.isdigit():
            continue
        training_path = tree_path / "gold.training.json"
        if training_path.is_file():
            dataset_docs.append(json.loads(training_path.read_text(encoding="utf-8")))
    dataset = {
        "version": 1,
        "source": "gold_builder_v1",
        "doc_count": len(dataset_docs),
        "documents": dataset_docs,
    }
    (gold_dir / "dataset.json").write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary["gold_dir"] = str(gold_dir)
    summary["dataset_doc_count"] = len(dataset_docs)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build validated gold labels and optionally submit to Label Studio.")
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--labels-dir", type=Path, default=DEFAULT_LABELS_DIR)
    parser.add_argument("--gold-dir", type=Path, default=DEFAULT_GOLD_DIR)
    parser.add_argument("--tree-id", type=int, action="append", dest="tree_ids")
    parser.add_argument(
        "--pilot-file",
        type=Path,
        default=None,
        help="JSON with selected_tree_ids (e.g. tier_a_trees.json).",
    )
    parser.add_argument("--limit", type=int, default=10, help="Max trees when --tree-id not set (default: 10).")
    parser.add_argument("--all", action="store_true", help="Process all trees with Gemini labels.")
    parser.add_argument(
        "--no-gemini",
        action="store_true",
        help="Build gold from pha_he diagram + regex rules only (skip Gemini JSON).",
    )
    parser.add_argument("--submit-ls", action="store_true", help="Submit gold annotations to Label Studio.")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip LS submit when task already has an annotation.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Compute gold files only.")
    parser.add_argument(
        "--pha-ky-file",
        type=Path,
        default=None,
        help="Override Phả ký text file (single --tree-id only).",
    )
    parser.add_argument("--env-file", type=Path, default=PACKAGE_DIR / ".env")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    _configure_logging(args.verbose)
    _load_env(args.env_file)

    limit = None if args.all or args.pilot_file or args.no_gemini else args.limit
    tree_ids = _resolve_tree_ids(
        corpus_dir=args.corpus_dir,
        labels_dir=args.labels_dir,
        tree_ids=args.tree_ids,
        limit=limit,
        pilot_file=args.pilot_file,
        no_gemini=args.no_gemini,
    )
    if not tree_ids:
        print("No tree_ids to process.", file=sys.stderr)
        sys.exit(2)
    if args.pha_ky_file and (not args.tree_ids or len(args.tree_ids) != 1):
        print("--pha-ky-file requires exactly one --tree-id.", file=sys.stderr)
        sys.exit(2)

    try:
        summary = run_submit_gold(
            corpus_dir=args.corpus_dir,
            labels_dir=args.labels_dir,
            gold_dir=args.gold_dir,
            tree_ids=tree_ids,
            submit_ls=args.submit_ls,
            dry_run=args.dry_run,
            pha_ky_file=str(args.pha_ky_file) if args.pha_ky_file else None,
            skip_existing_annotations=args.skip_existing,
            no_gemini=args.no_gemini,
        )
    except Exception as exc:
        logging.getLogger(__name__).exception("submit_gold failed: %s", exc)
        sys.exit(1)

    print(json.dumps(sdk_response_to_dict(summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
