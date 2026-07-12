from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.documents.repository import DocumentRepository, DocumentService
from app.documents.storage import ObjectStorage
from app.family_tree_store import FamilyTreeNotFoundError
from app.pipeline.service import PipelineService
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
    family_tree_id: Optional[str] = None,
    tree_name: Optional[str] = None,
    sync_pipeline: bool = True,
    force_documents: bool = False,
) -> Dict[str, Any]:
    crawl_summary = crawl_nomfoundation_run(
        collection_id=collection_id,
        volume_id=volume_id,
        output_dir=output_dir,
        delay_seconds=delay_seconds,
        max_pages=max_pages,
        image_variant=image_variant,  # type: ignore[arg-type]
    )

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

    pipeline_synced = False
    if sync_pipeline:
        pipeline = PipelineService(db, get_tree=get_tree)
        pipeline.sync_from_tree_state(resolved_tree_id)
        db.commit()
        pipeline_synced = True

    return {
        **crawl_summary,
        "tree_id": resolved_tree_id,
        "tree_name": resolved_name,
        "tree": tree_doc,
        "images_document": images_result,
        "metadata_document": metadata_result,
        "pipeline_synced": pipeline_synced,
    }
