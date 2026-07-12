from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.documents.repository import DocumentRepository, DocumentService
from app.documents.storage import ObjectStorage
from app.family_tree_store import FamilyTreeNotFoundError
from app.pipeline.service import PipelineService
from app.nomfoundation.ocr_pipeline import analyze_family_tree_from_merged_ocr, post_ocr_hooks
from tools.fetch_nomfoundation import run as crawl_nomfoundation_run
from tools.sync_nomfoundation_documents import (
    attach_nom_images_from_volume_dir,
    attach_nom_metadata_document,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_nom_tree_id(volume_id: int) -> str:
    return f"nom-{volume_id}"


def upsert_nom_family_tree(
    db: Session,
    store: Any,
    *,
    family_tree_id: str,
    name: str,
    description: Optional[str],
    external_url: str,
) -> Dict[str, Any]:
    now = _now_iso()
    db.execute(
        text(
            """
            INSERT INTO family_tree (
                id, name, description, nodes_json, node_count,
                external_url, has_source_document, has_hannom_text,
                created_at, updated_at
            )
            VALUES (
                :id, :name, :description, CAST(:nodes_json AS JSON), 0,
                :external_url, 1, 1, :created_at, :updated_at
            )
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                description = VALUES(description),
                external_url = VALUES(external_url),
                has_source_document = GREATEST(has_source_document, VALUES(has_source_document)),
                has_hannom_text = GREATEST(has_hannom_text, VALUES(has_hannom_text)),
                updated_at = VALUES(updated_at)
            """
        ),
        {
            "id": family_tree_id,
            "name": name,
            "description": description,
            "nodes_json": "[]",
            "external_url": external_url,
            "created_at": now,
            "updated_at": now,
        },
    )
    db.commit()

    try:
        tree_doc = store.get_tree(family_tree_id)
    except FamilyTreeNotFoundError:
        tree_doc = {
            "id": family_tree_id,
            "name": name,
            "description": description,
            "nodes": [],
            "external_url": external_url,
            "has_source_document": True,
            "has_hannom_text": True,
        }
    else:
        if hasattr(store, "_sync_source_document"):
            try:
                store._sync_source_document(tree_doc)
            except Exception:
                pass
    return tree_doc


def import_nom_volume(
    *,
    collection_id: int,
    volume_id: int,
    output_dir: Path,
    db: Session,
    storage: ObjectStorage,
    store: Any,
    get_tree: Callable[[str], dict],
    delay_seconds: float = 0.3,
    max_pages: int = 100,
    image_variant: str = "large",
    page_start: int = 1,
    page_end: Optional[int] = None,
    family_tree_id: Optional[str] = None,
    tree_name: Optional[str] = None,
    sync_pipeline: bool = True,
    force_documents: bool = False,
    crawl_only: bool = False,
    attach_only: bool = False,
    run_ocr: bool = False,
    run_analyze: bool = False,
    job_id: Optional[str] = None,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    def _progress(patch: Dict[str, Any]) -> None:
        if on_progress:
            on_progress(patch)

    if not attach_only:
        crawl_summary = crawl_nomfoundation_run(
            collection_id=collection_id,
            volume_id=volume_id,
            output_dir=output_dir,
            delay_seconds=delay_seconds,
            max_pages=max_pages,
            image_variant=image_variant,  # type: ignore[arg-type]
            page_start=page_start,
            page_end=page_end,
        )
        _progress(
            {
                "phase": "crawl",
                "downloaded_pages": len(crawl_summary.get("downloaded_pages", [])),
                "skipped_pages": len(crawl_summary.get("skipped_pages", [])),
                "errors": len(crawl_summary.get("errors", [])),
            }
        )
    else:
        crawl_summary = {
            "collection_id": collection_id,
            "volume_id": volume_id,
            "downloaded_pages": [],
            "skipped_pages": [],
            "errors": [],
            "page_count": 0,
        }

    if crawl_only:
        return {
            **crawl_summary,
            "job_id": job_id,
            "crawl_only": True,
        }

    volume_dir = output_dir / "volumes" / str(volume_id)
    metadata_path = volume_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}

    resolved_tree_id = (family_tree_id or default_nom_tree_id(volume_id)).strip()
    resolved_name = (
        tree_name or metadata.get("title_vn") or metadata.get("title") or f"Nom volume {volume_id}"
    ).strip()
    volume_url = metadata.get("url") or (
        f"https://lib.nomfoundation.org/collection/{collection_id}/volume/{volume_id}/"
    )
    description = (
        f"Nguồn Nom Foundation — collection {collection_id}, volume {volume_id}. "
        f"{metadata.get('catalog_code') or ''}".strip()
    )

    tree_doc = upsert_nom_family_tree(
        db,
        store,
        family_tree_id=resolved_tree_id,
        name=resolved_name,
        description=description,
        external_url=volume_url,
    )

    service = DocumentService(
        DocumentRepository(db),
        storage,
        get_tree=get_tree,
    )
    pages_dir = volume_dir / "pages"
    images_result = attach_nom_images_from_volume_dir(
        service=service,
        family_tree_id=resolved_tree_id,
        title=resolved_name,
        pages_dir=pages_dir,
        collection_id=collection_id,
        volume_id=volume_id,
        force=force_documents,
    )
    metadata_result = attach_nom_metadata_document(
        service=service,
        family_tree_id=resolved_tree_id,
        title=resolved_name,
        metadata=metadata,
        collection_id=collection_id,
        volume_id=volume_id,
        force=force_documents,
    )
    db.commit()
    _progress(
        {
            "phase": "attach",
            "images_document_id": images_result.get("document_id"),
            "images_attached": images_result.get("uploaded_count") or images_result.get("file_count"),
        }
    )

    ocr_result: Dict[str, Any] = {"processed": 0, "skipped": 0, "errors": []}
    if run_ocr and images_result.get("document_id"):
        images_doc_id = int(images_result["document_id"])
        ocr_file_ids: Optional[List[int]] = None
        uploaded_names = set(images_result.get("file_names") or [])
        if uploaded_names:
            images_doc = service.get_document(images_doc_id)
            ocr_file_ids = [
                item.id
                for item in images_doc.files
                if item.file_name in uploaded_names and str(item.file_type).startswith("image/")
            ] or None

        ocr_result = service.ocr_transliterate_batch(
            images_doc_id,
            file_ids=ocr_file_ids,
            skip_existing=not force_documents,
        )
        hook_result = post_ocr_hooks(
            db,
            service,
            images_doc_id,
            merge_pages=True,
            sync_pipeline=True,
        )
        ocr_result["merged_page_count"] = hook_result.get("merge", {}).get("page_count", 0)
        ocr_result["combined_transcription_text"] = hook_result.get("merge", {}).get("combined_text", "")
        db.commit()
        _progress(
            {
                "phase": "ocr",
                "ocr_processed": ocr_result.get("processed", 0),
                "ocr_skipped": ocr_result.get("skipped", 0),
                "ocr_errors": len(ocr_result.get("errors", [])),
                "merged_pages": ocr_result.get("merged_page_count", 0),
            }
        )

    analyze_result: Dict[str, Any] = {"node_count": 0, "gemini_error": None}
    if run_analyze and images_result.get("document_id"):
        merged_text = service.read_merged_transcription_text(int(images_result["document_id"]))
        analyze_result = analyze_family_tree_from_merged_ocr(
            store,
            get_tree,
            resolved_tree_id,
            merged_text,
            source=f"nomfoundation:{volume_id}",
        )
        _progress(
            {
                "phase": "analyze",
                "node_count": analyze_result.get("node_count", 0),
                "gemini_error": analyze_result.get("gemini_error"),
            }
        )

    pipeline_synced = False
    if sync_pipeline:
        pipeline = PipelineService(db, get_tree=get_tree)
        pipeline.sync_from_tree_state(resolved_tree_id)
        db.commit()
        pipeline_synced = True
        _progress({"phase": "pipeline", "pipeline_synced": True})

    return {
        **crawl_summary,
        "job_id": job_id,
        "tree_id": resolved_tree_id,
        "tree_name": resolved_name,
        "tree": tree_doc,
        "images_document": images_result,
        "metadata_document": metadata_result,
        "ocr_result": ocr_result,
        "analyze_result": analyze_result,
        "pipeline_synced": pipeline_synced,
        "page_start": page_start,
        "page_end": page_end,
    }
