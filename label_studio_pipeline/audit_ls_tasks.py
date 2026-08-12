"""Audit Label Studio tasks against tier selection files."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from label_studio_pipeline.corpus_store import load_json
from label_studio_pipeline.ls_importer import LabelStudioConfig, get_or_create_client, get_or_create_project, sdk_response_to_dict

DEFAULT_TIER_A = Path("data/vgp_corpus/tier_a_trees.json")
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


def audit_ls_tasks(
    *,
    tier_file: Path,
    ls_config: LabelStudioConfig,
) -> dict:
    tier_data = load_json(tier_file) or {}
    expected_ids = {int(x) for x in tier_data.get("selected_tree_ids") or []}

    if not ls_config.api_key:
        raise ValueError("LABEL_STUDIO_API_KEY is required")

    client = get_or_create_client(ls_config)
    project = get_or_create_project(client, ls_config)

    ls_tasks: list[dict] = []
    ls_tree_ids: set[int] = set()
    missing_tree_id: list[int] = []

    for task in client.tasks.list(project=project.id, page_size=500):
        task_dict = sdk_response_to_dict(task)
        data = task_dict.get("data") or {}
        tree_id = data.get("tree_id")
        task_id = task_dict.get("id")
        annotations = task_dict.get("annotations") or []
        if tree_id is None:
            missing_tree_id.append(int(task_id))
            continue
        tree_id = int(tree_id)
        ls_tree_ids.add(tree_id)
        ls_tasks.append(
            {
                "task_id": task_id,
                "tree_id": tree_id,
                "title": data.get("title"),
                "annotation_count": len(annotations),
                "has_human": any(
                    (ann.get("completed_by") is not None or float(ann.get("lead_time") or 0) > 0)
                    for ann in annotations
                ),
            }
        )

    in_ls_not_tier = sorted(ls_tree_ids - expected_ids)
    in_tier_not_ls = sorted(expected_ids - ls_tree_ids)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_id": project.id,
        "tier_file": str(tier_file),
        "expected_tier_count": len(expected_ids),
        "ls_task_count": len(ls_tasks),
        "ls_tree_id_count": len(ls_tree_ids),
        "missing_tree_id_tasks": missing_tree_id,
        "in_ls_not_tier": in_ls_not_tier,
        "in_tier_not_ls": in_tier_not_ls,
        "match_count": len(ls_tree_ids & expected_ids),
        "tasks": sorted(ls_tasks, key=lambda item: item["tree_id"]),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit Label Studio tasks vs tier file.")
    parser.add_argument("--tier-file", type=Path, default=DEFAULT_TIER_A)
    parser.add_argument("--output", type=Path, default=Path("data/vgp_corpus/ls_audit_report.json"))
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
        report = audit_ls_tasks(tier_file=args.tier_file, ls_config=ls_config)
    except Exception as exc:
        logging.getLogger(__name__).exception("audit_ls_tasks failed: %s", exc)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
