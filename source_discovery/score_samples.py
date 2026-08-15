"""Phase 2 — scrape sample URLs and score feasibility."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from source_discovery.firecrawl_client import get_client, load_env
from source_discovery.scoring import scrape_to_dict, score_scrape
from source_discovery.seeds import SEED_SOURCES

DEFAULT_DISCOVERY_DIR = Path("data/sources_discovery")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sample_per_source() -> int:
    load_env()
    raw = os.getenv("FIRECRAWL_SAMPLE_PER_SOURCE", "5").strip()
    return int(raw) if raw else 5


def _pick_sample_urls(urls: list[str], limit: int, track: str) -> list[str]:
    if not urls:
        return []

    ranked = list(urls)
    if track == "hannom":
        volume_roots = [u for u in ranked if "/volume/" in u and "/page/" not in u]
        genealogy = [u for u in volume_roots if any(k in u.lower() for k in ("1255", "1256", "208", "855"))]
        rest = [u for u in volume_roots if u not in genealogy]
        ranked = genealogy + rest + [u for u in ranked if u not in volume_roots]

    seen: set[str] = set()
    picked: list[str] = []
    for url in ranked:
        if url in seen:
            continue
        seen.add(url)
        picked.append(url)
        if len(picked) >= limit:
            break
    return picked


def _load_map_urls(discovery_dir: Path, track: str, source_id: str) -> dict | None:
    path = discovery_dir / track / source_id / "map_urls.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def score_source(
    source: dict,
    *,
    discovery_dir: Path,
    sample_limit: int | None = None,
) -> dict[str, Any]:
    log = logging.getLogger(__name__)
    client = get_client()
    source_id = source["source_id"]
    track = source["track"]
    limit = sample_limit or _sample_per_source()

    mapped = _load_map_urls(discovery_dir, track, source_id)
    if not mapped:
        raise FileNotFoundError(f"Missing map_urls.json for {source_id}")

    urls = mapped.get("urls_genealogy") or mapped.get("urls_all") or []
    sample_urls = _pick_sample_urls(urls, limit, track)

    out_dir = discovery_dir / track / source_id / "samples"
    out_dir.mkdir(parents=True, exist_ok=True)

    samples: list[dict] = []
    errors: list[dict] = []

    for url in sample_urls:
        log.info("Scoring sample source_id=%s url=%s", source_id, url)
        try:
            response = client.scrape(url, formats=["markdown"])
            scrape = scrape_to_dict(response)
            scored = score_scrape(track, scrape, url)
            sample_record = {
                **scored,
                "scraped_at": _now_iso(),
            }
            slug = re_sub_slug(url)
            (out_dir / f"{slug}.json").write_text(
                json.dumps({"score": sample_record, "scrape_meta": _compact_scrape(scrape)}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            samples.append(sample_record)
            time.sleep(7)
        except Exception as exc:
            log.exception("scrape failed url=%s: %s", url, exc)
            errors.append({"url": url, "error": str(exc)})
            if "Rate Limit" in str(exc):
                time.sleep(30)

    scores = [s["score"] for s in samples]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    max_score = max(scores) if scores else 0
    decisions = [s["decision"] for s in samples]
    if max_score >= 70 or decisions.count("collect") >= 2:
        source_decision = "collect"
    elif max_score >= 45 or decisions.count("pilot") >= 2:
        source_decision = "pilot"
    else:
        source_decision = "reject"

    summary = {
        "source_id": source_id,
        "track": track,
        "name": source.get("name"),
        "base_url": source.get("base_url"),
        "scored_at": _now_iso(),
        "sample_count": len(samples),
        "error_count": len(errors),
        "avg_score": avg_score,
        "max_score": max_score,
        "source_decision": source_decision,
        "samples": samples,
        "errors": errors,
    }
    (discovery_dir / track / source_id / "score_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    log.info(
        "source_id=%s avg=%.1f max=%d decision=%s",
        source_id,
        avg_score,
        max_score,
        source_decision,
    )
    return summary


def re_sub_slug(url: str) -> str:
    import re

    slug = re.sub(r"^https?://", "", url)
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", slug).strip("_")
    return slug[:80] or "sample"


def _compact_scrape(scrape: dict[str, Any]) -> dict[str, Any]:
    md = scrape.get("markdown") or ""
    return {
        "metadata": scrape.get("metadata"),
        "links_count": len(scrape.get("links") or []),
        "markdown_preview": md[:500],
    }


def run_score_all(
    *,
    discovery_dir: Path = DEFAULT_DISCOVERY_DIR,
    source_ids: list[str] | None = None,
    track: str | None = None,
    sample_limit: int | None = None,
) -> dict[str, Any]:
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
            results.append(
                score_source(source, discovery_dir=discovery_dir, sample_limit=sample_limit)
            )
        except Exception as exc:
            logging.getLogger(__name__).exception("score failed source_id=%s: %s", source["source_id"], exc)
            errors.append({"source_id": source["source_id"], "error": str(exc)})

    payload = {
        "scored_at": _now_iso(),
        "discovery_dir": str(discovery_dir),
        "success_count": len(results),
        "error_count": len(errors),
        "results": [
            {
                "source_id": r["source_id"],
                "track": r["track"],
                "avg_score": r["avg_score"],
                "max_score": r["max_score"],
                "source_decision": r["source_decision"],
                "sample_count": r["sample_count"],
            }
            for r in results
        ],
        "errors": errors,
    }
    discovery_dir.mkdir(parents=True, exist_ok=True)
    (discovery_dir / "score_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload
