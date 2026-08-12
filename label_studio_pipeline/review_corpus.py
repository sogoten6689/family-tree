"""Export stratified review corpus under data/review_corpus/."""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from label_studio_pipeline.corpus_store import load_json, tree_dir
from label_studio_pipeline.pilot_file import resolve_tree_ids
from label_studio_pipeline.vgp_images import download_tree_images
from label_studio_pipeline.vgp_urls import giapha_url, hinh_anh_url, pha_he_url, pha_ky_url

logger = logging.getLogger(__name__)

DEFAULT_SOURCE_DIR = Path("data/vgp_corpus")
DEFAULT_OUTPUT_DIR = Path("data/review_corpus/quoc_ngu")
DEFAULT_PILOT_FILE = Path("data/gold_labels/stratified_sample.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_stratified_doc_map(pilot_file: Path | None) -> dict[int, dict[str, Any]]:
    if not pilot_file or not pilot_file.is_file():
        return {}
    data = load_json(pilot_file) or {}
    docs = data.get("documents")
    if not isinstance(docs, list):
        return {}
    out: dict[int, dict[str, Any]] = {}
    for doc in docs:
        if isinstance(doc, dict) and doc.get("tree_id") is not None:
            out[int(doc["tree_id"])] = doc
    return out


def build_links_json(*, tree_id: int, meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "tree_id": tree_id,
        "giapha": meta.get("giapha_url") or giapha_url(tree_id),
        "pha_ky": meta.get("pha_ky_url") or pha_ky_url(tree_id),
        "pha_he": meta.get("pha_he_url") or pha_he_url(tree_id),
        "hinh_anh": hinh_anh_url(tree_id),
    }


def export_review_tree(
    tree_id: int,
    *,
    source_dir: Path,
    output_dir: Path,
    include_images: bool = True,
    stratified_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    src = tree_dir(source_dir, tree_id)
    if not (src / "pha_ky.txt").is_file():
        raise FileNotFoundError(f"Missing pha_ky.txt for tree_id={tree_id}")

    dst = output_dir / str(tree_id)
    dst.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for name in ("pha_ky.txt", "pha_he.json", "pha_he.txt"):
        src_path = src / name
        if src_path.is_file():
            shutil.copy2(src_path, dst / name)
            copied.append(name)

    meta = load_json(src / "meta.json") or {}
    review_meta: dict[str, Any] = {
        "tree_id": tree_id,
        "lineage_name": meta.get("lineage_name") or (stratified_doc or {}).get("lineage_name"),
        "title": meta.get("title"),
        "location": meta.get("location"),
        "stats": {
            "pha_ky_char_count": meta.get("pha_ky_char_count"),
            "pha_he_node_count": meta.get("pha_he_node_count"),
        },
        "content_hash": meta.get("content_hash"),
        "source_updated_at": meta.get("updated_at"),
        "exported_at": _now_iso(),
    }
    if stratified_doc:
        review_meta["review"] = {
            "doc_id": stratified_doc.get("doc_id"),
            "stratum": stratified_doc.get("stratum"),
            "split": stratified_doc.get("split"),
            "review_priority": stratified_doc.get("review_priority"),
            "double_annotation": stratified_doc.get("double_annotation"),
            "gold_source": stratified_doc.get("gold_source"),
        }
    (dst / "meta.json").write_text(
        json.dumps(review_meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    copied.append("meta.json")

    links = build_links_json(tree_id=tree_id, meta=meta)
    (dst / "links.json").write_text(
        json.dumps(links, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    copied.append("links.json")

    image_summary = None
    if include_images:
        image_summary = download_tree_images(tree_id, dst)
        copied.append("images/")
        (dst / "images.json").write_text(
            json.dumps(image_summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        copied.append("images.json")

    return {
        "tree_id": tree_id,
        "export_dir": str(dst),
        "files": copied,
        "lineage_name": review_meta.get("lineage_name"),
        "images": image_summary,
    }


def export_review_corpus(
    tree_ids: list[int],
    *,
    source_dir: Path = DEFAULT_SOURCE_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    include_images: bool = True,
    pilot_file: Path | None = DEFAULT_PILOT_FILE,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    doc_map = _load_stratified_doc_map(pilot_file)

    exported: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for tree_id in tree_ids:
        try:
            exported.append(
                export_review_tree(
                    tree_id,
                    source_dir=source_dir,
                    output_dir=output_dir,
                    include_images=include_images,
                    stratified_doc=doc_map.get(tree_id),
                ),
            )
        except (OSError, FileNotFoundError) as exc:
            logger.exception("tree_id=%s export failed", tree_id)
            errors.append({"tree_id": tree_id, "error": str(exc)})

    index = {
        "description": "Review corpus — 25 stratified VGP trees for human review",
        "source_dir": str(source_dir),
        "output_dir": str(output_dir),
        "pilot_file": str(pilot_file) if pilot_file else None,
        "include_images": include_images,
        "exported_count": len(exported),
        "error_count": len(errors),
        "tree_ids": [item["tree_id"] for item in exported],
        "trees": exported,
        "errors": errors,
        "generated_at": _now_iso(),
    }
    (output_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return index
