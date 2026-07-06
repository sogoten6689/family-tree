import os
from typing import Callable

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser
from app.database import database_enabled, get_db
from app.documents.repository import (
    DocumentNotFoundError,
    DocumentRepository,
    DocumentService,
    DocumentValidationError,
)
from app.documents.schemas import (
    DocumentCreateRequest,
    DocumentFileResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdateRequest,
    OcrTransliterateResponse,
    ReorderFilesRequest,
    UploadFilesResponse,
)
from app.documents.storage import ObjectStorage, ObjectStorageError
from app.family_tree_store import FamilyTreeNotFoundError
from app.hannom.errors import HannomApiError


def require_documents_database() -> None:
    if not database_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database chưa được cấu hình. Thiết lập biến môi trường MYSQL_*.",
        )


def _max_upload_bytes() -> int:
    return int(os.getenv("MINIO_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))


def create_documents_router(get_tree: Callable[[str], dict]) -> APIRouter:
    router = APIRouter(
        tags=["Documents"],
        dependencies=[Depends(require_documents_database)],
    )

    def get_storage() -> ObjectStorage:
        storage = ObjectStorage.from_env()
        if storage.config.enabled:
            try:
                storage.ensure_bucket()
            except ObjectStorageError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=str(exc),
                ) from exc
        return storage

    def get_service(
        db: Session = Depends(get_db),
        storage: ObjectStorage = Depends(get_storage),
    ) -> DocumentService:
        return DocumentService(
            DocumentRepository(db),
            storage,
            get_tree=get_tree,
        )

    def _raise_service_error(error: Exception) -> None:
        if isinstance(error, FamilyTreeNotFoundError):
            raise HTTPException(status_code=404, detail=str(error)) from error
        if isinstance(error, DocumentNotFoundError):
            raise HTTPException(status_code=404, detail=str(error)) from error
        if isinstance(error, DocumentValidationError):
            raise HTTPException(status_code=400, detail=str(error)) from error
        if isinstance(error, ObjectStorageError):
            raise HTTPException(status_code=503, detail=str(error)) from error
        if isinstance(error, HannomApiError):
            raise HTTPException(
                status_code=502,
                detail={
                    "message": str(error),
                    "api_code": error.api_code,
                    "upstream_status": error.status_code,
                },
            ) from error
        raise HTTPException(status_code=500, detail="Unexpected document service error") from error

    def _serialize_file(file_item) -> DocumentFileResponse:
        return DocumentFileResponse(
            id=file_item.id,
            file_name=file_item.file_name,
            file_key=file_item.file_key,
            file_type=file_item.file_type,
            size=file_item.size,
            position=file_item.position,
            created_at=file_item.created_at,
            download_url=getattr(file_item, "download_url", None),
        )

    def _serialize_document(document) -> DocumentResponse:
        return DocumentResponse(
            id=document.id,
            family_tree_id=document.family_tree_id,
            title=document.title,
            description=document.description,
            type=document.type,
            created_at=document.created_at,
            files=[_serialize_file(file_item) for file_item in document.files],
        )

    @router.get(
        "/api/family-trees/{tree_id}/documents",
        response_model=DocumentListResponse,
        summary="Danh sách tài liệu của gia phả",
    )
    def list_documents(
        tree_id: str,
        _: AdminUser,
        document_service=Depends(get_service),
    ) -> DocumentListResponse:
        try:
            items = document_service.list_documents(tree_id)
        except Exception as error:
            _raise_service_error(error)
        serialized = [_serialize_document(item) for item in items]
        return DocumentListResponse(total=len(serialized), items=serialized)

    @router.post(
        "/api/family-trees/{tree_id}/documents",
        response_model=DocumentResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Tạo tài liệu cho gia phả",
    )
    def create_document(
        tree_id: str,
        req: DocumentCreateRequest,
        _: AdminUser,
        document_service=Depends(get_service),
        db: Session = Depends(get_db),
    ) -> DocumentResponse:
        try:
            document = document_service.create_document(
                family_tree_id=tree_id,
                title=req.title,
                description=req.description,
                doc_type=req.type,
            )
            db.commit()
            db.refresh(document)
        except Exception as error:
            db.rollback()
            _raise_service_error(error)
        return _serialize_document(document)

    @router.get(
        "/api/documents/{document_id}",
        response_model=DocumentResponse,
        summary="Chi tiết tài liệu",
    )
    def get_document(
        document_id: int,
        _: AdminUser,
        document_service=Depends(get_service),
    ) -> DocumentResponse:
        try:
            document = document_service.get_document(document_id)
        except Exception as error:
            _raise_service_error(error)
        return _serialize_document(document)

    @router.put(
        "/api/documents/{document_id}",
        response_model=DocumentResponse,
        summary="Cập nhật tài liệu",
    )
    def update_document(
        document_id: int,
        req: DocumentUpdateRequest,
        _: AdminUser,
        document_service=Depends(get_service),
        db: Session = Depends(get_db),
    ) -> DocumentResponse:
        if req.title is None and req.description is None and req.type is None:
            raise HTTPException(status_code=400, detail="No fields to update")
        try:
            document = document_service.update_document(
                document_id,
                title=req.title,
                description=req.description,
                doc_type=req.type,
            )
            db.commit()
        except Exception as error:
            db.rollback()
            _raise_service_error(error)
        return _serialize_document(document)

    @router.delete(
        "/api/documents/{document_id}/files/{file_id}",
        response_model=DocumentResponse,
        summary="Xóa file khỏi tài liệu",
    )
    def delete_document_file(
        document_id: int,
        file_id: int,
        _: AdminUser,
        document_service=Depends(get_service),
        db: Session = Depends(get_db),
    ) -> DocumentResponse:
        try:
            document = document_service.delete_file(document_id, file_id)
            db.commit()
        except Exception as error:
            db.rollback()
            _raise_service_error(error)
        return _serialize_document(document)

    @router.post(
        "/api/documents/{document_id}/upload-files",
        response_model=UploadFilesResponse,
        summary="Upload file vào tài liệu",
    )
    async def upload_files(
        document_id: int,
        _: AdminUser,
        document_service=Depends(get_service),
        db: Session = Depends(get_db),
        files: list[UploadFile] = File(...),
    ) -> UploadFilesResponse:
        if not files:
            raise HTTPException(status_code=400, detail="At least one file is required.")

        max_bytes = _max_upload_bytes()
        uploads: list[tuple[str, str, object, int]] = []

        for upload in files:
            content = await upload.read()
            size = len(content)
            if size <= 0:
                raise HTTPException(status_code=400, detail=f"File '{upload.filename}' is empty.")
            if size > max_bytes:
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{upload.filename}' exceeds max upload size ({max_bytes} bytes).",
                )

            from io import BytesIO

            uploads.append(
                (
                    upload.filename or "upload.bin",
                    upload.content_type or "application/octet-stream",
                    BytesIO(content),
                    size,
                )
            )

        try:
            created = document_service.upload_files(document_id, uploads)
            db.commit()
            for item in created:
                db.refresh(item)
                try:
                    item.download_url = document_service.storage.get_presigned_url(item.file_key)  # type: ignore[attr-defined]
                except ObjectStorageError:
                    item.download_url = None  # type: ignore[attr-defined]
        except Exception as error:
            db.rollback()
            _raise_service_error(error)

        return UploadFilesResponse(
            document_id=document_id,
            uploaded=[_serialize_file(item) for item in created],
        )

    @router.post(
        "/api/documents/{document_id}/ocr-transliterate",
        response_model=OcrTransliterateResponse,
        summary="OCR Hán-Nôm và phiên âm Quốc ngữ (Kim Hán Nôm API)",
    )
    async def ocr_transliterate(
        document_id: int,
        _: AdminUser,
        document_service=Depends(get_service),
        db: Session = Depends(get_db),
        image: UploadFile = File(..., description="Ảnh gia phả chữ Hán-Nôm"),
    ) -> OcrTransliterateResponse:
        content = await image.read()
        max_bytes = _max_upload_bytes()
        if len(content) <= 0:
            raise HTTPException(status_code=400, detail="File ảnh rỗng.")
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File vượt quá giới hạn upload ({max_bytes} bytes).",
            )

        filename = image.filename or "hannom.jpg"
        try:
            result = document_service.ocr_transliterate_and_save(
                document_id,
                content,
                filename,
            )
            db.commit()
            saved_file = result["saved_file"]
            db.refresh(saved_file)
            try:
                saved_file.download_url = document_service.storage.get_presigned_url(saved_file.file_key)  # type: ignore[attr-defined]
            except ObjectStorageError:
                saved_file.download_url = None  # type: ignore[attr-defined]
        except Exception as error:
            db.rollback()
            _raise_service_error(error)

        result_document = result["result_document"]
        return OcrTransliterateResponse(
            source_document_id=document_id,
            result_document_id=result_document.id,
            ocr_text=result["ocr_text"],
            ocr_lines=result["ocr_lines"],
            transcription_lines=result["transcription_lines"],
            transcription_text=result["transcription_text"],
            saved_file=_serialize_file(saved_file),
            result_document=_serialize_document(result_document),
        )

    @router.put(
        "/api/documents/{document_id}/reorder-files",
        response_model=DocumentResponse,
        summary="Cập nhật thứ tự file trong tài liệu",
    )
    def reorder_files(
        document_id: int,
        req: ReorderFilesRequest,
        _: AdminUser,
        document_service=Depends(get_service),
        db: Session = Depends(get_db),
    ) -> DocumentResponse:
        ordered_items = [(item.id, item.position) for item in req.files]
        try:
            document = document_service.reorder_files(document_id, ordered_items)
            db.commit()
        except Exception as error:
            db.rollback()
            _raise_service_error(error)
        return _serialize_document(document)

    return router
