"""Export normalized gia phả folders under data/gia_pha/."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from label_studio_pipeline.corpus_store import load_json, tree_dir
from label_studio_pipeline.import_registry import load_registry

DEFAULT_SOURCE_DIR = Path("data/vgp_corpus")
DEFAULT_EXPORT_DIR = Path("data/gia_pha")
DEFAULT_LABELS_DIR = Path("data/gemini_labels")

TREE_FILES = (
    ("pha_ky.txt", "pha_ky.txt"),
    ("pha_he.json", "pha_he.json"),
    ("pha_he.txt", "pha_he.txt"),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_text_optional(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def build_metadata(
    *,
    tree_id: int,
    source_dir: Path,
    labels_dir: Path | None = None,
) -> dict[str, Any]:
    """Merge crawl meta, assessment, and label import info into metadata.json."""
    base = tree_dir(source_dir, tree_id)
    meta = load_json(base / "meta.json") or {}
    assessment = load_json(base / "pha_ky.assessment.json")

    metadata: dict[str, Any] = {
        "tree_id": tree_id,
        "lineage_name": meta.get("lineage_name"),
        "title": meta.get("title"),
        "location": meta.get("location"),
        "urls": {
            "giapha": meta.get("giapha_url"),
            "pha_ky": meta.get("pha_ky_url"),
            "pha_he": meta.get("pha_he_url"),
        },
        "stats": {
            "person_count": meta.get("person_count"),
            "family_count": meta.get("family_count"),
            "generation_count": meta.get("generation_count"),
            "pha_ky_char_count": meta.get("pha_ky_char_count"),
            "pha_he_node_count": meta.get("pha_he_node_count"),
        },
        "content_hash": meta.get("content_hash"),
        "source_updated_at": meta.get("updated_at"),
        "exported_at": _now_iso(),
    }

    if assessment:
        metadata["assessment"] = {
            "suitable": assessment.get("suitable"),
            "score": assessment.get("score"),
            "skip_reasons": assessment.get("skip_reasons", []),
            "warnings": assessment.get("warnings", []),
            "metrics": assessment.get("metrics"),
        }

    if labels_dir is not None:
        registry = load_registry(labels_dir)
        import_entry = registry.get("entries", {}).get(str(tree_id))
        labels_base = labels_dir / str(tree_id)
        entities = load_json(labels_base / "pha_ky.entities.json")
        if import_entry or entities:
            metadata["labeling"] = {
                "imported": import_entry.get("status") == "imported" if import_entry else False,
                "imported_at": import_entry.get("imported_at") if import_entry else None,
                "project_id": import_entry.get("project_id") if import_entry else None,
                "entity_count": len(entities.get("entities", [])) if entities else None,
                "relation_count": len(entities.get("relations", [])) if entities else None,
            }

    return metadata


def export_tree(
    tree_id: int,
    *,
    source_dir: Path,
    export_dir: Path,
    labels_dir: Path | None = None,
    include_labels: bool = True,
) -> dict[str, Any]:
    """Export one tree into export_dir/{tree_id}/ with standardized filenames."""
    src = tree_dir(source_dir, tree_id)
    if not (src / "pha_ky.txt").is_file():
        raise FileNotFoundError(f"Missing source pha_ky.txt for tree_id={tree_id}")

    dst = export_dir / str(tree_id)
    dst.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for src_name, dst_name in TREE_FILES:
        src_path = src / src_name
        if src_path.is_file():
            shutil.copy2(src_path, dst / dst_name)
            copied.append(dst_name)

    metadata = build_metadata(tree_id=tree_id, source_dir=source_dir, labels_dir=labels_dir)
    (dst / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    copied.append("metadata.json")

    assessment_src = src / "pha_ky.assessment.json"
    if assessment_src.is_file():
        shutil.copy2(assessment_src, dst / "assessment.json")
        copied.append("assessment.json")

    if include_labels and labels_dir is not None:
        label_src = labels_dir / str(tree_id)
        if label_src.is_dir():
            label_dst = dst / "labels"
            label_dst.mkdir(exist_ok=True)
            for name in ("pha_ky.entities.json", "pha_ky.ls_task.json", "import_status.json", "cross_check.json"):
                path = label_src / name
                if path.is_file():
                    out_name = name.replace("pha_ky.", "")
                    shutil.copy2(path, label_dst / out_name)
                    copied.append(f"labels/{out_name}")

    return {
        "tree_id": tree_id,
        "export_dir": str(dst),
        "files": copied,
        "lineage_name": metadata.get("lineage_name"),
    }


def export_trees(
    tree_ids: list[int],
    *,
    source_dir: Path = DEFAULT_SOURCE_DIR,
    export_dir: Path = DEFAULT_EXPORT_DIR,
    labels_dir: Path | None = DEFAULT_LABELS_DIR,
    include_labels: bool = True,
) -> dict[str, Any]:
    """Export many trees and write index.json at export root."""
    export_dir.mkdir(parents=True, exist_ok=True)
    exported: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for tree_id in tree_ids:
        try:
            exported.append(
                export_tree(
                    tree_id,
                    source_dir=source_dir,
                    export_dir=export_dir,
                    labels_dir=labels_dir,
                    include_labels=include_labels,
                ),
            )
        except (OSError, FileNotFoundError) as exc:
            errors.append({"tree_id": tree_id, "error": str(exc)})

    index = {
        "description": "Gia phả export — mỗi thư mục con = 1 tree_id từ vietnamgiapha.com",
        "layout": {
            "metadata.json": "Metadata gia phả (URLs, stats, assessment, labeling)",
            "pha_ky.txt": "Phả ký — văn bản Quốc ngữ",
            "pha_he.json": "Phả hệ — sơ đồ structured (nodes + relationships)",
            "pha_he.txt": "Phả hệ dạng text phẳng (optional)",
            "assessment.json": "Đánh giá chất lượng Phả ký trước Gemini",
            "labels/": "Gemini pre-annotation + import status (optional)",
        },
        "source_dir": str(source_dir),
        "export_dir": str(export_dir),
        "exported_count": len(exported),
        "error_count": len(errors),
        "tree_ids": [item["tree_id"] for item in exported],
        "trees": exported,
        "errors": errors,
        "generated_at": _now_iso(),
    }
    (export_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return index
