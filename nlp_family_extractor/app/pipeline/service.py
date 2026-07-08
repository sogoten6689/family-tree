from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.documents.models import Document, DocumentType
from app.pipeline.models import (
    PIPELINE_STEP_ORDER,
    GenealogyPipelineStep,
    PipelineStepId,
    PipelineStepStatus,
)
from tools.sync_vietnamgiapha_documents import VGP_TEXT_MARKER


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PipelineService:
    def __init__(
        self,
        db: Session,
        *,
        get_tree: Callable[[str], dict],
    ) -> None:
        self.db = db
        self.get_tree = get_tree

    def _get_or_create_steps(self, family_tree_id: str) -> List[GenealogyPipelineStep]:
        stmt = (
            select(GenealogyPipelineStep)
            .where(GenealogyPipelineStep.family_tree_id == family_tree_id)
            .order_by(GenealogyPipelineStep.id.asc())
        )
        existing = list(self.db.scalars(stmt).all())
        existing_ids = {item.step_id for item in existing}
        created = False
        for step_id in PIPELINE_STEP_ORDER:
            if step_id not in existing_ids:
                record = GenealogyPipelineStep(
                    family_tree_id=family_tree_id,
                    document_id=0,
                    step_id=step_id,
                    status=PipelineStepStatus.PENDING,
                )
                self.db.add(record)
                existing.append(record)
                created = True
        if created:
            self.db.flush()
        return existing

    def _tree_documents(self, family_tree_id: str) -> List[Document]:
        stmt = select(Document).where(Document.family_tree_id == family_tree_id)
        return list(self.db.scalars(stmt).all())

    def _is_vgp_tree(self, family_tree_id: str, tree: dict) -> bool:
        if family_tree_id.startswith("vgp-"):
            return True
        external_url = str(tree.get("external_url") or "")
        return "vietnamgiapha.com" in external_url

    def sync_from_tree_state(self, family_tree_id: str) -> List[GenealogyPipelineStep]:
        tree = self.get_tree(family_tree_id)
        steps = self._get_or_create_steps(family_tree_id)
        documents = self._tree_documents(family_tree_id)
        is_vgp = self._is_vgp_tree(family_tree_id, tree)

        name = str(tree.get("name") or "").strip()
        nodes = tree.get("nodes") or []
        has_nodes = isinstance(nodes, list) and len(nodes) > 0

        vgp_text_doc = next(
            (
                doc
                for doc in documents
                if doc.type == DocumentType.VAN_BAN and doc.description == VGP_TEXT_MARKER
            ),
            None,
        )
        han_nom_docs = [doc for doc in documents if doc.type in {DocumentType.HAN_NOM, DocumentType.HINH_ANH}]
        ocr_result_docs = [doc for doc in documents if doc.type == DocumentType.KET_QUA_VAN_BAN]
        quoc_ngu_docs = [
            doc
            for doc in documents
            if doc.type == DocumentType.VAN_BAN and doc.description != VGP_TEXT_MARKER
        ]

        for step in steps:
            if step.status == PipelineStepStatus.RUNNING:
                continue

            if step.step_id == PipelineStepId.NAME:
                if name:
                    step.status = PipelineStepStatus.DONE
                    step.output_ref = name
                elif step.status != PipelineStepStatus.SKIPPED:
                    step.status = PipelineStepStatus.PENDING

            elif step.step_id == PipelineStepId.HANNOM_IMAGE:
                if han_nom_docs:
                    step.status = PipelineStepStatus.DONE
                    step.output_ref = f"documents:{han_nom_docs[0].id}"
                elif is_vgp and step.status not in {PipelineStepStatus.DONE, PipelineStepStatus.SKIPPED}:
                    step.status = PipelineStepStatus.SKIPPED
                    step.skipped_reason = "vgp_entry"

            elif step.step_id == PipelineStepId.OCR:
                if ocr_result_docs:
                    step.status = PipelineStepStatus.DONE
                    step.output_ref = f"documents:{ocr_result_docs[0].id}"
                elif is_vgp and step.status not in {PipelineStepStatus.DONE, PipelineStepStatus.SKIPPED}:
                    step.status = PipelineStepStatus.SKIPPED
                    step.skipped_reason = "vgp_entry"

            elif step.step_id == PipelineStepId.HAN_CHARS:
                if ocr_result_docs:
                    step.status = PipelineStepStatus.DONE
                    step.output_ref = f"documents:{ocr_result_docs[0].id}"
                elif is_vgp and step.status not in {PipelineStepStatus.DONE, PipelineStepStatus.SKIPPED}:
                    step.status = PipelineStepStatus.SKIPPED
                    step.skipped_reason = "vgp_entry"

            elif step.step_id == PipelineStepId.QUOC_NGU:
                if vgp_text_doc or quoc_ngu_docs:
                    target = vgp_text_doc or quoc_ngu_docs[0]
                    step.status = PipelineStepStatus.DONE
                    step.output_ref = f"documents:{target.id}"
                elif step.status not in {PipelineStepStatus.DONE, PipelineStepStatus.SKIPPED}:
                    step.status = PipelineStepStatus.PENDING

            elif step.step_id == PipelineStepId.DISTILLED:
                if is_vgp and step.status not in {PipelineStepStatus.DONE, PipelineStepStatus.SKIPPED}:
                    step.status = PipelineStepStatus.SKIPPED
                    step.skipped_reason = "vgp_entry"

            elif step.step_id == PipelineStepId.OUTPUT:
                if has_nodes:
                    step.status = PipelineStepStatus.DONE
                    step.output_ref = f"nodes:{len(nodes)}"
                elif step.status not in {PipelineStepStatus.DONE, PipelineStepStatus.SKIPPED}:
                    step.status = PipelineStepStatus.PENDING

            step.updated_at = _now()

        self.db.flush()
        return steps

    def get_pipeline(self, family_tree_id: str) -> List[GenealogyPipelineStep]:
        return self.sync_from_tree_state(family_tree_id)

    def skip_step(
        self,
        family_tree_id: str,
        step_id: PipelineStepId,
        *,
        reason: str,
    ) -> GenealogyPipelineStep:
        steps = self._get_or_create_steps(family_tree_id)
        target = next((item for item in steps if item.step_id == step_id), None)
        if target is None:
            raise ValueError(f"Unknown step '{step_id.value}'")
        target.status = PipelineStepStatus.SKIPPED
        target.skipped_reason = reason[:64]
        target.finished_at = _now()
        target.updated_at = _now()
        self.db.flush()
        return target

    def run_step(self, family_tree_id: str, step_id: PipelineStepId) -> GenealogyPipelineStep:
        steps = self.sync_from_tree_state(family_tree_id)
        target = next((item for item in steps if item.step_id == step_id), None)
        if target is None:
            raise ValueError(f"Unknown step '{step_id.value}'")

        if target.status in {PipelineStepStatus.DONE, PipelineStepStatus.SKIPPED}:
            return target

        target.status = PipelineStepStatus.RUNNING
        target.started_at = _now()
        target.error_message = None
        target.updated_at = _now()
        self.db.flush()

        try:
            if step_id == PipelineStepId.NAME:
                tree = self.get_tree(family_tree_id)
                name = str(tree.get("name") or "").strip()
                if not name:
                    raise ValueError("Cây chưa có tên.")
                target.status = PipelineStepStatus.DONE
                target.output_ref = name
            elif step_id == PipelineStepId.OUTPUT:
                tree = self.get_tree(family_tree_id)
                nodes = tree.get("nodes") or []
                if not isinstance(nodes, list) or not nodes:
                    raise ValueError("Cây chưa có node — chạy phân tích hoặc import trước.")
                target.status = PipelineStepStatus.DONE
                target.output_ref = f"nodes:{len(nodes)}"
            elif step_id == PipelineStepId.QUOC_NGU:
                documents = self._tree_documents(family_tree_id)
                text_doc = next(
                    (
                        doc
                        for doc in documents
                        if doc.type == DocumentType.VAN_BAN
                    ),
                    None,
                )
                if text_doc is None:
                    raise ValueError("Chưa có tài liệu quốc ngữ — upload hoặc attach VGP text.")
                target.status = PipelineStepStatus.DONE
                target.output_ref = f"documents:{text_doc.id}"
            elif step_id in {PipelineStepId.OCR, PipelineStepId.HAN_CHARS}:
                raise ValueError("Chạy OCR từ tab Tài liệu (nút Phiên âm) rồi làm mới pipeline.")
            elif step_id == PipelineStepId.HANNOM_IMAGE:
                raise ValueError("Upload ảnh Hán-Nôm hoặc crawl Nom Foundation trước.")
            elif step_id == PipelineStepId.DISTILLED:
                raise ValueError("Bước cô đọng chưa triển khai — sẽ dùng Gemini/NLP.")
            else:
                raise ValueError(f"Step '{step_id.value}' chưa hỗ trợ chạy tự động.")
        except Exception as exc:
            target.status = PipelineStepStatus.ERROR
            target.error_message = str(exc)
            target.finished_at = _now()
            target.updated_at = _now()
            self.db.flush()
            return target

        target.finished_at = _now()
        target.updated_at = _now()
        self.db.flush()
        return target

    def run_all(self, family_tree_id: str) -> Dict[str, List[str]]:
        result = {"ran": [], "skipped": [], "errors": []}
        for step_id in PIPELINE_STEP_ORDER:
            steps = self.sync_from_tree_state(family_tree_id)
            current = next(item for item in steps if item.step_id == step_id)
            if current.status in {PipelineStepStatus.DONE, PipelineStepStatus.SKIPPED}:
                result["skipped"].append(step_id.value)
                continue
            updated = self.run_step(family_tree_id, step_id)
            if updated.status == PipelineStepStatus.DONE:
                result["ran"].append(step_id.value)
            elif updated.status == PipelineStepStatus.SKIPPED:
                result["skipped"].append(step_id.value)
            else:
                result["errors"].append(step_id.value)
                break
        return result
