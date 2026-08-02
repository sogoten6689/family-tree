"""Track trees already labeled/imported into Label Studio."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from label_studio_pipeline.corpus_store import compute_tree_content_hash, load_json, tree_dir

REGISTRY_FILENAME = "import_registry.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def registry_path(labels_dir: Path) -> Path:
    return labels_dir / REGISTRY_FILENAME


def load_registry(labels_dir: Path) -> dict[str, Any]:
    data = load_json(registry_path(labels_dir))
    if not data:
        return {"version": 1, "updated_at": _now_iso(), "entries": {}}
    entries = data.get("entries")
    if not isinstance(entries, dict):
        data["entries"] = {}
    return data


def save_registry(labels_dir: Path, registry: dict[str, Any]) -> Path:
    labels_dir.mkdir(parents=True, exist_ok=True)
    registry["updated_at"] = _now_iso()
    path = registry_path(labels_dir)
    path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def get_imported_tree_ids(labels_dir: Path) -> set[int]:
    registry = load_registry(labels_dir)
    imported: set[int] = set()
    for key, entry in registry.get("entries", {}).items():
        if not isinstance(entry, dict):
            continue
        if entry.get("status") != "imported":
            continue
        try:
            imported.add(int(entry.get("tree_id", key)))
        except (TypeError, ValueError):
            continue
    return imported


def _tree_content_hash(corpus_dir: Path, tree_id: int) -> str | None:
    base = tree_dir(corpus_dir, tree_id)
    pha_ky_text = (base / "pha_ky.txt").read_text(encoding="utf-8") if (base / "pha_ky.txt").is_file() else ""
    pha_he = load_json(base / "pha_he.json") or {}
    if not pha_ky_text and not pha_he:
        return None
    return compute_tree_content_hash(pha_ky_text=pha_ky_text, pha_he_payload=pha_he)


def is_tree_imported(
    labels_dir: Path,
    tree_id: int,
    *,
    corpus_dir: Path | None = None,
) -> bool:
    """Return True when tree was previously imported into Label Studio."""
    registry = load_registry(labels_dir)
    entry = registry.get("entries", {}).get(str(tree_id))
    if not isinstance(entry, dict) or entry.get("status") != "imported":
        return False

    if corpus_dir is None:
        return True

    stored_hash = entry.get("content_hash")
    if not stored_hash:
        return True

    current_hash = _tree_content_hash(corpus_dir, tree_id)
    if current_hash is None:
        return True
    return stored_hash == current_hash


def mark_tree_imported(
    labels_dir: Path,
    *,
    tree_id: int,
    project_id: int | None = None,
    corpus_dir: Path | None = None,
    source: str = "label_and_import",
    ls_task_ids: list[int] | None = None,
) -> None:
    registry = load_registry(labels_dir)
    content_hash = _tree_content_hash(corpus_dir, tree_id) if corpus_dir else None
    registry.setdefault("entries", {})[str(tree_id)] = {
        "tree_id": tree_id,
        "status": "imported",
        "imported_at": _now_iso(),
        "project_id": project_id,
        "content_hash": content_hash,
        "source": source,
        "ls_task_ids": ls_task_ids or [],
    }
    save_registry(labels_dir, registry)

    out_dir = labels_dir / str(tree_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "import_status.json").write_text(
        json.dumps(registry["entries"][str(tree_id)], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def bootstrap_registry(
    labels_dir: Path,
    *,
    corpus_dir: Path,
    tree_ids: list[int] | None = None,
    project_id: int | None = None,
    source: str = "bootstrap",
) -> dict[str, Any]:
    """
    Mark trees as imported when they already have Label Studio task artifacts on disk.

    Useful after manual imports or before the registry existed.
    """
    if tree_ids is None:
        tree_ids = sorted(
            int(path.name)
            for path in labels_dir.iterdir()
            if path.is_dir() and path.name.isdigit() and (path / "pha_ky.ls_task.json").is_file()
        )

    registry = load_registry(labels_dir)
    added: list[int] = []
    for tree_id in tree_ids:
        key = str(tree_id)
        if key in registry.get("entries", {}) and registry["entries"][key].get("status") == "imported":
            continue
        ls_task_path = labels_dir / str(tree_id) / "pha_ky.ls_task.json"
        if not ls_task_path.is_file():
            continue
        content_hash = _tree_content_hash(corpus_dir, tree_id)
        registry.setdefault("entries", {})[key] = {
            "tree_id": tree_id,
            "status": "imported",
            "imported_at": datetime.fromtimestamp(ls_task_path.stat().st_mtime, tz=timezone.utc).isoformat(),
            "project_id": project_id,
            "content_hash": content_hash,
            "source": source,
            "ls_task_ids": [],
        }
        added.append(tree_id)

    save_registry(labels_dir, registry)
    return {
        "bootstrapped_count": len(added),
        "bootstrapped_tree_ids": added,
        "imported_total": len(get_imported_tree_ids(labels_dir)),
    }
