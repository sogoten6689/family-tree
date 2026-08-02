"""CLI entrypoint: scrape → Gemini → Label Studio."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from label_studio_pipeline.gemini_extractor import GeminiConfig, GeminiExtractionError, extract_genealogy_entities
from label_studio_pipeline.ls_importer import (
    LabelStudioConfig,
    build_task_payload,
    get_or_create_client,
    get_or_create_project,
    import_task_with_predictions,
)
from label_studio_pipeline.prompts import DEFAULT_SYSTEM_PROMPT
from label_studio_pipeline.scraper import resolve_url, scrape_genealogy_text

DEFAULT_SCRAPE_URL = "https://vietnamgiapha.com/XemGiaPha/11108/giapha.html"


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _load_env(env_file: Path | None) -> None:
    if env_file and env_file.is_file():
        load_dotenv(env_file)
        logging.getLogger(__name__).info("Loaded environment from %s", env_file)
    else:
        load_dotenv()


def _env_int(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    return int(raw)


def run_pipeline(
    *,
    scrape_url: str,
    dry_run: bool = False,
    skip_import: bool = False,
    output_json: Path | None = None,
    timeout: float = 30.0,
) -> dict:
    """Execute the full pipeline and return a summary dict."""
    log = logging.getLogger(__name__)

    log.info("Step 1/4 — Scraping genealogy text")
    scrape_result = scrape_genealogy_text(scrape_url, timeout=timeout)
    log.info("Scraped title=%r chars=%d", scrape_result.title, len(scrape_result.text))

    gemini_config = GeminiConfig(
        api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        model_name=os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip(),
        system_prompt=os.getenv("GEMINI_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT).strip(),
    )

    log.info("Step 2/4 — Gemini extraction")
    extraction = extract_genealogy_entities(scrape_result.text, gemini_config)
    log.info(
        "Extraction complete: entities=%d relations=%d",
        len(extraction["entities"]),
        len(extraction["relations"]),
    )

    ls_config = LabelStudioConfig(
        url=os.getenv("LABEL_STUDIO_URL", "http://localhost:8080").strip(),
        api_key=os.getenv("LABEL_STUDIO_API_KEY", "").strip(),
        project_id=_env_int("LABEL_STUDIO_PROJECT_ID"),
        project_title=os.getenv("LABEL_STUDIO_PROJECT_TITLE", "Family Tree NER+RE").strip(),
        model_version=os.getenv("LABEL_STUDIO_MODEL_VERSION", "gemini-preannotation").strip(),
    )

    task_payload = build_task_payload(
        text=scrape_result.text,
        source_url=scrape_result.url,
        title=scrape_result.title,
        extraction=extraction,
        model_version=ls_config.model_version,
    )

    summary = {
        "scrape_url": scrape_result.url,
        "title": scrape_result.title,
        "text_length": len(scrape_result.text),
        "entity_count": len(extraction["entities"]),
        "relation_count": len(extraction["relations"]),
        "prediction_regions": len(task_payload["predictions"][0]["result"]),
    }

    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(
            json.dumps(
                {
                    "scrape": {
                        "url": scrape_result.url,
                        "title": scrape_result.title,
                        "text": scrape_result.text,
                    },
                    "extraction": extraction,
                    "label_studio_task": task_payload,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        log.info("Wrote debug JSON to %s", output_json)
        summary["output_json"] = str(output_json)

    if dry_run:
        log.info("Dry run — skipping Label Studio import")
        return summary

    if skip_import:
        log.info("Skip import flag set — done")
        return summary

    if not ls_config.api_key:
        raise ValueError("LABEL_STUDIO_API_KEY is required for import")

    log.info("Step 3/4 — Label Studio project setup")
    client = get_or_create_client(ls_config)
    project = get_or_create_project(client, ls_config)
    summary["project_id"] = project.id

    log.info("Step 4/4 — Import pre-annotated task")
    import_response = import_task_with_predictions(client, project.id, task_payload)
    summary["import_response"] = import_response

    log.info("Pipeline finished successfully")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape genealogy text, extract via Gemini, import to Label Studio.",
    )
    parser.add_argument(
        "--url",
        default=os.getenv("SCRAPE_URL", DEFAULT_SCRAPE_URL),
        help="vietnamgiapha.com URL to scrape (default: env SCRAPE_URL or sample tree).",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(__file__).resolve().parent / ".env",
        help="Path to .env file (default: label_studio_pipeline/.env).",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional path to save scrape/extraction/task JSON for debugging.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run scrape + Gemini only; do not import to Label Studio.",
    )
    parser.add_argument(
        "--skip-import",
        action="store_true",
        help="Build task payload but skip Label Studio import.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds for scraping.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    _configure_logging(args.verbose)
    _load_env(args.env_file)

    scrape_url = resolve_url(args.url)

    try:
        summary = run_pipeline(
            scrape_url=scrape_url,
            dry_run=args.dry_run,
            skip_import=args.skip_import,
            output_json=args.output_json,
            timeout=args.timeout,
        )
    except GeminiExtractionError as exc:
        logging.getLogger(__name__).error("Gemini extraction failed: %s", exc)
        sys.exit(2)
    except Exception as exc:
        logging.getLogger(__name__).exception("Pipeline failed: %s", exc)
        sys.exit(1)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
