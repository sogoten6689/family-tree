"""Import synthetic Phả ký tasks + gold annotations into a separate Label Studio project."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from label_studio_pipeline.ls_importer import LabelStudioConfig, get_or_create_client, get_or_create_project, sdk_response_to_dict

DEFAULT_SYNTHETIC_DIR = Path("data/synthetic_pha_ky")
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


def _resolve_tree_ids(synthetic_dir: Path, tree_ids: list[int] | None, limit: int | None) -> list[int]:
    if tree_ids:
        resolved = tree_ids
    else:
        resolved = sorted(
            int(path.name)
            for path in synthetic_dir.iterdir()
            if path.is_dir() and path.name.isdigit() and (path / "gold.ls_annotation.json").is_file()
        )
    if limit is not None:
        return resolved[:limit]
    return resolved


def _load_ls_task_index(client, project_id: int) -> dict[int, int]:
    index: dict[int, int] = {}
    for task in client.tasks.list(project=project_id, page_size=500):
        data = task.data or {}
        tree_id = data.get("tree_id")
        if tree_id is not None:
            index[int(tree_id)] = int(task.id)
    return index


def run_import_synthetic(
    *,
    synthetic_dir: Path,
    tree_ids: list[int],
    dry_run: bool,
    skip_existing: bool,
    ls_config: LabelStudioConfig,
) -> dict:
    log = logging.getLogger(__name__)
    summary: dict = {"imported": [], "skipped": [], "errors": []}

    if dry_run:
        for tree_id in tree_ids:
            base = synthetic_dir / str(tree_id)
            if not (base / "synthetic_pha_ky.txt").is_file():
                summary["skipped"].append({"tree_id": tree_id, "reason": "missing_synthetic"})
                continue
            summary["imported"].append({"tree_id": tree_id, "dry_run": True})
        summary["dry_run"] = True
        return summary

    if not ls_config.api_key:
        raise ValueError("LABEL_STUDIO_API_KEY is required")

    client = get_or_create_client(ls_config)
    project = get_or_create_project(client, ls_config)
    summary["project_id"] = project.id
    task_index = _load_ls_task_index(client, project.id)

    for tree_id in tree_ids:
        base = synthetic_dir / str(tree_id)
        text_path = base / "synthetic_pha_ky.txt"
        annotation_path = base / "gold.ls_annotation.json"
        metadata_path = base / "metadata.json"

        if not text_path.is_file() or not annotation_path.is_file():
            summary["skipped"].append({"tree_id": tree_id, "reason": "missing_files"})
            continue

        if skip_existing and tree_id in task_index:
            summary["skipped"].append({"tree_id": tree_id, "reason": "already_imported", "task_id": task_index[tree_id]})
            continue

        try:
            text = text_path.read_text(encoding="utf-8")
            annotation = json.loads(annotation_path.read_text(encoding="utf-8"))
            metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}

            task_payload = {
                "data": {
                    "text": text,
                    "tree_id": tree_id,
                    "title": metadata.get("lineage_name") or f"tree_{tree_id}",
                    "source_url": metadata.get("real_pha_ky_url") or "",
                    "source": "synthetic_from_pha_he",
                },
                "annotations": [
                    {
                        "result": annotation["result"],
                        "ground_truth": True,
                        "was_cancelled": False,
                        "lead_time": 0.0,
                    }
                ],
            }

            response = client.projects.import_tasks(
                id=project.id,
                request=[task_payload],
                return_task_ids=True,
            )
            payload = sdk_response_to_dict(response)
            task_ids = payload.get("task_ids") or payload.get("ids") or []
            task_id = int(task_ids[0]) if task_ids else None
            summary["imported"].append({"tree_id": tree_id, "task_id": task_id})
            log.info("Imported synthetic tree_id=%s task_id=%s", tree_id, task_id)
        except Exception as exc:
            log.exception("tree_id=%s failed: %s", tree_id, exc)
            summary["errors"].append({"tree_id": tree_id, "error": str(exc)})

    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import synthetic Phả ký into Label Studio (separate project).")
    parser.add_argument("--synthetic-dir", type=Path, default=DEFAULT_SYNTHETIC_DIR)
    parser.add_argument("--tree-id", type=int, action="append", dest="tree_ids")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--env-file", type=Path, default=PACKAGE_DIR / ".env")
    parser.add_argument(
        "--project-id",
        type=int,
        default=None,
        help="Override LABEL_STUDIO_SYNTHETIC_PROJECT_ID.",
    )
    parser.add_argument(
        "--project-title",
        type=str,
        default=None,
        help="Override LABEL_STUDIO_SYNTHETIC_PROJECT_TITLE.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    _configure_logging(args.verbose)
    _load_env(args.env_file)

    tree_ids = _resolve_tree_ids(args.synthetic_dir, args.tree_ids, args.limit)
    if not tree_ids:
        print("No synthetic tree_ids to import.", file=sys.stderr)
        sys.exit(2)

    ls_config = LabelStudioConfig(
        url=os.getenv("LABEL_STUDIO_URL", "http://localhost:8080").strip(),
        api_key=os.getenv("LABEL_STUDIO_API_KEY", "").strip(),
        project_id=args.project_id or _env_int("LABEL_STUDIO_SYNTHETIC_PROJECT_ID"),
        project_title=(
            args.project_title
            or os.getenv("LABEL_STUDIO_SYNTHETIC_PROJECT_TITLE", "Family Tree NER+RE (Synthetic)").strip()
        ),
    )

    try:
        summary = run_import_synthetic(
            synthetic_dir=args.synthetic_dir,
            tree_ids=tree_ids,
            dry_run=args.dry_run,
            skip_existing=args.skip_existing,
            ls_config=ls_config,
        )
    except Exception as exc:
        logging.getLogger(__name__).exception("import_synthetic failed: %s", exc)
        sys.exit(1)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
