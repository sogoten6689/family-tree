from __future__ import annotations

from typing import Callable, Iterable, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from io import BytesIO

from app.documents.models import Document, DocumentFile, DocumentType
from app.documents.storage import ObjectStorage, ObjectStorageError
from app.hannom.errors import HannomApiError
from app.hannom.pipeline import process_hannom_image_to_vietnamese


class DocumentNotFoundError(Exception):
    pass


class DocumentValidationError(Exception):
    pass


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_result_document_for_source(self, source_document_id: int) -> Optional[Document]:
        marker = f"source_document_id={source_document_id}"
        stmt = (
            select(Document)
            .where(
                Document.type == DocumentType.KET_QUA_VAN_BAN,
                Document.description == marker,
            )
            .options(selectinload(Document.files))
            .limit(1)
        )
        return self.db.scalar(stmt)

    def list_by_family_tree(self, family_tree_id: str) -> List[Document]:
        stmt = (
            select(Document)
            .where(Document.family_tree_id == family_tree_id)
            .options(selectinload(Document.files))
            .order_by(Document.created_at.desc(), Document.id.desc())
        )
        documents = list(self.db.scalars(stmt).all())
        for document in documents:
            document.files.sort(key=lambda item: (item.position, item.id))
        return documents

    def get(self, document_id: int) -> Document:
        document = self.db.get(
            Document,
            document_id,
            options=(selectinload(Document.files),),
        )
        if document is None:
            raise DocumentNotFoundError(f"document '{document_id}' not found")
        document.files.sort(key=lambda item: (item.position, item.id))
        return document

    def create(
        self,
        *,
        family_tree_id: str,
        title: str,
        description: Optional[str],
        doc_type: DocumentType,
    ) -> Document:
        document = Document(
            family_tree_id=family_tree_id,
            title=title.strip(),
            description=description.strip() if description else None,
            type=doc_type,
        )
        self.db.add(document)
        self.db.flush()
        self.db.refresh(document)
        return document

    def next_file_position(self, document_id: int) -> int:
        stmt = (
            select(DocumentFile.position)
            .where(DocumentFile.document_id == document_id)
            .order_by(DocumentFile.position.desc(), DocumentFile.id.desc())
            .limit(1)
        )
        current = self.db.scalar(stmt)
        return 0 if current is None else int(current) + 1

    def add_file(
        self,
        *,
        document_id: int,
        file_name: str,
        file_key: str,
        file_type: str,
        size: int,
        position: int,
    ) -> DocumentFile:
        record = DocumentFile(
            document_id=document_id,
            file_name=file_name,
            file_key=file_key,
            file_type=file_type,
            size=size,
            position=position,
        )
        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)
        return record

    def reorder_files(self, document_id: int, ordered_items: Iterable[tuple[int, int]]) -> Document:
        document = self.get(document_id)
        file_map = {item.id: item for item in document.files}
        requested_ids = [file_id for file_id, _ in ordered_items]

        if len(requested_ids) != len(set(requested_ids)):
            raise DocumentValidationError("Duplicate file ids in reorder payload.")

        if set(requested_ids) != set(file_map.keys()):
            raise DocumentValidationError("Reorder payload must include all files of the document.")

        positions = [position for _, position in ordered_items]
        if len(positions) != len(set(positions)):
            raise DocumentValidationError("Duplicate positions in reorder payload.")

        for file_id, position in ordered_items:
            file_map[file_id].position = position

        self.db.flush()
        return self.get(document_id)

    def update(
        self,
        document_id: int,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        doc_type: Optional[DocumentType] = None,
    ) -> Document:
        document = self.get(document_id)
        if title is not None:
            document.title = title.strip()
        if description is not None:
            document.description = description.strip() if description else None
        if doc_type is not None:
            document.type = doc_type
        self.db.flush()
        return self.get(document_id)

    def get_file(self, document_id: int, file_id: int) -> DocumentFile:
        document = self.get(document_id)
        record = next((item for item in document.files if item.id == file_id), None)
        if record is None:
            raise DocumentNotFoundError(f"file '{file_id}' not found in document '{document_id}'")
        return record

    def delete_file(self, document_id: int, file_id: int) -> DocumentFile:
        record = self.get_file(document_id, file_id)
        self.db.delete(record)
        self.db.flush()
        return record


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        storage: ObjectStorage,
        *,
        get_tree: Callable[[str], dict],
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.get_tree = get_tree

    def _ensure_family_tree_exists(self, family_tree_id: str) -> None:
        self.get_tree(family_tree_id)

    def _attach_download_urls(self, document: Document) -> Document:
        if not self.storage.config.enabled:
            return document
        for file_item in document.files:
            try:
                file_item.download_url = self.storage.get_presigned_url(file_item.file_key)  # type: ignore[attr-defined]
            except ObjectStorageError:
                file_item.download_url = None  # type: ignore[attr-defined]
        return document

    def list_documents(self, family_tree_id: str) -> List[Document]:
        self._ensure_family_tree_exists(family_tree_id)
        documents = self.repository.list_by_family_tree(family_tree_id)
        return [self._attach_download_urls(document) for document in documents]

    def create_document(
        self,
        *,
        family_tree_id: str,
        title: str,
        description: Optional[str],
        doc_type: DocumentType,
    ) -> Document:
        self._ensure_family_tree_exists(family_tree_id)
        return self.repository.create(
            family_tree_id=family_tree_id,
            title=title,
            description=description,
            doc_type=doc_type,
        )

    def get_document(self, document_id: int) -> Document:
        document = self.repository.get(document_id)
        return self._attach_download_urls(document)

    def update_document(
        self,
        document_id: int,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        doc_type: Optional[DocumentType] = None,
    ) -> Document:
        if title is None and description is None and doc_type is None:
            raise DocumentValidationError("No fields to update.")
        document = self.repository.update(
            document_id,
            title=title,
            description=description,
            doc_type=doc_type,
        )
        return self._attach_download_urls(document)

    def delete_file(self, document_id: int, file_id: int) -> Document:
        record = self.repository.get_file(document_id, file_id)
        if self.storage.config.enabled:
            try:
                self.storage.delete_file(record.file_key)
            except ObjectStorageError as exc:
                raise ObjectStorageError(f"Cannot delete file from storage: {exc}") from exc
        self.repository.delete_file(document_id, file_id)
        return self.get_document(document_id)

    def reorder_files(self, document_id: int, ordered_items: list[tuple[int, int]]) -> Document:
        document = self.repository.reorder_files(document_id, ordered_items)
        return self._attach_download_urls(document)

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        cleaned = filename.replace("\\", "/").split("/")[-1].strip()
        if not cleaned:
            raise DocumentValidationError("Invalid file name.")
        return cleaned[:255]

    def build_file_key(self, *, family_tree_id: str, document_id: int, file_name: str) -> str:
        from uuid import uuid4

        safe_name = self._sanitize_filename(file_name)
        return f"family-trees/{family_tree_id}/documents/{document_id}/{uuid4().hex}_{safe_name}"

    def upload_files(
        self,
        document_id: int,
        uploads: list[tuple[str, str, object, int]],
    ) -> list[DocumentFile]:
        if not self.storage.config.enabled:
            raise ObjectStorageError("Object storage is not configured.")

        document = self.repository.get(document_id)
        self.storage.ensure_bucket()

        created: list[DocumentFile] = []
        position = self.repository.next_file_position(document_id)

        for file_name, content_type, file_obj, size in uploads:
            safe_name = self._sanitize_filename(file_name)
            file_key = self.build_file_key(
                family_tree_id=document.family_tree_id,
                document_id=document_id,
                file_name=safe_name,
            )
            try:
                self.storage.upload_file(
                    file_key,
                    file_obj,  # type: ignore[arg-type]
                    content_type=content_type or "application/octet-stream",
                    size=size,
                )
            except ObjectStorageError:
                for uploaded in created:
                    try:
                        self.storage.delete_file(uploaded.file_key)
                    except ObjectStorageError:
                        pass
                raise

            record = self.repository.add_file(
                document_id=document_id,
                file_name=safe_name,
                file_key=file_key,
                file_type=content_type or "application/octet-stream",
                size=size,
                position=position,
            )
            created.append(record)
            position += 1

        return created

    def ocr_transliterate_and_save(
        self,
        document_id: int,
        file_bytes: bytes,
        filename: str,
        *,
        ocr_id: int | None = None,
        lang_type: int | None = None,
    ) -> dict:
        if not self.storage.config.enabled:
            raise ObjectStorageError("Object storage is not configured.")

        source = self.repository.get(document_id)
        if source.type not in {
            DocumentType.HAN_NOM,
            DocumentType.HINH_ANH,
            DocumentType.VAN_BAN,
        }:
            raise DocumentValidationError(
                "Chỉ hỗ trợ OCR/phiên âm từ tài liệu loại han_nom, hinh_anh hoặc van_ban.",
            )

        try:
            pipeline_result = process_hannom_image_to_vietnamese(
                file_bytes,
                filename,
                ocr_id=ocr_id,
                lang_type=lang_type,
            )
        except HannomApiError:
            raise
        except ValueError as exc:
            raise DocumentValidationError(str(exc)) from exc

        marker = f"source_document_id={document_id}"
        result_document = self.repository.find_result_document_for_source(document_id)
        if result_document is None:
            result_document = self.repository.create(
                family_tree_id=source.family_tree_id,
                title=f"{source.title} - Kết quả phiên âm",
                description=marker,
                doc_type=DocumentType.KET_QUA_VAN_BAN,
            )

        transcription_text = str(pipeline_result["transcription_text"])
        safe_source = self._sanitize_filename(filename)
        result_name = f"{safe_source.rsplit('.', 1)[0]}_transcription.txt"
        encoded = transcription_text.encode("utf-8")
        buffer = BytesIO(encoded)

        created_files = self.upload_files(
            result_document.id,
            [
                (
                    result_name,
                    "text/plain; charset=utf-8",
                    buffer,
                    len(encoded),
                )
            ],
        )

        return {
            "source_document": source,
            "result_document": self.get_document(result_document.id),
            "ocr_text": str(pipeline_result["ocr_text"]),
            "ocr_lines": list(pipeline_result["ocr_lines"]),
            "transcription_lines": list(pipeline_result["transcription_lines"]),
            "transcription_text": transcription_text,
            "saved_file": created_files[0],
        }
