from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.documents.models import DocumentType


class DocumentCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    type: DocumentType


class DocumentUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    type: Optional[DocumentType] = None


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
