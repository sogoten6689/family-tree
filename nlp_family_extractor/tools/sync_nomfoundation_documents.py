from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.documents.models import Document, DocumentType
from app.documents.repository import DocumentRepository, DocumentService
from app.documents.storage import ObjectStorage

NOM_HINH_ANH_MARKER_PREFIX = "nomfoundation_hinh_anh="


def nom_hinh_anh_marker(*, collection_id: int, volume_id: int) -> str:
    return f"{NOM_HINH_ANH_MARKER_PREFIX}c{collection_id}:v{volume_id}"


def _find_nom_document(
    repository: DocumentRepository,
    *,
    family_tree_id: str,
    marker: str,
) -> Optional[Document]:
    stmt = (
        select(Document)
        .where(
            Document.family_tree_id == family_tree_id,
            Document.type == DocumentType.HINH_ANH,
            Document.description == marker,
        )
        .limit(1)
    )
    return repository.db.scalar(stmt)


def attach_nom_images_from_volume_dir(
    *,
    service: DocumentService,
    family_tree_id: str,
    title: str,
    pages_dir: Path,
    collection_id: int,
    volume_id: int,
    force: bool = False,
) -> Dict[str, Any]:
    image_files = sorted(pages_dir.glob("*.jpg"))
    if not image_files:
        return {
            "family_tree_id": family_tree_id,
            "attached": False,
            "reason": "no_local_images",
        }

    marker = nom_hinh_anh_marker(collection_id=collection_id, volume_id=volume_id)
    repository = service.repository
    existing = _find_nom_document(repository, family_tree_id=family_tree_id, marker=marker)
    if existing and existing.files and len(existing.files) >= len(image_files) and not force:
        return {
            "family_tree_id": family_tree_id,
            "attached": False,
            "reason": "already_attached",
            "document_id": existing.id,
            "file_count": len(existing.files),
        }

    doc_title = f"Nom scan — {title or family_tree_id}"
    if existing is None:
        document = repository.create(
            family_tree_id=family_tree_id,
            title=doc_title,
            description=marker,
            doc_type=DocumentType.HINH_ANH,
            subtype="nomfoundation",
        )
    else:
        document = existing

    upload_payload: List[Tuple[str, str, BytesIO, int]] = []
    for image_path in image_files:
        content = image_path.read_bytes()
        upload_payload.append((image_path.name, "image/jpeg", BytesIO(content), len(content)))

    created_files = service.upload_files(document.id, upload_payload)
    return {
        "family_tree_id": family_tree_id,
        "attached": True,
        "document_id": document.id,
        "file_count": len(created_files),
        "file_names": [item.file_name for item in created_files],
    }


def attach_nom_metadata_document(
    *,
    service: DocumentService,
    family_tree_id: str,
    title: str,
    metadata: Dict[str, Any],
    collection_id: int,
    volume_id: int,
    force: bool = False,
) -> Dict[str, Any]:
    marker = f"nomfoundation_metadata=c{collection_id}:v{volume_id}"
    repository = service.repository
    existing = repository.db.scalar(
        select(Document)
        .where(
            Document.family_tree_id == family_tree_id,
            Document.type == DocumentType.HAN_NOM,
            Document.description == marker,
        )
        .limit(1)
    )
    if existing and existing.files and not force:
        return {
            "family_tree_id": family_tree_id,
            "attached": False,
            "reason": "already_attached",
            "document_id": existing.id,
        }

    text_content = json.dumps(metadata, ensure_ascii=False, indent=2)
    file_bytes = text_content.encode("utf-8")
    doc_title = f"Nom metadata — {title or family_tree_id}"
    if existing is None:
        document = repository.create(
            family_tree_id=family_tree_id,
            title=doc_title,
            description=marker,
            doc_type=DocumentType.HAN_NOM,
            subtype="nomfoundation",
        )
    else:
        document = existing

    created_files = service.upload_files(
        document.id,
        [
            (
                "metadata.json",
                "application/json; charset=utf-8",
                BytesIO(file_bytes),
                len(file_bytes),
            )
        ],
    )
    return {
        "family_tree_id": family_tree_id,
        "attached": True,
        "document_id": document.id,
        "file_count": len(created_files),
    }
