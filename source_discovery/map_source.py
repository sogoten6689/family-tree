"""Phase 1 — Firecrawl map + URL filter per seed source."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from source_discovery.firecrawl_client import get_client, map_limit
from source_discovery.seeds import SEED_SOURCES
from source_discovery.url_filters import extract_links_from_map_response, filter_urls

DEFAULT_OUTPUT = Path("data/sources_discovery")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def map_source(source: dict, *, output_dir: Path) -> dict:
    log = logging.getLogger(__name__)
    client = get_client()
    source_id = source["source_id"]
    track = source["track"]
    base_url = source["base_url"]
    search = source.get("map_search")

    log.info("Mapping source_id=%s url=%s search=%r", source_id, base_url, search)
    kwargs: dict = {
        "url": base_url,
        "limit": map_limit(),
        "sitemap": "include",
    }
    if search:
        kwargs["search"] = search

    response = client.map(**kwargs)
    all_urls = extract_links_from_map_response(response)
    filtered = filter_urls(all_urls, track)

    out = output_dir / track / source_id
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_id": source_id,
        "track": track,
        "base_url": base_url,
        "map_search": search,
        "mapped_at": _now_iso(),
        "urls_total": len(all_urls),
        "urls_filtered": len(filtered),
        "urls_all": all_urls,
        "urls_genealogy": filtered,
    }
    (out / "map_urls.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log.info(
        "source_id=%s total=%d filtered=%d",
        source_id,
        len(all_urls),
        len(filtered),
    )
    return payload


def run_map_all(
    *,
    output_dir: Path = DEFAULT_OUTPUT,
    source_ids: list[str] | None = None,
    track: str | None = None,
) -> dict:
    sources = SEED_SOURCES
    if source_ids:
        ids = set(source_ids)
        sources = [s for s in sources if s["source_id"] in ids]
    if track:
        sources = [s for s in sources if s["track"] == track]

    results: list[dict] = []
    errors: list[dict] = []
    for source in sources:
        try:
            results.append(map_source(source, output_dir=output_dir))
        except Exception as exc:
            logging.getLogger(__name__).exception("map failed source_id=%s: %s", source["source_id"], exc)
            errors.append({"source_id": source["source_id"], "error": str(exc)})

    summary = {
        "mapped_at": _now_iso(),
        "output_dir": str(output_dir),
        "success_count": len(results),
        "error_count": len(errors),
        "results": [
            {
                "source_id": r["source_id"],
                "track": r["track"],
                "urls_total": r["urls_total"],
                "urls_filtered": r["urls_filtered"],
            }
            for r in results
        ],
        "errors": errors,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "map_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary
