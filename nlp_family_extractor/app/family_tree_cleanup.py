from __future__ import annotations

from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.documents.models import Document
from app.documents.storage import ObjectStorage, ObjectStorageError
from app.pipeline.models import GenealogyPipelineStep
from app.pipeline.models import ResearchSourceLink
from app.vgp.models import VgpCrawl


def delete_family_tree_related(db: Session, tree_id: str, storage: Optional[ObjectStorage] = None) -> None:
    """Remove documents, pipeline, VGP crawl metadata, and research links for a tree."""
    documents = db.scalars(
        select(Document)
        .where(Document.family_tree_id == tree_id)
        .options(selectinload(Document.files))
    ).all()

    if storage is not None and storage.config.enabled:
        for document in documents:
            for file_item in document.files:
                try:
                    storage.delete_file(file_item.file_key)
                except ObjectStorageError:
                    pass

    for document in documents:
        db.delete(document)

    db.execute(delete(GenealogyPipelineStep).where(GenealogyPipelineStep.family_tree_id == tree_id))
    try:
        db.execute(delete(VgpCrawl).where(VgpCrawl.family_tree_id == tree_id))
    except Exception:
        pass
    db.execute(delete(ResearchSourceLink).where(ResearchSourceLink.family_tree_id == tree_id))
    db.flush()
