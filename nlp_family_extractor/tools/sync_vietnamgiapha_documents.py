from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.documents.models import Document, DocumentType
from app.documents.repository import DocumentRepository, DocumentService
from app.documents.storage import ObjectStorage

VGP_TEXT_MARKER = "vgp_text_export=1"


def _find_vgp_text_document(repository: DocumentRepository, family_tree_id: str) -> Optional[Document]:
    stmt = (
        select(Document)
        .where(
            Document.family_tree_id == family_tree_id,
            Document.type == DocumentType.VAN_BAN,
            Document.description == VGP_TEXT_MARKER,
        )
        .limit(1)
    )
    return repository.db.scalar(stmt)


def attach_vgp_text_document(
    *,
    service: DocumentService,
    family_tree_id: str,
    lineage_name: str,
    text_dir: Path,
    force: bool = False,
) -> Dict[str, Any]:
    full_text_path = text_dir / "full_text.txt"
    if not full_text_path.exists():
        return {
            "family_tree_id": family_tree_id,
            "attached": False,
            "reason": "missing_full_text",
        }

    repository = service.repository
    existing = _find_vgp_text_document(repository, family_tree_id)
    if existing and existing.files and not force:
        return {
            "family_tree_id": family_tree_id,
            "attached": False,
            "reason": "already_attached",
            "document_id": existing.id,
        }

    title = f"VGP text — {lineage_name or family_tree_id}"
    if existing is None:
        document = repository.create(
            family_tree_id=family_tree_id,
            title=title,
            description=VGP_TEXT_MARKER,
            doc_type=DocumentType.VAN_BAN,
        )
    else:
        document = existing

    file_bytes = full_text_path.read_bytes()
    buffer = BytesIO(file_bytes)
    created_files = service.upload_files(
        document.id,
        [
            (
                "full_text.txt",
                "text/plain; charset=utf-8",
                buffer,
                len(file_bytes),
            )
        ],
    )

    return {
        "family_tree_id": family_tree_id,
        "attached": True,
        "document_id": document.id,
        "file_count": len(created_files),
        "file_names": [item.file_name for item in created_files],
    }


def attach_documents_for_tree(
    *,
    db: Session,
    storage: ObjectStorage,
    get_tree: Callable[[str], dict],
    family_tree_id: str,
    lineage_name: str,
    text_root: Path,
    tree_id: int,
    force: bool = False,
) -> Dict[str, Any]:
    service = DocumentService(DocumentRepository(db), storage, get_tree=get_tree)
    text_dir = text_root / str(tree_id)
    return attach_vgp_text_document(
        service=service,
        family_tree_id=family_tree_id,
        lineage_name=lineage_name,
        text_dir=text_dir,
        force=force,
    )


def attach_documents_batch(
    *,
    db: Session,
    storage: ObjectStorage,
    get_tree: Callable[[str], dict],
    text_root: Path,
    tree_ids: List[int],
    dry_run: bool = False,
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "attached": [],
        "skipped": [],
        "errors": [],
    }

    for tree_id in tree_ids:
        family_tree_id = f"vgp-{tree_id}"
        meta_path = text_root / str(tree_id) / "meta.json"
        lineage_name = f"Tree {tree_id}"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if isinstance(meta, dict) and meta.get("lineage_name"):
                    lineage_name = str(meta["lineage_name"])
            except (OSError, json.JSONDecodeError):
                pass

        if dry_run:
            report["attached"].append(
                {
                    "family_tree_id": family_tree_id,
                    "tree_id": tree_id,
                    "mode": "dry-run",
                }
            )
            continue

        try:
            result = attach_documents_for_tree(
                db=db,
                storage=storage,
                get_tree=get_tree,
                family_tree_id=family_tree_id,
                lineage_name=lineage_name,
                text_root=text_root,
                tree_id=tree_id,
            )
            if result.get("attached"):
                report["attached"].append(result)
            else:
                report["skipped"].append(result)
        except Exception as exc:
            report["errors"].append(
                {
                    "family_tree_id": family_tree_id,
                    "tree_id": tree_id,
                    "error": str(exc),
                }
            )

    return report
