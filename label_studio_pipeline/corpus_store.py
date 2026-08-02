"""Read/write local VGP corpus artifacts."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from label_studio_pipeline.pha_he_parser import ParsedNode, nodes_to_plain_text

MIN_PHA_KY_CHARS = 200
DEFAULT_PILOT_LIMIT = 10


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def tree_dir(corpus_root: Path, tree_id: int) -> Path:
    return corpus_root / str(tree_id)


def compute_tree_content_hash(*, pha_ky_text: str, pha_he_payload: dict[str, Any]) -> str:
    normalized = json.dumps(
        {"pha_ky": pha_ky_text, "pha_he": pha_he_payload},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def save_tree_corpus(
    corpus_root: Path,
    *,
    tree_id: int,
    meta: dict[str, Any],
    pha_ky_text: str,
    pha_he_payload: dict[str, Any],
    content_hash: str,
) -> Path:
    out_dir = tree_dir(corpus_root, tree_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    meta_out = {
        **meta,
        "tree_id": tree_id,
        "content_hash": content_hash,
        "pha_ky_char_count": len(pha_ky_text),
        "pha_he_node_count": pha_he_payload.get("node_count", 0),
        "updated_at": _now_iso(),
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta_out, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "pha_ky.txt").write_text(pha_ky_text, encoding="utf-8")
    (out_dir / "pha_he.json").write_text(
        json.dumps(pha_he_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    nodes_raw = pha_he_payload.get("nodes", [])
    if isinstance(nodes_raw, list) and nodes_raw:
        nodes = [
            ParsedNode(**item)
            for item in nodes_raw
            if isinstance(item, dict) and "node_id" in item
        ]
        (out_dir / "pha_he.txt").write_text(nodes_to_plain_text(nodes) + "\n", encoding="utf-8")

    return out_dir


def is_valid_pilot_tree(corpus_root: Path, tree_id: int) -> bool:
    out_dir = tree_dir(corpus_root, tree_id)
    pha_ky_path = out_dir / "pha_ky.txt"
    pha_he_path = out_dir / "pha_he.json"
    if not pha_ky_path.is_file() or not pha_he_path.is_file():
        return False

    pha_ky_text = pha_ky_path.read_text(encoding="utf-8").strip()
    if len(pha_ky_text) < MIN_PHA_KY_CHARS:
        return False

    pha_he = load_json(pha_he_path)
    if not pha_he:
        return False
    return int(pha_he.get("node_count") or 0) > 0


def select_pilot_trees(
    corpus_root: Path,
    *,
    start: int,
    end: int,
    limit: int = DEFAULT_PILOT_LIMIT,
    exclude: set[int] | None = None,
    output_name: str = "pilot_trees.json",
) -> dict[str, Any]:
    excluded = exclude or set()
    selected: list[int] = []
    for tree_id in range(start, end + 1):
        if tree_id in excluded:
            continue
        if is_valid_pilot_tree(corpus_root, tree_id):
            selected.append(tree_id)
        if len(selected) >= limit:
            break

    payload = {
        "range": {"start": start, "end": end},
        "pilot_limit": limit,
        "exclude_tree_ids": sorted(excluded),
        "selected_tree_ids": selected,
        "selected_count": len(selected),
        "generated_at": _now_iso(),
    }
    corpus_root.mkdir(parents=True, exist_ok=True)
    (corpus_root / output_name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def select_batch_from_corpus(
    corpus_root: Path,
    *,
    limit: int,
    exclude: set[int] | None = None,
    min_tree_id: int | None = None,
    output_name: str = "batch_trees.json",
) -> dict[str, Any]:
    """Pick up to ``limit`` valid trees already crawled under corpus_root."""
    excluded = exclude or set()
    candidates: list[int] = []
    for path in sorted(corpus_root.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 0):
        if not path.is_dir() or not path.name.isdigit():
            continue
        tree_id = int(path.name)
        if min_tree_id is not None and tree_id < min_tree_id:
            continue
        if tree_id in excluded:
            continue
        if is_valid_pilot_tree(corpus_root, tree_id):
            candidates.append(tree_id)

    selected = candidates[:limit]
    payload = {
        "pilot_limit": limit,
        "exclude_tree_ids": sorted(excluded),
        "selected_tree_ids": selected,
        "selected_count": len(selected),
        "generated_at": _now_iso(),
    }
    corpus_root.mkdir(parents=True, exist_ok=True)
    (corpus_root / output_name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def list_valid_tree_ids(corpus_root: Path) -> list[int]:
    return sorted(
        int(path.name)
        for path in corpus_root.iterdir()
        if path.is_dir() and path.name.isdigit() and is_valid_pilot_tree(corpus_root, int(path.name))
    )


def load_pilot_trees(corpus_root: Path) -> list[int]:
    data = load_json(corpus_root / "pilot_trees.json")
    if not data:
        return []
    raw = data.get("selected_tree_ids", [])
    if not isinstance(raw, list):
        return []
    return [int(x) for x in raw]
