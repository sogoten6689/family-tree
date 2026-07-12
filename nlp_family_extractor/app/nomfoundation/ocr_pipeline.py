from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from sqlalchemy.orm import Session

from app.documents.repository import DocumentService
from app.domains.extraction.extractor import FamilyExtractor
from app.pipeline.service import PipelineService


def sync_pipeline_for_document(
    db: Session,
    document_service: DocumentService,
    source_document_id: int,
) -> str:
    source = document_service.get_document(source_document_id)
    pipeline = PipelineService(db, get_tree=document_service.get_tree)
    pipeline.sync_from_tree_state(source.family_tree_id)
    db.flush()
    return source.family_tree_id


def post_ocr_hooks(
    db: Session,
    document_service: DocumentService,
    source_document_id: int,
    *,
    merge_pages: bool = True,
    sync_pipeline: bool = True,
) -> Dict[str, Any]:
    merge_result: Dict[str, Any] = {
        "merged": False,
        "page_count": 0,
        "text_length": 0,
        "combined_text": "",
    }
    if merge_pages:
        merge_result = document_service.rebuild_merged_transcription(source_document_id)
    pipeline_synced = False
    tree_id: Optional[str] = None
    if sync_pipeline:
        tree_id = sync_pipeline_for_document(db, document_service, source_document_id)
        pipeline_synced = True
    return {
        "merge": merge_result,
        "pipeline_synced": pipeline_synced,
        "tree_id": tree_id,
    }


def analyze_family_tree_from_merged_ocr(
    store: Any,
    get_tree: Callable[[str], dict],
    family_tree_id: str,
    text: str,
    *,
    source: str = "nomfoundation",
) -> Dict[str, Any]:
    cleaned = text.strip()
    if not cleaned:
        return {
            "node_count": 0,
            "gemini_error": "Không có text phiên âm để phân tích.",
            "balkan_nodes": [],
        }

    tree = get_tree(family_tree_id)
    extractor = FamilyExtractor()
    extraction = extractor.parse(cleaned)
    from app.gemini_service import normalize_balkan_nodes

    balkan_nodes, gemini_err = normalize_balkan_nodes(cleaned, extraction)

    if gemini_err:
        return {
            "node_count": 0,
            "gemini_error": gemini_err,
            "balkan_nodes": [],
        }

    store.replace_tree_document(
        family_tree_id,
        name=str(tree.get("name") or family_tree_id),
        description=tree.get("description"),
        nodes=balkan_nodes,
    )
    return {
        "node_count": len(balkan_nodes),
        "gemini_error": None,
        "balkan_nodes": balkan_nodes,
        "source": source,
    }
