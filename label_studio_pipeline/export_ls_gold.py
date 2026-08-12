"""Export human-reviewed Label Studio annotations to gold training JSON."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from label_studio_pipeline.gold_builder import to_training_record
from label_studio_pipeline.ls_importer import LabelStudioConfig, get_or_create_client, get_or_create_project, sdk_response_to_dict

DEFAULT_OUTPUT_DIR = Path("data/gold_labels/v1_human")
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


def _annotation_dict(annotation: Any) -> dict:
    if isinstance(annotation, dict):
        return annotation
    return sdk_response_to_dict(annotation)


def _is_human_reviewed(annotation: dict, *, include_auto: bool) -> bool:
    if include_auto:
        return True
    if annotation.get("was_cancelled"):
        return False
    completed_by = annotation.get("completed_by")
    if completed_by is not None:
        return True
    lead_time = float(annotation.get("lead_time") or 0)
    if lead_time > 0:
        return True
    return False


def _ls_result_to_extraction(result: list[dict]) -> dict[str, list]:
    entities: list[dict] = []
    relations: list[dict] = []
    region_to_text: dict[str, str] = {}

    for item in result:
        if item.get("type") == "labels":
            value = item.get("value") or {}
            region_id = str(item.get("id") or "")
            span_text = str(value.get("text") or "")
            labels = value.get("labels") or []
            if not labels or not span_text:
                continue
            entities.append({"text": span_text, "label": labels[0]})
            if region_id:
                region_to_text[region_id] = span_text
        elif item.get("type") == "relation":
            labels = item.get("labels") or []
            head = region_to_text.get(str(item.get("from_id") or ""))
            tail = region_to_text.get(str(item.get("to_id") or ""))
            if head and tail and labels:
                relations.append({"type": labels[0], "head": head, "tail": tail})

    return {"entities": entities, "relations": relations}


def export_ls_gold(
    *,
    output_dir: Path,
    ls_config: LabelStudioConfig,
    include_auto: bool,
    stratified_file: Path | None,
) -> dict:
    log = logging.getLogger(__name__)
    if not ls_config.api_key:
        raise ValueError("LABEL_STUDIO_API_KEY is required")

    client = get_or_create_client(ls_config)
    project = get_or_create_project(client, ls_config)

    stratum_by_tree: dict[int, dict] = {}
    if stratified_file and stratified_file.is_file():
        stratified = json.loads(stratified_file.read_text(encoding="utf-8"))
        for doc in stratified.get("documents") or []:
            stratum_by_tree[int(doc["tree_id"])] = doc

    exported: list[dict] = []
    skipped: list[dict] = []

    for task in client.tasks.list(project=project.id, page_size=500):
        task_dict = sdk_response_to_dict(task)
        data = task_dict.get("data") or {}
        tree_id = data.get("tree_id")
        text = str(data.get("text") or "")
        if tree_id is None or not text.strip():
            skipped.append({"task_id": task_dict.get("id"), "reason": "missing_tree_id_or_text"})
            continue

        annotations = task_dict.get("annotations") or []
        chosen: dict | None = None
        for annotation in annotations:
            ann = _annotation_dict(annotation)
            if not _is_human_reviewed(ann, include_auto=include_auto):
                continue
            if chosen is None or float(ann.get("lead_time") or 0) >= float(chosen.get("lead_time") or 0):
                chosen = ann

        if chosen is None:
            skipped.append({"tree_id": int(tree_id), "task_id": task_dict.get("id"), "reason": "no_human_annotation"})
            continue

        result = chosen.get("result") or []
        extraction = _ls_result_to_extraction(result)
        meta_doc = stratum_by_tree.get(int(tree_id)) or {}
        training = to_training_record(
            tree_id=int(tree_id),
            text=text,
            extraction=extraction,
            source_url=str(data.get("source_url") or ""),
            title=str(data.get("title") or f"tree_{tree_id}"),
        )
        training["source"] = "human_reviewed_ls"
        training["stratum"] = meta_doc.get("stratum")
        training["split"] = meta_doc.get("split")
        training["annotation_id"] = chosen.get("id")
        training["completed_by"] = chosen.get("completed_by")
        training["lead_time"] = chosen.get("lead_time")

        out_tree = output_dir / str(tree_id)
        out_tree.mkdir(parents=True, exist_ok=True)
        (out_tree / "gold.training.json").write_text(
            json.dumps(training, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (out_tree / "gold.ls_annotation.json").write_text(
            json.dumps(chosen, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        exported.append(
            {
                "tree_id": int(tree_id),
                "task_id": task_dict.get("id"),
                "entity_count": len(extraction["entities"]),
                "relation_count": len(extraction["relations"]),
                "stratum": meta_doc.get("stratum"),
                "split": meta_doc.get("split"),
            }
        )
        log.info("Exported tree_id=%s entities=%d relations=%d", tree_id, len(extraction["entities"]), len(extraction["relations"]))

    output_dir.mkdir(parents=True, exist_ok=True)
    dataset = {
        "version": 1,
        "source": "label_studio_human_export",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "project_id": project.id,
        "include_auto": include_auto,
        "doc_count": len(exported),
        "documents": [json.loads((output_dir / str(item["tree_id"]) / "gold.training.json").read_text(encoding="utf-8")) for item in exported],
    }
    (output_dir / "dataset.json").write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "project_id": project.id,
        "output_dir": str(output_dir),
        "exported_count": len(exported),
        "skipped_count": len(skipped),
        "exported": exported,
        "skipped": skipped,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export human-reviewed LS annotations to gold JSON.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--stratified-file",
        type=Path,
        default=Path("data/gold_labels/stratified_sample.json"),
        help="Attach stratum/split metadata when available.",
    )
    parser.add_argument(
        "--include-auto",
        action="store_true",
        help="Include auto-gold annotations (lead_time=0, no completed_by).",
    )
    parser.add_argument("--env-file", type=Path, default=PACKAGE_DIR / ".env")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    _configure_logging(args.verbose)
    _load_env(args.env_file)

    ls_config = LabelStudioConfig(
        url=os.getenv("LABEL_STUDIO_URL", "http://localhost:8080").strip(),
        api_key=os.getenv("LABEL_STUDIO_API_KEY", "").strip(),
        project_id=_env_int("LABEL_STUDIO_PROJECT_ID"),
        project_title=os.getenv("LABEL_STUDIO_PROJECT_TITLE", "Family Tree NER+RE").strip(),
    )

    try:
        summary = export_ls_gold(
            output_dir=args.output_dir,
            ls_config=ls_config,
            include_auto=args.include_auto,
            stratified_file=args.stratified_file if args.stratified_file.is_file() else None,
        )
    except Exception as exc:
        logging.getLogger(__name__).exception("export_ls_gold failed: %s", exc)
        sys.exit(1)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
