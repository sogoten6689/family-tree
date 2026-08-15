"""Build and update sources_registry.json from discovery results."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from source_discovery.seeds import SEED_SOURCES

DEFAULT_REGISTRY = Path("data/sources_discovery/sources_registry.json")
DEFAULT_DISCOVERY_DIR = Path("data/sources_discovery")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_registry(discovery_dir: Path = DEFAULT_DISCOVERY_DIR) -> dict:
    sources: list[dict] = []
    for seed in SEED_SOURCES:
        source_id = seed["source_id"]
        track = seed["track"]
        entry: dict = {
            "source_id": source_id,
            "track": track,
            "name": seed["name"],
            "base_url": seed["base_url"],
            "status": seed.get("status", "seed"),
        }

        mapped = _load_json(discovery_dir / track / source_id / "map_urls.json")
        if mapped:
            entry["discovery"] = {
                "firecrawl_map_at": mapped.get("mapped_at"),
                "urls_discovered": mapped.get("urls_total"),
                "urls_genealogy_filtered": mapped.get("urls_filtered"),
            }
            entry["status"] = "discovered"

        scored = _load_json(discovery_dir / track / source_id / "score_summary.json")
        if scored:
            entry["feasibility_score"] = scored.get("max_score")
            entry["avg_score"] = scored.get("avg_score")
            entry["source_decision"] = scored.get("source_decision")
            entry["scored_at"] = scored.get("scored_at")
            decision = scored.get("source_decision")
            if decision == "collect":
                entry["status"] = "scored"
            elif decision == "pilot":
                entry["status"] = "pilot"
            elif decision == "reject":
                entry["status"] = "rejected"

        if seed.get("status") == "active_collector":
            entry["status"] = "active_collector"
            if source_id == "vietnamgiapha":
                entry["collected"] = {"trees": 2152, "tier_a": 101, "path": "data/vgp_corpus/"}
            if source_id == "nomfoundation_c2":
                entry["collected"] = {"volumes": 5, "pages": 163, "path": "data/hannom/nomfoundation/"}

        sources.append(entry)

    return {
        "version": 1,
        "updated_at": _now_iso(),
        "sources": sources,
    }


def write_registry(path: Path = DEFAULT_REGISTRY, discovery_dir: Path = DEFAULT_DISCOVERY_DIR) -> dict:
    registry = build_registry(discovery_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return registry
