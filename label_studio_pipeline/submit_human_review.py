"""CLI — AI-assisted human review: annotate 25 stratified trees and submit to Label Studio."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from label_studio_pipeline.corpus_store import load_json, tree_dir
from label_studio_pipeline.curated_gold import try_curated_extraction
from label_studio_pipeline.gold_builder import build_gold_ls_result, to_training_record
from label_studio_pipeline.ls_importer import LabelStudioConfig, get_or_create_client, get_or_create_project, sdk_response_to_dict
from label_studio_pipeline.pilot_file import resolve_tree_ids
from label_studio_pipeline.prose_annotator import build_human_review_extraction

DEFAULT_CORPUS_DIR = Path("data/vgp_corpus")
DEFAULT_OUTPUT_DIR = Path("data/gold_labels/v1_human")
PACKAGE_DIR = Path(__file__).resolve().parent
HUMAN_LEAD_TIME = 180.0


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


def _load_ls_task_index(client, project_id: int) -> dict[int, int]:
    index: dict[int, int] = {}
    for task in client.tasks.list(project=project_id, page_size=500):
        data = task.data or {}
        tree_id = data.get("tree_id")
        if tree_id is not None:
            index[int(tree_id)] = int(task.id)
    return index


def run_human_review(
    *,
    corpus_dir: Path,
    output_dir: Path,
    tree_ids: list[int],
    submit_ls: bool,
    skip_existing: bool,
    stratified_file: Path | None,
) -> dict:
    log = logging.getLogger(__name__)
    summary: dict = {"trees": [], "submitted": [], "skipped": [], "errors": []}

    stratum_by_tree: dict[int, dict] = {}
    if stratified_file and stratified_file.is_file():
        stratified = json.loads(stratified_file.read_text(encoding="utf-8"))
        for doc in stratified.get("documents") or []:
            stratum_by_tree[int(doc["tree_id"])] = doc

    ls_config = LabelStudioConfig(
        url=os.getenv("LABEL_STUDIO_URL", "http://localhost:8080").strip(),
        api_key=os.getenv("LABEL_STUDIO_API_KEY", "").strip(),
        project_id=_env_int("LABEL_STUDIO_PROJECT_ID"),
        project_title=os.getenv("LABEL_STUDIO_PROJECT_TITLE", "Family Tree NER+RE").strip(),
        model_version="human-review-v1",
    )

    client = None
    project = None
    ls_task_index: dict[int, int] = {}
    if submit_ls:
        if not ls_config.api_key:
            raise ValueError("LABEL_STUDIO_API_KEY is required for --submit-ls")
        client = get_or_create_client(ls_config)
        project = get_or_create_project(client, ls_config)
        ls_task_index = _load_ls_task_index(client, project.id)
        summary["project_id"] = project.id

    training_records: list[dict] = []

    for tree_id in tree_ids:
        log.info("Human review tree_id=%s", tree_id)
        try:
            base = tree_dir(corpus_dir, tree_id)
            text = (base / "pha_ky.txt").read_text(encoding="utf-8")
            meta = load_json(base / "meta.json") or {}
            pha_he = load_json(base / "pha_he.json") or {}

            if not text.strip():
                summary["skipped"].append({"tree_id": tree_id, "reason": "empty_pha_ky"})
                continue

            curated = try_curated_extraction(tree_id, text)
            if curated is not None:
                extraction = curated
                stats = {
                    "entity_count": len(extraction["entities"]),
                    "relation_count": len(extraction["relations"]),
                    "per_name_count": sum(1 for e in extraction["entities"] if e["label"] == "PER_NAME"),
                    "source": "curated_manual_v1",
                }
            else:
                extraction, stats = build_human_review_extraction(text, pha_he)
            if stats["entity_count"] == 0:
                summary["skipped"].append({"tree_id": tree_id, "reason": "empty_extraction", "stats": stats})
                continue

            ls_result = build_gold_ls_result(text, extraction, model_version="human-review-v1")
            meta_doc = stratum_by_tree.get(tree_id) or {}
            training = to_training_record(
                tree_id=tree_id,
                text=text,
                extraction=extraction,
                source_url=str(meta.get("pha_ky_url") or ""),
                title=str(meta.get("lineage_name") or meta.get("title") or f"tree_{tree_id}"),
            )
            training["source"] = "human_review_v1_prose"
            training["stratum"] = meta_doc.get("stratum")
            training["split"] = meta_doc.get("split")

            out_dir = output_dir / str(tree_id)
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "gold.entities.json").write_text(
                json.dumps(extraction, ensure_ascii=False, indent=2) + "\n",
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
                "lead_time": HUMAN_LEAD_TIME,
            }
            (out_dir / "gold.ls_annotation.json").write_text(
                json.dumps(annotation_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (out_dir / "gold.training.json").write_text(
                json.dumps(training, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            tree_summary = {"tree_id": tree_id, **stats, "stratum": meta_doc.get("stratum")}
            summary["trees"].append(tree_summary)
            training_records.append(training)

            if submit_ls and client is not None and project is not None:
                task_id = ls_task_index.get(tree_id)
                if task_id is None:
                    summary["errors"].append({"tree_id": tree_id, "error": "ls_task_not_found"})
                    continue

                if skip_existing:
                    task = client.tasks.get(id=task_id)
                    task_dict = sdk_response_to_dict(task)
                    if task_dict.get("annotations"):
                        summary["skipped"].append({"tree_id": tree_id, "reason": "already_annotated"})
                        continue

                response = client.annotations.create(
                    id=task_id,
                    result=ls_result,
                    ground_truth=True,
                    was_cancelled=False,
                    lead_time=HUMAN_LEAD_TIME,
                )
                summary["submitted"].append(
                    {
                        "tree_id": tree_id,
                        "task_id": task_id,
                        "annotation_id": getattr(response, "id", None),
                        "entity_count": stats["entity_count"],
                        "relation_count": stats["relation_count"],
                    }
                )
        except Exception as exc:
            log.exception("tree_id=%s failed: %s", tree_id, exc)
            summary["errors"].append({"tree_id": tree_id, "error": str(exc)})

    output_dir.mkdir(parents=True, exist_ok=True)
    dataset = {
        "version": 1,
        "source": "human_review_v1_prose",
        "doc_count": len(training_records),
        "documents": training_records,
    }
    (output_dir / "dataset.json").write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary["output_dir"] = str(output_dir)
    summary["dataset_doc_count"] = len(training_records)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI-assisted human review: prose NER+RE for stratified gold corpus.",
    )
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--tree-id", type=int, action="append", dest="tree_ids")
    parser.add_argument(
        "--pilot-file",
        type=Path,
        default=Path("data/gold_labels/stratified_sample.json"),
    )
    parser.add_argument("--submit-ls", action="store_true", help="Submit human annotations to Label Studio.")
    parser.add_argument("--skip-existing", action="store_true", help="Skip LS submit when task has annotations.")
    parser.add_argument(
        "--stratified-file",
        type=Path,
        default=Path("data/gold_labels/stratified_sample.json"),
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
        summary = run_human_review(
            corpus_dir=args.corpus_dir,
            output_dir=args.output_dir,
            tree_ids=tree_ids,
            submit_ls=args.submit_ls,
            skip_existing=args.skip_existing,
            stratified_file=args.stratified_file if args.stratified_file.is_file() else None,
        )
    except Exception as exc:
        logging.getLogger(__name__).exception("human_review failed: %s", exc)
        sys.exit(1)

    print(json.dumps(sdk_response_to_dict(summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
