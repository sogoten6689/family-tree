"""CLI — Gemini label pilot corpus and import into Label Studio."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from label_studio_pipeline.corpus_store import load_json, load_pilot_trees, tree_dir
from label_studio_pipeline.cross_check import build_cross_check
from label_studio_pipeline.gemini_extractor import GeminiConfig, GeminiExtractionError, extract_genealogy_entities
from label_studio_pipeline.import_registry import is_tree_imported, mark_tree_imported
from label_studio_pipeline.ls_importer import (
    LabelStudioConfig,
    build_task_payload,
    get_or_create_client,
    get_or_create_project,
    import_task_with_predictions,
    sdk_response_to_dict,
)
from label_studio_pipeline.pha_ky_assessment import PhaKyAssessmentConfig, assess_pha_ky
from label_studio_pipeline.prompts import DEFAULT_SYSTEM_PROMPT

DEFAULT_CORPUS_DIR = Path("data/vgp_corpus")
DEFAULT_LABELS_DIR = Path("data/gemini_labels")
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
    meta_path = base / "meta.json"
    pha_he_path = base / "pha_he.json"

    if not pha_ky_path.is_file():
        raise FileNotFoundError(f"Missing pha_ky.txt for tree_id={tree_id}")

    text = pha_ky_path.read_text(encoding="utf-8")
    meta = load_json(meta_path) or {}
    pha_he = load_json(pha_he_path) or {}
    return text, meta, pha_he


def run_label_and_import(
    *,
    corpus_dir: Path,
    labels_dir: Path,
    tree_ids: list[int],
    dry_run: bool,
    skip_import: bool,
    cross_check: bool,
    skip_assessment: bool,
    assessment_config: PhaKyAssessmentConfig | None,
    skip_imported: bool,
    force_tree_ids: set[int],
) -> dict:
    log = logging.getLogger(__name__)

    gemini_config = GeminiConfig(
        api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        model_name=os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip(),
        system_prompt=os.getenv("GEMINI_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT).strip(),
    )
    if not gemini_config.api_key:
        raise ValueError("GEMINI_API_KEY is not set. Add it to label_studio_pipeline/.env")

    ls_config = LabelStudioConfig(
        url=os.getenv("LABEL_STUDIO_URL", "http://localhost:8080").strip(),
        api_key=os.getenv("LABEL_STUDIO_API_KEY", "").strip(),
        project_id=_env_int("LABEL_STUDIO_PROJECT_ID"),
        project_title=os.getenv("LABEL_STUDIO_PROJECT_TITLE", "Family Tree NER+RE").strip(),
        model_version=os.getenv("LABEL_STUDIO_MODEL_VERSION", "gemini-preannotation").strip(),
    )

    summary: dict = {"trees": [], "imported": [], "skipped": [], "already_imported": [], "errors": []}
    task_payloads: list[tuple[int, dict]] = []
    assess_cfg = assessment_config or PhaKyAssessmentConfig()

    for tree_id in tree_ids:
        log.info("Processing tree_id=%s", tree_id)
        try:
            if skip_imported and tree_id not in force_tree_ids and is_tree_imported(
                labels_dir,
                tree_id,
                corpus_dir=corpus_dir,
            ):
                log.info("Skipping tree_id=%s — already imported to Label Studio", tree_id)
                summary["already_imported"].append({"tree_id": tree_id, "reason": "already_imported"})
                continue

            text, meta, pha_he = _read_tree_corpus(corpus_dir, tree_id)

            if not skip_assessment:
                assessment = assess_pha_ky(
                    text,
                    tree_id=tree_id,
                    pha_he=pha_he,
                    meta=meta,
                    config=assess_cfg,
                )
                assessment_path = tree_dir(corpus_dir, tree_id) / "pha_ky.assessment.json"
                assessment_path.write_text(
                    json.dumps(assessment.to_dict(), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                if not assessment.suitable:
                    log.warning(
                        "Skipping tree_id=%s (score=%.1f): %s",
                        tree_id,
                        assessment.score,
                        "; ".join(assessment.skip_reasons),
                    )
                    summary["skipped"].append(
                        {
                            "tree_id": tree_id,
                            "score": assessment.score,
                            "skip_reasons": assessment.skip_reasons,
                            "warnings": assessment.warnings,
                        },
                    )
                    continue

            extraction = extract_genealogy_entities(text, gemini_config)

            out_tree = labels_dir / str(tree_id)
            out_tree.mkdir(parents=True, exist_ok=True)
            (out_tree / "pha_ky.entities.json").write_text(
                json.dumps(extraction, ensure_ascii=False, indent=2) + "\n",
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
                "entity_count": len(extraction["entities"]),
                "relation_count": len(extraction["relations"]),
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
        except (GeminiExtractionError, FileNotFoundError, ValueError) as exc:
            log.error("tree_id=%s: %s", tree_id, exc)
            summary["errors"].append({"tree_id": tree_id, "error": str(exc)})

    if dry_run or skip_import:
        summary["dry_run"] = dry_run
        summary["skip_import"] = skip_import
        return summary

    if not ls_config.api_key:
        raise ValueError("LABEL_STUDIO_API_KEY is required for import")

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
            labels_dir,
            tree_id=tree_id,
            project_id=project.id,
            corpus_dir=corpus_dir,
            ls_task_ids=ls_task_ids,
        )

    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gemini pre-label pilot corpus and import into Label Studio.",
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=DEFAULT_CORPUS_DIR,
        help="Corpus directory from crawl_corpus.",
    )
    parser.add_argument(
        "--labels-dir",
        type=Path,
        default=DEFAULT_LABELS_DIR,
        help="Directory for Gemini JSON outputs.",
    )
    parser.add_argument(
        "--pilot-file",
        type=Path,
        default=None,
        help="JSON with selected_tree_ids (default: corpus-dir/pilot_trees.json).",
    )
    parser.add_argument(
        "--tree-id",
        type=int,
        action="append",
        dest="tree_ids",
        help="Focus specific tree_id (repeatable). Re-runs even if already imported.",
    )
    parser.add_argument(
        "--cross-check",
        action="store_true",
        help="Write cross_check.json comparing entities vs pha_he names.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Gemini only, no Label Studio import.")
    parser.add_argument("--skip-import", action="store_true", help="Build tasks but skip LS import.")
    parser.add_argument(
        "--skip-assessment",
        action="store_true",
        help="Send all trees to Gemini without Phả ký quality gate.",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=None,
        help="Minimum Phả ký assessment score (default: 45).",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=None,
        help="Skip Phả ký longer than this (default: 12000).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run Gemini/import for all tree_ids, including already imported ones.",
    )
    parser.add_argument(
        "--include-imported",
        action="store_true",
        help="Alias of --force.",
    )
    parser.add_argument(
        "--no-diagram-overlap",
        action="store_true",
        help="Do not require diagram name overlap during assessment.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=PACKAGE_DIR / ".env",
        help="Path to .env file.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    _configure_logging(args.verbose)
    _load_env(args.env_file)

    if args.tree_ids:
        tree_ids = args.tree_ids
        force_tree_ids = set(args.tree_ids)
    else:
        pilot_file = args.pilot_file or (args.corpus_dir / "pilot_trees.json")
        data = load_json(pilot_file) if pilot_file.is_file() else None
        if data and isinstance(data.get("selected_tree_ids"), list):
            tree_ids = [int(x) for x in data["selected_tree_ids"]]
        else:
            tree_ids = load_pilot_trees(args.corpus_dir)
        force_tree_ids = set()

    force_all = args.force or args.include_imported
    skip_imported = not force_all and not bool(args.tree_ids)

    if not tree_ids:
        print(
            "No tree_ids. Run crawl_corpus first or pass --tree-id.",
            file=sys.stderr,
        )
        sys.exit(2)

    assessment_config = PhaKyAssessmentConfig(
        min_score=args.min_score if args.min_score is not None else PhaKyAssessmentConfig.min_score,
        max_chars=args.max_chars if args.max_chars is not None else PhaKyAssessmentConfig.max_chars,
        require_diagram_overlap=not args.no_diagram_overlap,
    )

    try:
        summary = run_label_and_import(
            corpus_dir=args.corpus_dir,
            labels_dir=args.labels_dir,
            tree_ids=tree_ids,
            dry_run=args.dry_run,
            skip_import=args.skip_import,
            cross_check=args.cross_check,
            skip_assessment=args.skip_assessment,
            assessment_config=assessment_config,
            skip_imported=skip_imported,
            force_tree_ids=force_tree_ids,
        )
    except Exception as exc:
        logging.getLogger(__name__).exception("label_and_import failed: %s", exc)
        sys.exit(1)

    print(json.dumps(sdk_response_to_dict(summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
