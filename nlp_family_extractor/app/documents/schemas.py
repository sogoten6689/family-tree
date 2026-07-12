from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.documents.models import DocumentType


class DocumentCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    type: DocumentType
    subtype: Optional[str] = Field(default=None, max_length=64)


class DocumentUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    type: Optional[DocumentType] = None
    subtype: Optional[str] = Field(default=None, max_length=64)


class DocumentFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    file_key: str
    file_type: str
    size: int
    position: int
    created_at: datetime
    download_url: Optional[str] = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    family_tree_id: str
    title: str
    description: Optional[str] = None
    type: DocumentType
    subtype: Optional[str] = None
    created_at: datetime
    files: List[DocumentFileResponse] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    total: int
    items: List[DocumentResponse]


class FileReorderItem(BaseModel):
    id: int
    position: int = Field(ge=0)


class ReorderFilesRequest(BaseModel):
    files: List[FileReorderItem] = Field(min_length=1)


class UploadFilesResponse(BaseModel):
    document_id: int
    uploaded: List[DocumentFileResponse]


class OcrTransliterateResponse(BaseModel):
    source_document_id: int
    result_document_id: int
    ocr_text: str
    ocr_lines: List[str]
    transcription_lines: List[str]
    transcription_text: str
    saved_file: DocumentFileResponse
    result_document: DocumentResponse


class OcrBatchRequest(BaseModel):
    file_ids: Optional[List[int]] = Field(
        default=None,
        description="Danh sách file id; để trống = tất cả ảnh. Chỉ định 1 id = OCR từng trang.",
    )
    skip_existing: bool = Field(default=True, description="Bỏ qua trang đã có file kết quả OCR")
    merge_pages: bool = Field(default=True, description="Ghép tất cả trang đã OCR vào combined_transcription.txt")
    sync_pipeline: bool = Field(default=True, description="Đồng bộ pipeline sau OCR")


class OcrBatchItemResult(BaseModel):
    file_id: int
    file_name: str
    result_document_id: int
    transcription_text: str


class OcrBatchError(BaseModel):
    file_id: int
    file_name: str
    error: str


class OcrBatchResponse(BaseModel):
    source_document_id: int
    processed: int
    skipped: int
    results: List[OcrBatchItemResult] = Field(default_factory=list)
    errors: List[OcrBatchError] = Field(default_factory=list)
    combined_transcription_text: str = ""
    merged_page_count: int = 0
    pipeline_synced: bool = False
