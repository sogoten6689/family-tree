from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.documents.models import Document, DocumentType
from app.documents.storage import ObjectStorage, ObjectStorageError
from app.pipeline.models import (
    PIPELINE_STEP_ORDER,
    GenealogyPipelineStep,
    PipelineStepId,
    PipelineStepStatus,
)
from app.pipeline.schemas import (
    PipelineArtifactFileResponse,
    PipelineArtifactResponse,
    PipelineContextResponse,
    PipelineStepUpdateRequest,
)
from tools.sync_vietnamgiapha_documents import VGP_TEXT_MARKER

PREVIEW_MAX_LEN = 200
DOCUMENT_REF_PATTERN = re.compile(r"^documents:(\d+)$")
NODES_REF_PATTERN = re.compile(r"^nodes:(\d+)$")
TEXT_FILE_EXTENSIONS = {".txt", ".text", ".md", ".csv"}
TEXT_FILE_MIME_PREFIXES = ("text/", "application/json")


class PipelineConflictError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_ref(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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

    def _detect_source_type(self, family_tree_id: str, tree: dict) -> str:
        if self._is_vgp_tree(family_tree_id, tree):
            return "vgp"
        external_url = str(tree.get("external_url") or "")
        if "nomfoundation.org" in external_url:
            return "nom"
        return "upload"

    def build_context(self, family_tree_id: str, tree: Optional[dict] = None) -> PipelineContextResponse:
        resolved_tree = tree or self.get_tree(family_tree_id)
        nodes = resolved_tree.get("nodes") or []
        node_count = len(nodes) if isinstance(nodes, list) else 0
        return PipelineContextResponse(
            family_tree_id=family_tree_id,
            tree_name=str(resolved_tree.get("name") or "").strip() or None,
            external_url=str(resolved_tree.get("external_url") or "").strip() or None,
            source_type=self._detect_source_type(family_tree_id, resolved_tree),
            node_count=node_count,
        )

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
            if step.manual_override:
                continue
            if step.status == PipelineStepStatus.RUNNING:
                continue

            if step.step_id == PipelineStepId.NAME:
                if name:
                    step.status = PipelineStepStatus.DONE
                    step.output_ref = name
                    step.content_hash = _hash_ref(name)
                elif step.status != PipelineStepStatus.SKIPPED:
                    step.status = PipelineStepStatus.PENDING
                    step.output_ref = None
                    step.content_hash = None

            elif step.step_id == PipelineStepId.HANNOM_IMAGE:
                if han_nom_docs:
                    ref = f"documents:{han_nom_docs[0].id}"
                    step.status = PipelineStepStatus.DONE
                    step.output_ref = ref
                    step.document_id = han_nom_docs[0].id
                    step.content_hash = _hash_ref(ref)
                elif is_vgp and step.status not in {PipelineStepStatus.DONE, PipelineStepStatus.SKIPPED}:
                    step.status = PipelineStepStatus.SKIPPED
                    step.skipped_reason = "vgp_entry"

            elif step.step_id == PipelineStepId.OCR:
                if ocr_result_docs:
                    ref = f"documents:{ocr_result_docs[0].id}"
                    step.status = PipelineStepStatus.DONE
                    step.output_ref = ref
                    step.document_id = ocr_result_docs[0].id
                    step.input_ref = f"documents:{han_nom_docs[0].id}" if han_nom_docs else None
                    step.content_hash = _hash_ref(ref)
                elif is_vgp and step.status not in {PipelineStepStatus.DONE, PipelineStepStatus.SKIPPED}:
                    step.status = PipelineStepStatus.SKIPPED
                    step.skipped_reason = "vgp_entry"

            elif step.step_id == PipelineStepId.HAN_CHARS:
                if ocr_result_docs:
                    ref = f"documents:{ocr_result_docs[0].id}"
                    step.status = PipelineStepStatus.DONE
                    step.output_ref = ref
                    step.document_id = ocr_result_docs[0].id
                    step.input_ref = f"documents:{ocr_result_docs[0].id}"
                    step.content_hash = _hash_ref(ref)
                elif is_vgp and step.status not in {PipelineStepStatus.DONE, PipelineStepStatus.SKIPPED}:
                    step.status = PipelineStepStatus.SKIPPED
                    step.skipped_reason = "vgp_entry"

            elif step.step_id == PipelineStepId.QUOC_NGU:
                if vgp_text_doc or quoc_ngu_docs:
                    target = vgp_text_doc or quoc_ngu_docs[0]
                    ref = f"documents:{target.id}"
                    step.status = PipelineStepStatus.DONE
                    step.output_ref = ref
                    step.document_id = target.id
                    if ocr_result_docs:
                        step.input_ref = f"documents:{ocr_result_docs[0].id}"
                    step.content_hash = _hash_ref(ref)
                elif step.status not in {PipelineStepStatus.DONE, PipelineStepStatus.SKIPPED}:
                    step.status = PipelineStepStatus.PENDING

            elif step.step_id == PipelineStepId.DISTILLED:
                if is_vgp and step.status not in {PipelineStepStatus.DONE, PipelineStepStatus.SKIPPED}:
                    step.status = PipelineStepStatus.SKIPPED
                    step.skipped_reason = "vgp_entry"

            elif step.step_id == PipelineStepId.OUTPUT:
                if has_nodes:
                    ref = f"nodes:{len(nodes)}"
                    step.status = PipelineStepStatus.DONE
                    step.output_ref = ref
                    step.content_hash = _hash_ref(ref)
                elif step.status not in {PipelineStepStatus.DONE, PipelineStepStatus.SKIPPED}:
                    step.status = PipelineStepStatus.PENDING

            step.updated_at = _now()

        self.db.flush()
        return steps

    def get_pipeline(self, family_tree_id: str) -> Tuple[List[GenealogyPipelineStep], PipelineContextResponse]:
        tree = self.get_tree(family_tree_id)
        steps = self.sync_from_tree_state(family_tree_id)
        return steps, self.build_context(family_tree_id, tree)

    def get_step(
        self,
        family_tree_id: str,
        step_id: PipelineStepId,
    ) -> Tuple[GenealogyPipelineStep, PipelineArtifactResponse, PipelineContextResponse]:
        tree = self.get_tree(family_tree_id)
        steps = self.sync_from_tree_state(family_tree_id)
        target = next((item for item in steps if item.step_id == step_id), None)
        if target is None:
            raise ValueError(f"Unknown step '{step_id.value}'")
        artifact = self._resolve_artifact(target, tree)
        return target, artifact, self.build_context(family_tree_id, tree)

    def resync_pipeline(
        self,
        family_tree_id: str,
        *,
        step_id: Optional[PipelineStepId] = None,
    ) -> List[GenealogyPipelineStep]:
        self.get_tree(family_tree_id)
        steps = self._get_or_create_steps(family_tree_id)
        for step in steps:
            if step_id is not None and step.step_id != step_id:
                continue
            step.manual_override = False
            step.updated_at = _now()
        self.db.flush()
        return self.sync_from_tree_state(family_tree_id)

    def update_step(
        self,
        family_tree_id: str,
        step_id: PipelineStepId,
        payload: PipelineStepUpdateRequest,
    ) -> GenealogyPipelineStep:
        self.get_tree(family_tree_id)
        steps = self._get_or_create_steps(family_tree_id)
        target = next((item for item in steps if item.step_id == step_id), None)
        if target is None:
            raise ValueError(f"Unknown step '{step_id.value}'")
        if target.status == PipelineStepStatus.RUNNING:
            raise PipelineConflictError("Không thể sửa step đang chạy.")

        fields_set = payload.model_fields_set

        if "status" in fields_set and payload.status is not None:
            target.status = PipelineStepStatus(payload.status)
            if target.status == PipelineStepStatus.DONE:
                target.error_message = None
            elif target.status == PipelineStepStatus.PENDING:
                target.finished_at = None
                if "error_message" not in fields_set:
                    target.error_message = None
            if target.status in {
                PipelineStepStatus.DONE,
                PipelineStepStatus.SKIPPED,
                PipelineStepStatus.ERROR,
            }:
                target.finished_at = _now()

        if "skipped_reason" in fields_set:
            target.skipped_reason = payload.skipped_reason[:64] if payload.skipped_reason else None
        if "input_ref" in fields_set:
            target.input_ref = payload.input_ref[:512] if payload.input_ref else None
        if "output_ref" in fields_set:
            target.output_ref = payload.output_ref[:512] if payload.output_ref else None
            if target.output_ref:
                target.content_hash = _hash_ref(target.output_ref)
            else:
                target.content_hash = None
        if "error_message" in fields_set:
            target.error_message = payload.error_message
        if "document_id" in fields_set and payload.document_id is not None:
            target.document_id = payload.document_id
        if "admin_note" in fields_set:
            target.admin_note = payload.admin_note.strip() if payload.admin_note else None

        target.manual_override = True
        target.updated_at = _now()
        self.db.flush()
        return target

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
        target.manual_override = True
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
                target.content_hash = _hash_ref(name)
            elif step_id == PipelineStepId.OUTPUT:
                tree = self.get_tree(family_tree_id)
                nodes = tree.get("nodes") or []
                if not isinstance(nodes, list) or not nodes:
                    raise ValueError("Cây chưa có node — chạy phân tích hoặc import trước.")
                ref = f"nodes:{len(nodes)}"
                target.status = PipelineStepStatus.DONE
                target.output_ref = ref
                target.content_hash = _hash_ref(ref)
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
                ref = f"documents:{text_doc.id}"
                target.status = PipelineStepStatus.DONE
                target.output_ref = ref
                target.document_id = text_doc.id
                target.content_hash = _hash_ref(ref)
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

    @staticmethod
    def _is_text_file(mime_type: str, filename: str) -> bool:
        lowered = filename.lower()
        if any(lowered.endswith(ext) for ext in TEXT_FILE_EXTENSIONS):
            return True
        return mime_type.startswith(TEXT_FILE_MIME_PREFIXES)

    def _read_text_preview(self, storage: ObjectStorage, file_key: str) -> Optional[str]:
        if not storage.config.enabled:
            return None
        try:
            raw = storage.read_file_head(file_key, max_bytes=8192)
        except ObjectStorageError:
            return None
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
            return None
        normalized = " ".join(text.split())
        if len(normalized) <= PREVIEW_MAX_LEN:
            return normalized
        return normalized[: PREVIEW_MAX_LEN - 1] + "…"

    def _artifact_from_document(self, document_id: int) -> PipelineArtifactResponse:
        document = self.db.get(
            Document,
            document_id,
            options=(selectinload(Document.files),),
        )
        if document is None:
            return PipelineArtifactResponse(kind="none", message=f"Không tìm thấy tài liệu #{document_id}.")

        files = sorted(document.files, key=lambda item: (item.position, item.id))
        storage = ObjectStorage.from_env()
        artifact_files: List[PipelineArtifactFileResponse] = []
        preview_text: Optional[str] = None

        for file_item in files:
            download_url = None
            if storage.config.enabled:
                try:
                    download_url = storage.get_presigned_url(file_item.file_key)
                except ObjectStorageError:
                    download_url = None
            artifact_files.append(
                PipelineArtifactFileResponse(
                    id=file_item.id,
                    filename=file_item.file_name,
                    mime_type=file_item.file_type,
                    url=download_url,
                    size=file_item.size,
                )
            )
            if preview_text is None and self._is_text_file(file_item.file_type, file_item.file_name):
                preview_text = self._read_text_preview(storage, file_item.file_key)

        return PipelineArtifactResponse(
            kind="document",
            document_id=document.id,
            title=document.title,
            type=document.type.value,
            preview_text=preview_text,
            files=artifact_files,
        )

    def _resolve_artifact(self, step: GenealogyPipelineStep, tree: dict) -> PipelineArtifactResponse:
        output_ref = (step.output_ref or "").strip()
        if not output_ref:
            if step.status == PipelineStepStatus.SKIPPED and step.skipped_reason == "vgp_entry":
                return PipelineArtifactResponse(
                    kind="none",
                    message="Nguồn VGP — bước này không áp dụng (đã có full_text / nodes).",
                )
            return PipelineArtifactResponse(kind="none", message="Chưa có artifact.")

        doc_match = DOCUMENT_REF_PATTERN.match(output_ref)
        if doc_match:
            return self._artifact_from_document(int(doc_match.group(1)))

        if step.document_id:
            return self._artifact_from_document(step.document_id)

        nodes_match = NODES_REF_PATTERN.match(output_ref)
        if nodes_match:
            nodes = tree.get("nodes") or []
            node_count = len(nodes) if isinstance(nodes, list) else int(nodes_match.group(1))
            sample_names = [
                str(node.get("name") or "").strip()
                for node in nodes[:5]
                if isinstance(node, dict) and str(node.get("name") or "").strip()
            ]
            preview = ", ".join(sample_names)
            if len(preview) > PREVIEW_MAX_LEN:
                preview = preview[: PREVIEW_MAX_LEN - 1] + "…"
            return PipelineArtifactResponse(
                kind="family_tree",
                node_count=node_count,
                preview_text=preview or None,
            )

        if step.step_id == PipelineStepId.NAME:
            preview = output_ref
            if len(preview) > PREVIEW_MAX_LEN:
                preview = preview[: PREVIEW_MAX_LEN - 1] + "…"
            return PipelineArtifactResponse(kind="text", preview_text=preview)

        preview = output_ref
        if len(preview) > PREVIEW_MAX_LEN:
            preview = preview[: PREVIEW_MAX_LEN - 1] + "…"
        return PipelineArtifactResponse(kind="text", preview_text=preview)
