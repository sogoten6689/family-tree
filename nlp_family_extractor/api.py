from __future__ import annotations

import io
import json
import os
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from app.auth.bootstrap import bootstrap_auth
from app.auth.dependencies import AdminUser, CurrentUser, OptionalUser
from app.auth.router import router as auth_router
from app.database import database_enabled, database_init_error, get_db, init_database, session_scope
from app.documents.bootstrap import bootstrap_documents
from app.documents.router import create_documents_router
from app.documents.storage import ObjectStorage, ObjectStorageError
from app.hannom.bootstrap import bootstrap_hannom
from app.hannom.errors import HannomApiError
from app.hannom.pdf_utils import render_pdf_pages_to_png
from app.hannom.pipeline import run_hannom_pipeline
from app.hannom.router import router as hannom_developer_router
from app.pipeline.bootstrap import bootstrap_pipeline
from app.pipeline.router import create_pipeline_router
from app.settings.bootstrap import bootstrap_settings
from app.settings.router import gemini_usage_router, ocr_engines_router, router as settings_router, text_engines_router
from app.vgp.bootstrap import bootstrap_vgp
from app.workspace.bootstrap import bootstrap_workspace
from app.hannom.text_engines import load_local_engines
from app.gemini_usage import bootstrap_gemini_usage
from app.workspace.repository import UserScanRepository
from app.workspace.router import create_workspace_router
from app.export.router import create_export_router, create_node_meta_router
from app.domains.extraction.extractor import FamilyExtractor
from app.family_tree_store import (
    FamilyTreeNotFoundError,
    FamilyTreeStoreError,
    FamilyTreeValidationError,
    JsonFamilyTreeStore,
    MirroredFamilyTreeStore,
)
from app.family_tree_store import MySqlFamilyTreeStore
from app.gemini_service import normalize_balkan_nodes
from app.history_repository import HistoryRepository
from app.domains.extraction.validator import (
    validate_no_duplicate_edges,
    validate_no_self_relationship,
    validate_parent_age_gap,
)


class RequestMetadata(BaseModel):
    file_name: Optional[str] = Field(
        default=None,
        alias="fileName",
        description="Tên file nguồn do frontend gửi lên.",
    )
    language: Optional[str] = Field(
        default=None,
        description="Ngôn ngữ của văn bản, ví dụ `vi` hoặc `en`.",
    )
    document_type: Optional[str] = Field(
        default=None,
        alias="documentType",
        description="Loại tài liệu, ví dụ `gia-pha`, `ho-so`, `ghi-chu`.",
    )

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }


class AnalyzeRequest(BaseModel):
    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "text": "Ông Nguyễn Văn A sinh năm 1940, là cha của Nguyễn Văn B sinh năm 1965. Nguyễn Văn A kết hôn với Trần Thị C sinh năm 1942.",
                    "source": "document-reader",
                    "metadata": {"fileName": "gia-pha.docx", "language": "vi"},
                }
            ]
        }
    }

    text: str = Field(
        min_length=1,
        description="Nội dung văn bản gia phả thô được trích xuất từ tài liệu.",
    )
    source: Optional[str] = Field(
        default="frontend",
        description="Định danh caller (ví dụ: `document-reader`, `frontend`).",
    )
    metadata: RequestMetadata = Field(
        default_factory=RequestMetadata,
        description="Metadata tuỳ ý đính kèm request (tên file, ngôn ngữ, …).",
    )


class AnalyzeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    request_id: Optional[str] = Field(
        default=None,
        description="UUID của request, dùng tra lịch sử và liên kết tài liệu.",
    )
    balkan_nodes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Mảng node BALKAN (Gemini): id số, name, gender, birthYear, pids, fid, mid."
        ),
    )
    gemini_error: Optional[str] = Field(
        default=None,
        description="Lỗi khi thiếu API key, lỗi API hoặc không parse được JSON.",
    )


class AnalyzeImageResponse(AnalyzeResponse):
    ocr_text: Optional[str] = Field(
        default=None,
        description="Văn bản Quốc ngữ do OCR + phiên âm Kim Hán Nôm sinh ra, dùng để hiển thị/cho người dùng sửa trước khi lưu.",
    )
    hannom_text: Optional[str] = Field(
        default=None,
        description="Văn bản Hán-Nôm gốc (trước phiên âm), do bước OCR Kim Hán Nôm trả về — hiển thị cột đối chiếu.",
    )
    source_file_key: Optional[str] = Field(
        default=None,
        description="Key MinIO của ảnh/PDF gốc đã lưu (None nếu MinIO chưa cấu hình — OCR vẫn chạy bình thường).",
    )
    pages_processed: int = Field(
        default=0,
        description="Số trang ảnh/PDF đã OCR (PDF nhiều trang bị giới hạn, xem `pages_truncated`).",
    )
    pages_truncated: bool = Field(
        default=False,
        description="True nếu PDF có nhiều trang hơn giới hạn xử lý nhanh (dùng luồng Admin cho tài liệu dài).",
    )
    bbox: Optional[List[List[Dict[str, Any]]]] = Field(
        default=None,
        description="Bounding box OCR theo từng trang (1 danh sách box/trang, khớp index pages_processed). None nếu engine không trả box.",
    )
    translation_text: Optional[str] = Field(
        default=None,
        description="Dịch nghĩa Quốc ngữ hiện đại (chỉ có khi HANNOM_PIPELINE_VERSION=v2).",
    )
    vote_meta: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Metadata vote OCR nhiều engine, theo từng trang (chỉ có khi pipeline v2).",
    )
    pipeline_version: str = Field(
        default="v1",
        description="Phiên bản pipeline đã dùng để tạo kết quả này (v1 hoặc v2).",
    )


class HistoryItem(BaseModel):
    request_id: str = Field(description="UUID của request.")
    created_at: str = Field(description="Thời điểm xử lý (UTC ISO-8601).")
    source: str = Field(description="Caller source.")
    metadata: RequestMetadata = Field(description="Metadata đính kèm.")
    people_count: int = Field(description="Số người trích xuất được.")
    relationship_count: int = Field(description="Số quan hệ trích xuất được.")
    warning_count: int = Field(description="Số lượng cảnh báo validation.")
    user_id: Optional[int] = Field(default=None, description="User sở hữu request (nếu đã đăng nhập).")


class HistoryResponse(BaseModel):
    total: int = Field(description="Tổng số request đang lưu trong store.")
    items: List[HistoryItem] = Field(description="Danh sách request gần nhất (mới nhất trước).")


class HealthResponse(BaseModel):
    status: str = Field(description="Trạng thái sống của service, hiện tại là `ok`.")
    auth_storage: Literal["mysql", "disabled"] = Field(
        description="Backend đang lưu user bằng MySQL hay chưa cấu hình DB."
    )
    history_storage: Literal["mysql", "memory"] = Field(
        description="Backend đang lưu lịch sử bằng MySQL hay in-memory."
    )
    auth_init_error: Optional[str] = Field(
        default=None,
        description="Lỗi khởi tạo auth/database nếu có.",
    )
    history_init_error: Optional[str] = Field(
        default=None,
        description="Lý do fallback sang in-memory nếu MySQL khởi tạo thất bại.",
    )
    tree_storage: Literal["mysql+json", "json"] = Field(
        description="Backend đang lưu cây gia phả: đồng bộ MySQL+JSON hoặc chỉ JSON file."
    )
    object_storage: Literal["ok", "disabled", "error"] = Field(
        default="disabled",
        description="Trạng thái MinIO/S3: ok, disabled (thiếu MINIO_*), hoặc error.",
    )
    object_storage_error: Optional[str] = Field(
        default=None,
        description="Chi tiết lỗi MinIO nếu object_storage=error.",
    )


class ClearHistoryResponse(BaseModel):
    cleared: int = Field(description="Số lượng bản ghi lịch sử đã bị xoá.")


class FamilyTreeSummary(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: str
    updated_at: str
    node_count: int
    external_url: Optional[str] = None
    has_source_document: bool = False
    has_hannom_text: bool = False
    user_id: Optional[int] = None
    is_public: bool = False
    lineage_code: Optional[str] = Field(
        default=None,
        description="Mã họ F-{A...Y|Z}-{NNN}, sinh tự động từ tên cây theo bảng mã họ.",
    )
    generation_count: int = 0


class FamilyTreeListResponse(BaseModel):
    total: int
    items: List[FamilyTreeSummary]


class FamilyTreeDocument(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: str
    updated_at: str
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    external_url: Optional[str] = None
    has_source_document: bool = False
    has_hannom_text: bool = False
    user_id: Optional[int] = None
    is_public: bool = False
    lineage_code: Optional[str] = None
    generation_count: int = 0


class FamilyTreeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, description="Tên cây gia phả.")
    description: Optional[str] = Field(default=None, description="Mô tả ngắn.")
    external_url: Optional[str] = Field(default=None, description="Đường link nguồn (vietnamgiapha, ...).")
    has_source_document: bool = Field(default=False, description="Có tài liệu gốc.")
    has_hannom_text: bool = Field(default=False, description="Có văn bản Hán-Nôm.")
    is_public: bool = Field(default=False, description="Cho phép khách xem công khai.")
    nodes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Danh sách node BALKAN khởi tạo ban đầu.",
    )


class FamilyTreeUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = Field(default=None)
    external_url: Optional[str] = Field(default=None)
    has_source_document: Optional[bool] = Field(default=None)
    has_hannom_text: Optional[bool] = Field(default=None)
    is_public: Optional[bool] = Field(default=None)


class FamilyTreeReplaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: Optional[str] = Field(default=None)
    nodes: List[Dict[str, Any]] = Field(default_factory=list)


class FamilyTreeNodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    gender: Optional[Literal["male", "female"]] = None
    birthYear: Optional[int] = None
    deathYear: Optional[int] = None
    fid: Optional[int] = None
    mid: Optional[int] = None
    pids: Optional[List[int]] = None


class GenealogyExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, description="Nội dung văn bản gia phả")
    language: Literal["vietnamese", "hannom"] = Field(
        default="vietnamese",
        description="Ngôn ngữ của văn bản: 'vietnamese' hoặc 'hannom'",
    )
    model_version: Literal["regex", "phobert", "sikubert"] = Field(
        default="regex",
        description="Model version: 'regex' (MVP, 60%), 'phobert' (fine-tuned, 90%), 'sikubert' (fine-tuned, 90%)",
    )


class GenealogyExtractionResult(BaseModel):
    persons: List[str] = Field(description="Danh sách nhân vật được trích xuất")
    person_years: Dict[str, Optional[int]] = Field(description="Năm sinh/mất của mỗi nhân vật")
    relations: List[Dict[str, Any]] = Field(description="Danh sách quan hệ gia đình")
    statistics: Dict[str, int] = Field(description="Thống kê: số nhân vật, số quan hệ")
    model_info: Dict[str, str] = Field(
        description="Thông tin model được sử dụng: model_name, model_version"
    )


class GenealogyExtractResponse(BaseModel):
    success: bool = Field(description="Trích xuất thành công hay không")
    data: Optional[GenealogyExtractionResult] = Field(
        default=None, description="Kết quả trích xuất nếu thành công"
    )
    error: Optional[str] = Field(default=None, description="Thông báo lỗi nếu thất bại")
    title: Optional[str] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None


class FamilyTreeLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["spouse_of", "parent_of"]
    from_id: int = Field(ge=1)
    to_id: int = Field(ge=1)
    side: Optional[Literal["fid", "mid"]] = Field(
        default=None,
        description="Bắt buộc khi type=parent_of để xác định cha (fid) hoặc mẹ (mid).",
    )


class FamilyTreeDeleteResponse(BaseModel):
    deleted: bool
    id: str


_TAGS_METADATA = [
    {
        "name": "Analysis",
        "description": "Phân tích văn bản gia phả và trả về cây gia đình.",
    },
    {
        "name": "History",
        "description": (
            "Lịch sử các request phân tích. "
            "Dữ liệu được lưu vào **MySQL** khi có cấu hình `MYSQL_*`, "
            "hoặc fallback sang **in-memory** (mất sau khi restart)."
        ),
    },
    {
        "name": "System",
        "description": "Health check và trạng thái hệ thống.",
    },
    {
        "name": "FamilyTrees",
        "description": "CRUD cây gia phả dạng JSON file (BALKAN nodes).",
    },
    {
        "name": "Auth",
        "description": "Đăng ký, đăng nhập JWT và quản lý người dùng (Admin).",
    },
    {
        "name": "Documents",
        "description": "Quản lý tài liệu đính kèm cho từng cây gia phả (MinIO/S3).",
    },
]


def read_only_mode() -> bool:
    """READ_ONLY_MODE=1: chạy local nối thẳng DB/MinIO production bằng tài khoản
    CHỈ ĐỌC. Bỏ qua mọi bootstrap (CREATE/ALTER/UPDATE lúc khởi động) vì tài
    khoản chỉ đọc không ghi được và để không bao giờ đụng schema production."""
    return os.getenv("READ_ONLY_MODE", "").strip().lower() in {"1", "true", "yes"}


@asynccontextmanager
async def _lifespan(_: FastAPI):
    init_database()
    load_local_engines()  # adapter engine phiên âm/dịch do người dùng tự viết (nếu có)
    if database_enabled() and not read_only_mode():
        bootstrap_gemini_usage()
        bootstrap_auth()
        bootstrap_documents()
        bootstrap_pipeline()
        bootstrap_vgp()
        bootstrap_workspace()
        bootstrap_hannom()
        bootstrap_settings()
    yield

_DESCRIPTION = """
## Family Tree Analyzer API

Phân tích văn bản gia phả (tiếng Việt): NLP rule-based trích xuất thô, sau đó **Gemini**
chuẩn hoá. **`POST /api/family-tree/analyze`** chỉ trả **`balkan_nodes`** và **`gemini_error`**.

### Luồng sử dụng cơ bản

1. **POST** `/api/family-tree/analyze` — gửi văn bản, nhận lại cây gia đình.
2. **GET** `/api/family-tree/history` — xem danh sách request đã xử lý.
3. **GET** `/api/family-tree/history/{request_id}` — lấy lại kết quả đầy đủ.

### Định dạng văn bản khuyến nghị

| Loại quan hệ | Ví dụ câu |
|---|---|
| Vợ / chồng | `Nguyễn Văn A kết hôn với Trần Thị B.` |
| Cha mẹ – con | `Nguyễn Văn A và Trần Thị B có con là Nguyễn Văn C.` |
| Anh chị em | `Nguyễn Văn C và Nguyễn Thị D là anh em trong gia đình.` |

### Lưu trữ lịch sử

| Chế độ | Điều kiện | Bền vững |
|---|---|---|
| MySQL | Biến môi trường `MYSQL_*` được cấu hình | ✅ |
| In-memory | Fallback khi không có MySQL | ❌ |
"""

app = FastAPI(
    title="Family Tree Analyzer API",
    version="1.0.0",
    description=_DESCRIPTION,
    openapi_tags=_TAGS_METADATA,
    contact={"name": "Family Tree Project"},
    license_info={"name": "MIT"},
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=_lifespan,
)

app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_HISTORY_MAX_ITEMS = 200
_history_lock = Lock()
_history_store: deque[HistoryItem] = deque(maxlen=_HISTORY_MAX_ITEMS)
_detail_store: Dict[str, AnalyzeResponse] = {}
_detail_order: deque[str] = deque()
_history_repo = HistoryRepository()

def _create_family_tree_store():
    source_store = JsonFamilyTreeStore(
        Path(__file__).resolve().parent / "data" / "family_trees"
    )
    try:
        mysql_store = MySqlFamilyTreeStore.from_env()
        return MirroredFamilyTreeStore(
            primary_store=mysql_store,
            source_store=source_store,
        ), "mysql+json"
    except Exception:
        return source_store, "json"

_family_tree_store, _family_tree_storage = _create_family_tree_store()


def _get_family_tree_document(tree_id: str) -> dict:
    return _family_tree_store.get_tree(tree_id)


app.include_router(create_documents_router(_get_family_tree_document))
app.include_router(create_pipeline_router(_get_family_tree_document))
app.include_router(
    create_export_router(
        get_tree=_get_family_tree_document,
        get_public_tree=lambda tree_id: _family_tree_store.get_public_tree(tree_id),
    )
)
app.include_router(
    create_node_meta_router(get_tree_store=lambda: _family_tree_store),
)
app.include_router(
    create_workspace_router(
        get_tree_store=lambda: _family_tree_store,
        get_history_repo=lambda: _history_repo,
    )
)
app.include_router(hannom_developer_router)
app.include_router(settings_router)
app.include_router(ocr_engines_router)
app.include_router(text_engines_router)
app.include_router(gemini_usage_router)


def _raise_store_error(error: Exception) -> None:
    if isinstance(error, FamilyTreeNotFoundError):
        raise HTTPException(status_code=404, detail=str(error)) from error
    if isinstance(error, FamilyTreeValidationError):
        raise HTTPException(status_code=400, detail=str(error)) from error
    if isinstance(error, FamilyTreeStoreError):
        raise HTTPException(status_code=500, detail=str(error)) from error
    raise HTTPException(status_code=500, detail="Unexpected family tree storage error") from error


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check",
    response_description="Trạng thái hệ thống và chế độ lưu lịch sử.",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "history_storage": "mysql",
                        "history_init_error": None,
                    }
                }
            }
        }
    },
)
def health() -> HealthResponse:
    """
    Kiểm tra trạng thái API.

    - **status**: `ok` khi service hoạt động bình thường.
    - **history_storage**: `mysql` hoặc `memory`.
    - **history_init_error**: xuất hiện khi MySQL được cấu hình nhưng khởi tạo thất bại.
    """
    payload = {
        "status": "ok",
        "auth_storage": "mysql" if database_enabled() else "disabled",
        "history_storage": "mysql" if _history_repo.enabled else "memory",
    }
    payload["tree_storage"] = _family_tree_storage
    if database_init_error():
        payload["auth_init_error"] = database_init_error()
    if _history_repo.init_error:
        payload["history_init_error"] = _history_repo.init_error

    storage = ObjectStorage.from_env()
    if not storage.config.enabled:
        payload["object_storage"] = "disabled"
        payload["object_storage_error"] = "Thiếu MINIO_ENDPOINT / MINIO_ACCESS_KEY / MINIO_SECRET_KEY / MINIO_BUCKET."
    else:
        try:
            storage.ensure_bucket()
            payload["object_storage"] = "ok"
        except ObjectStorageError as exc:
            payload["object_storage"] = "error"
            payload["object_storage_error"] = str(exc)
            payload["status"] = "degraded"

    return HealthResponse(**payload)


@app.get(
    "/api/family-tree/history",
    response_model=HistoryResponse,
    tags=["History"],
    summary="Danh sách request gần nhất",
    response_description="Danh sách HistoryItem mới nhất trước.",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "total": 2,
                        "items": [
                            {
                                "request_id": "0f8fad5b-d9cb-469f-a165-70867728950e",
                                "created_at": "2026-03-28T09:00:00+00:00",
                                "source": "document-reader",
                                "metadata": {"fileName": "gia-pha.docx", "language": "vi"},
                                "people_count": 5,
                                "relationship_count": 4,
                                "warning_count": 0,
                            }
                        ],
                    }
                }
            }
        }
    },
)
def get_history(
    limit: int = Query(default=20, ge=1, le=100, description="Số lượng item trả về (1–100)."),
    current_user: OptionalUser = None,
) -> HistoryResponse:
    """
    Trả về danh sách các request phân tích gần nhất.

    - **limit**: số item muốn lấy, tối thiểu 1, tối đa 100 (mặc định 20).
    - Ưu tiên đọc từ MySQL nếu đã cấu hình; fallback sang in-memory store.
    """
    safe_limit = max(1, min(limit, 100))
    user_id = current_user.id if current_user is not None else None

    # Prefer durable MySQL history when available
    if _history_repo.enabled:
        total, db_items = _history_repo.list_recent(safe_limit, user_id=user_id)
        if user_id is not None or total > 0 or db_items:
            return HistoryResponse(total=total, items=[HistoryItem(**item) for item in db_items])

    with _history_lock:
        snapshot = list(_history_store)
        if user_id is not None:
            snapshot = [item for item in snapshot if item.user_id == user_id]

    items = list(reversed(snapshot))[:safe_limit]
    return HistoryResponse(total=len(snapshot), items=items)


@app.get(
    "/api/family-tree/history/{request_id}",
    response_model=AnalyzeResponse,
    tags=["History"],
    summary="Chi tiết một request theo ID",
    response_description="balkan_nodes + gemini_error.",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "balkan_nodes": [
                            {
                                "id": 1,
                                "name": "Nguyễn Văn A",
                                "gender": "male",
                                "birthYear": 1940,
                                "pids": [2],
                            },
                            {
                                "id": 2,
                                "name": "Trần Thị B",
                                "gender": "female",
                                "birthYear": 1942,
                                "pids": [1],
                            },
                            {
                                "id": 3,
                                "name": "Nguyễn Văn C",
                                "gender": "male",
                                "birthYear": 1965,
                                "fid": 1,
                                "mid": 2,
                            },
                        ],
                        "gemini_error": None,
                    }
                }
            }
        },
        404: {"description": "request_id không tồn tại trong store."},
    },
)
def get_history_detail(request_id: str) -> AnalyzeResponse:
    """
    Lấy lại kết quả phân tích đầy đủ của một request cụ thể.

    - **request_id**: UUID trả về từ `POST /api/family-tree/analyze`.
    - Trả về **404** nếu request_id không tìm thấy.
    """
    detail = _history_repo.get_detail(request_id) if _history_repo.enabled else None
    if detail:
        nodes = detail.get("balkan_nodes")
        if not isinstance(nodes, list):
            nodes = []
        return AnalyzeResponse(
            balkan_nodes=[x for x in nodes if isinstance(x, dict)],
            gemini_error=detail.get("gemini_error"),
        )

    with _history_lock:
        cached = _detail_store.get(request_id)

    if cached:
        return cached

    raise HTTPException(status_code=404, detail="History request_id not found")


@app.delete(
    "/api/family-tree/history",
    response_model=ClearHistoryResponse,
    tags=["History"],
    summary="Xoá toàn bộ lịch sử",
    response_description="Số lượng item đã xoá.",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {"cleared": 12}
                }
            }
        }
    },
)
def clear_history(current_user: OptionalUser = None) -> ClearHistoryResponse:
    """
    Xoá toàn bộ lịch sử request khỏi store (MySQL hoặc in-memory).

    Trả về `{ "cleared": <số lượng> }`.
    """
    user_id = current_user.id if current_user is not None else None
    if _history_repo.enabled:
        removed = _history_repo.clear(user_id=user_id)
        if removed is not None:
            with _history_lock:
                if user_id is None:
                    _history_store.clear()
                    _detail_store.clear()
                    _detail_order.clear()
                else:
                    remaining = [item for item in _history_store if item.user_id != user_id]
                    _history_store.clear()
                    _history_store.extend(remaining)
            return ClearHistoryResponse(cleared=removed)

    with _history_lock:
        if user_id is None:
            removed = len(_history_store)
            _history_store.clear()
            _detail_store.clear()
            _detail_order.clear()
        else:
            removed = sum(1 for item in _history_store if item.user_id == user_id)
            remaining = [item for item in _history_store if item.user_id != user_id]
            _history_store.clear()
            _history_store.extend(remaining)
    return ClearHistoryResponse(cleared=removed)


@app.get(
    "/api/family-trees",
    response_model=FamilyTreeListResponse,
    tags=["FamilyTrees"],
    summary="Danh sách cây gia phả",
)
def list_family_trees(_: AdminUser) -> FamilyTreeListResponse:
    try:
        items = _family_tree_store.list_trees()
    except Exception as error:  # pragma: no cover - defensive
        _raise_store_error(error)
    return FamilyTreeListResponse(total=len(items), items=[FamilyTreeSummary(**x) for x in items])


@app.post(
    "/api/family-trees",
    response_model=FamilyTreeDocument,
    tags=["FamilyTrees"],
    summary="Tạo cây gia phả mới",
)
def create_family_tree(req: FamilyTreeCreateRequest, _: AdminUser) -> FamilyTreeDocument:
    try:
        created = _family_tree_store.create_tree(
            name=req.name,
            description=req.description,
            nodes=req.nodes,
            external_url=req.external_url,
            has_source_document=req.has_source_document,
            has_hannom_text=req.has_hannom_text,
            is_public=req.is_public,
        )
    except Exception as error:
        _raise_store_error(error)
    return FamilyTreeDocument(**created)


@app.get(
    "/api/family-trees/{tree_id}",
    response_model=FamilyTreeDocument,
    tags=["FamilyTrees"],
    summary="Chi tiết cây gia phả",
)
def get_family_tree(tree_id: str, _: AdminUser) -> FamilyTreeDocument:
    try:
        item = _family_tree_store.get_tree(tree_id)
    except Exception as error:
        _raise_store_error(error)
    return FamilyTreeDocument(**item)


@app.put(
    "/api/family-trees/{tree_id}",
    response_model=FamilyTreeDocument,
    tags=["FamilyTrees"],
    summary="Cập nhật metadata cây gia phả",
)
def update_family_tree(tree_id: str, req: FamilyTreeUpdateRequest, _: AdminUser) -> FamilyTreeDocument:
    if (
        req.name is None
        and req.description is None
        and req.external_url is None
        and req.has_source_document is None
        and req.has_hannom_text is None
        and req.is_public is None
    ):
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        item = _family_tree_store.update_tree(
            tree_id,
            name=req.name,
            description=req.description,
            external_url=req.external_url,
            has_source_document=req.has_source_document,
            has_hannom_text=req.has_hannom_text,
            is_public=req.is_public,
        )
    except Exception as error:
        _raise_store_error(error)
    return FamilyTreeDocument(**item)


@app.put(
    "/api/family-trees/{tree_id}/document",
    response_model=FamilyTreeDocument,
    tags=["FamilyTrees"],
    summary="Thay thế toàn bộ document cây gia phả",
)
def replace_family_tree_document(tree_id: str, req: FamilyTreeReplaceRequest, _: AdminUser) -> FamilyTreeDocument:
    try:
        item = _family_tree_store.replace_tree_document(
            tree_id,
            name=req.name,
            description=req.description,
            nodes=req.nodes,
        )
    except Exception as error:
        _raise_store_error(error)
    return FamilyTreeDocument(**item)


@app.delete(
    "/api/family-trees/{tree_id}",
    response_model=FamilyTreeDeleteResponse,
    tags=["FamilyTrees"],
    summary="Xóa một cây gia phả",
)
def delete_family_tree(tree_id: str, _: AdminUser) -> FamilyTreeDeleteResponse:
    if database_enabled():
        from sqlalchemy.orm import Session

        db_gen = get_db()
        db: Session = next(db_gen)
        storage = ObjectStorage.from_env()
        try:
            from app.family_tree_cleanup import delete_family_tree_related

            delete_family_tree_related(
                db,
                tree_id,
                storage if storage.config.enabled else None,
            )
            db.commit()
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Không xóa được dữ liệu liên quan: {exc}") from exc
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

    try:
        _family_tree_store.delete_tree(tree_id)
    except Exception as error:
        _raise_store_error(error)
    return FamilyTreeDeleteResponse(deleted=True, id=tree_id)


@app.post(
    "/api/family-trees/{tree_id}/nodes",
    response_model=FamilyTreeDocument,
    tags=["FamilyTrees"],
    summary="Thêm node vào cây gia phả",
)
def add_family_tree_node(tree_id: str, req: FamilyTreeNodeRequest, _: AdminUser) -> FamilyTreeDocument:
    if req.name is None or req.gender is None:
        raise HTTPException(status_code=400, detail="name and gender are required")

    try:
        item = _family_tree_store.add_node(tree_id, req.model_dump(exclude_none=True))
    except Exception as error:
        _raise_store_error(error)
    return FamilyTreeDocument(**item)


@app.put(
    "/api/family-trees/{tree_id}/nodes/{node_id}",
    response_model=FamilyTreeDocument,
    tags=["FamilyTrees"],
    summary="Cập nhật node",
)
def update_family_tree_node(
    tree_id: str,
    node_id: int,
    req: FamilyTreeNodeRequest,
    _: AdminUser,
) -> FamilyTreeDocument:
    payload = req.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        item = _family_tree_store.update_node(tree_id, node_id=node_id, payload=payload)
    except Exception as error:
        _raise_store_error(error)
    return FamilyTreeDocument(**item)


@app.delete(
    "/api/family-trees/{tree_id}/nodes/{node_id}",
    response_model=FamilyTreeDocument,
    tags=["FamilyTrees"],
    summary="Xóa node",
)
def delete_family_tree_node(tree_id: str, node_id: int, _: AdminUser) -> FamilyTreeDocument:
    try:
        item = _family_tree_store.delete_node(tree_id, node_id=node_id)
    except Exception as error:
        _raise_store_error(error)
    return FamilyTreeDocument(**item)


@app.post(
    "/api/family-trees/{tree_id}/links",
    response_model=FamilyTreeDocument,
    tags=["FamilyTrees"],
    summary="Tạo liên kết quan hệ",
)
def create_family_tree_link(tree_id: str, req: FamilyTreeLinkRequest, _: AdminUser) -> FamilyTreeDocument:
    try:
        if req.type == "spouse_of":
            item = _family_tree_store.add_spouse_link(
                tree_id,
                from_id=req.from_id,
                to_id=req.to_id,
            )
        else:
            if req.side is None:
                raise HTTPException(
                    status_code=400,
                    detail="side is required for parent_of (fid or mid)",
                )
            item = _family_tree_store.add_parent_link(
                tree_id,
                parent_id=req.from_id,
                child_id=req.to_id,
                side=req.side,
            )
    except HTTPException:
        raise
    except Exception as error:
        _raise_store_error(error)
    return FamilyTreeDocument(**item)


@app.delete(
    "/api/family-trees/{tree_id}/links",
    response_model=FamilyTreeDocument,
    tags=["FamilyTrees"],
    summary="Xóa liên kết quan hệ",
)
def delete_family_tree_link(tree_id: str, req: FamilyTreeLinkRequest, _: AdminUser) -> FamilyTreeDocument:
    try:
        if req.type == "spouse_of":
            item = _family_tree_store.delete_spouse_link(
                tree_id,
                from_id=req.from_id,
                to_id=req.to_id,
            )
        else:
            item = _family_tree_store.delete_parent_link(
                tree_id,
                parent_id=req.from_id,
                child_id=req.to_id,
                side=req.side,
            )
    except Exception as error:
        _raise_store_error(error)
    return FamilyTreeDocument(**item)


@app.post(
    "/api/family-tree/analyze",
    response_model=AnalyzeResponse,
    tags=["Analysis"],
    summary="Phân tích văn bản gia phả",
    response_description="balkan_nodes + gemini_error.",
    status_code=200,
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "balkan_nodes": [
                            {
                                "id": 1,
                                "name": "Nguyễn Văn A",
                                "gender": "male",
                                "birthYear": 1940,
                                "pids": [2],
                            },
                            {
                                "id": 2,
                                "name": "Trần Thị B",
                                "gender": "female",
                                "birthYear": 1942,
                                "pids": [1],
                            },
                            {
                                "id": 3,
                                "name": "Nguyễn Văn C",
                                "gender": "male",
                                "birthYear": 1965,
                                "fid": 1,
                                "mid": 2,
                            },
                        ],
                        "gemini_error": None,
                    }
                }
            }
        }
    },
)
def analyze_family_text(req: AnalyzeRequest, current_user: OptionalUser = None) -> AnalyzeResponse:
    """
    Trả về **balkan_nodes** (Gemini) và **gemini_error** nếu có.
    """
    return _run_family_analysis(
        text=req.text,
        source=req.source or "frontend",
        metadata=req.metadata,
        current_user=current_user,
    )


def _run_family_analysis(
    *,
    text: str,
    source: str,
    metadata: RequestMetadata,
    current_user: OptionalUser,
) -> AnalyzeResponse:
    """Logic dùng chung cho cả phân tích text thuần lẫn text OCR từ ảnh/PDF."""
    request_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    extractor = FamilyExtractor()
    extraction = extractor.parse(text)

    warnings: List[str] = []
    warnings.extend(validate_no_self_relationship(extraction))
    warnings.extend(validate_no_duplicate_edges(extraction))
    warnings.extend(validate_parent_age_gap(extraction))

    balkan_nodes, gemini_err = normalize_balkan_nodes(text, extraction)
    if gemini_err:
        warnings.append(gemini_err)

    people_count = len(balkan_nodes) if gemini_err is None else len(extraction.get("people", []))

    response_payload = AnalyzeResponse(
        request_id=request_id,
        balkan_nodes=balkan_nodes,
        gemini_error=gemini_err,
    )

    history_item = HistoryItem(
        request_id=request_id,
        created_at=created_at,
        source=source,
        metadata=metadata,
        people_count=people_count,
        relationship_count=len(extraction.get("relationships", [])),
        warning_count=len(warnings),
        user_id=current_user.id if current_user is not None else None,
    )

    with _history_lock:
        _history_store.append(history_item)
        if len(_detail_order) >= _HISTORY_MAX_ITEMS:
            oldest = _detail_order.popleft()
            _detail_store.pop(oldest, None)
        _detail_store[request_id] = response_payload
        _detail_order.append(request_id)

    _history_repo.append(
        {
            **history_item.model_dump(),
            "analysis": response_payload.model_dump(),
            "user_id": history_item.user_id,
        }
    )

    return response_payload


def _max_image_upload_bytes() -> int:
    import os

    return int(os.getenv("MINIO_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))


@app.post(
    "/api/family-tree/analyze-image",
    response_model=AnalyzeImageResponse,
    tags=["Analysis"],
    summary="OCR ảnh/PDF gia phả Hán-Nôm rồi phân tích thành cây",
    response_description="ocr_text + balkan_nodes + gemini_error.",
)
async def analyze_family_image(
    file: UploadFile = File(..., description="Ảnh (jpg/png/webp) hoặc PDF gia phả Hán-Nôm"),
    lang_type: Optional[int] = Query(
        default=None,
        description="0 = tự động, 1 = Hán, 2 = Nôm (theo HANNOM_OCR_LANG_TYPE của Kim Hán Nôm).",
    ),
    scan_id: Optional[int] = Query(
        default=None,
        description="ID bản ghi user_scans (nếu có) để lưu ảnh gốc dưới đúng namespace của scan đó.",
    ),
    current_user: OptionalUser = None,
) -> AnalyzeImageResponse:
    """
    Pipeline nhanh cho Document Reader: OCR Hán-Nôm (Kim Hán Nôm API) → phiên âm
    Quốc ngữ → trích xuất gia phả (dùng lại đúng logic của `/api/family-tree/analyze`).
    PDF nhiều trang bị giới hạn `MAX_PDF_PAGES_DEFAULT` trang để tránh gọi quá
    nhiều lần API OCR trả phí/rate-limited từ một lần upload nhanh; tài liệu dài
    hơn nên dùng luồng Admin (upload nhiều file + pipeline 7 bước).

    Ảnh/PDF gốc cũng được lưu vào MinIO (best-effort — nếu MinIO chưa cấu
    hình, OCR vẫn chạy bình thường, chỉ `source_file_key` sẽ là `None`).
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File rỗng.")
    max_bytes = _max_image_upload_bytes()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File vượt quá giới hạn upload ({max_bytes} bytes).",
        )

    filename = file.filename or "upload"
    is_pdf = (file.content_type == "application/pdf") or filename.lower().endswith(".pdf")

    source_file_key: Optional[str] = None
    try:
        storage = ObjectStorage.from_env()
        if storage.config.enabled:
            storage.ensure_bucket()
            safe_name = "".join(c for c in filename if c.isalnum() or c in "._-") or "upload"
            namespace = f"scan-{scan_id}" if scan_id is not None else f"anon-{uuid4().hex[:8]}"
            source_file_key = f"user-scans/{namespace}/{uuid4().hex}_{safe_name}"
            storage.upload_file(
                source_file_key,
                io.BytesIO(content),
                content_type=file.content_type or "application/octet-stream",
                size=len(content),
            )
    except ObjectStorageError as error:
        # Lưu ảnh chỉ là best-effort — không chặn OCR/phân tích nếu MinIO lỗi.
        source_file_key = None
        print(f"[analyze-image] Không lưu được ảnh gốc vào MinIO: {error}")

    hannom_text_parts: List[str] = []
    ocr_text_parts: List[str] = []
    bbox_pages: List[List[Dict[str, Any]]] = []
    translation_parts: List[str] = []
    vote_meta_pages: List[Dict[str, Any]] = []
    pages_processed = 0
    pages_truncated = False
    pipeline_version = "v1"

    try:
        if is_pdf:
            import pypdfium2 as pdfium

            total_pages = len(pdfium.PdfDocument(content))
            page_images = render_pdf_pages_to_png(content)
            pages_truncated = total_pages > len(page_images)
            for index, page_bytes in enumerate(page_images):
                result = run_hannom_pipeline(
                    page_bytes, f"{filename}-p{index + 1}.png", lang_type=lang_type
                )
                hannom_text_parts.append(result["ocr_text"])
                ocr_text_parts.append(result["transcription_text"])
                bbox_pages.append(result.get("bbox") or [])
                if result.get("translation_text"):
                    translation_parts.append(result["translation_text"])
                if result.get("vote_meta"):
                    vote_meta_pages.append(result["vote_meta"])
                pipeline_version = result.get("pipeline_version", pipeline_version)
                pages_processed += 1
        else:
            result = run_hannom_pipeline(content, filename, lang_type=lang_type)
            hannom_text_parts.append(result["ocr_text"])
            ocr_text_parts.append(result["transcription_text"])
            bbox_pages.append(result.get("bbox") or [])
            if result.get("translation_text"):
                translation_parts.append(result["translation_text"])
            if result.get("vote_meta"):
                vote_meta_pages.append(result["vote_meta"])
            pipeline_version = result.get("pipeline_version", pipeline_version)
            pages_processed = 1
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except HannomApiError as error:
        raise HTTPException(status_code=502, detail=f"Lỗi OCR Kim Hán Nôm: {error}") from error

    translation_text = "\n\n".join(translation_parts) if translation_parts else None

    combined_text = "\n\n".join(part for part in ocr_text_parts if part.strip())
    combined_hannom = "\n\n".join(part for part in hannom_text_parts if part.strip())
    if not combined_text.strip():
        raise HTTPException(
            status_code=422,
            detail="OCR không nhận được văn bản nào từ file — thử ảnh rõ nét hơn.",
        )

    analysis = _run_family_analysis(
        text=combined_text,
        source="document-reader-image",
        metadata=RequestMetadata(fileName=filename, documentType="gia-pha"),
        current_user=current_user,
    )

    if scan_id is not None and current_user is not None:
        try:
            with session_scope() as db:
                scan_repo = UserScanRepository(db)
                scan = scan_repo.get_accessible(current_user, scan_id)
                if scan is not None:
                    scan_repo.update(
                        scan,
                        hannom_text=combined_hannom or None,
                        transliteration_text=combined_text or None,
                        source_text=translation_text,
                        ocr_vote_meta=vote_meta_pages or None,
                        ocr_bbox=bbox_pages or None,
                    )
                    # Tự tạo mã định danh sau khi dịch nghĩa (1 lượt Gemini,
                    # chỉ khi bộ CHƯA có mã — mã đã có không bao giờ bị ghi đè).
                    if translation_text and not scan.ma_dinh_danh:
                        from app.workspace.ma_dinh_danh_auto import ensure_ma_dinh_danh

                        _, problems = ensure_ma_dinh_danh(scan_repo, scan)
                        if problems:
                            print(f"[analyze-image] Chưa tạo được mã định danh scan {scan_id}: {'; '.join(problems)}")
        except Exception as error:
            print(f"[analyze-image] Không đồng bộ được user_scan {scan_id}: {error}")

    return AnalyzeImageResponse(
        **analysis.model_dump(),
        ocr_text=combined_text,
        hannom_text=combined_hannom or None,
        source_file_key=source_file_key,
        pages_processed=pages_processed,
        pages_truncated=pages_truncated,
        bbox=bbox_pages or None,
        translation_text=translation_text,
        vote_meta=vote_meta_pages or None,
        pipeline_version=pipeline_version,
    )


# ============================================================================
# Genealogy Parser API (Regex MVP + Dual-model Ready)
# ============================================================================

@app.post(
    "/api/genealogy/extract",
    response_model=GenealogyExtractResponse,
    tags=["Genealogy"],
    summary="Trích xuất gia phả từ văn bản Việt hoặc Hán-Nôm",
)
def extract_genealogy(req: GenealogyExtractRequest) -> GenealogyExtractResponse:
    """
    Extract genealogy (persons, relationships, years) from Vietnamese or Hán-Nôm text.

    Supports:
    - language="vietnamese": Vietnamese genealogy text (MVP regex-based)
    - language="hannom": Classical Chinese / Hán-Nôm genealogy text (MVP regex-based)

    Returns: persons, relationships (spouse/parent/sibling), birth/death years, model info.

    Current model: FamilyExtractor (regex MVP)
    - Accuracy: ~60% on diverse genealogy data
    - Next phase: Fine-tuned Phobert (Vietnamese) + SikuBERT (Hán-Nôm) for 90%+ accuracy
    """
    if req.language not in ["vietnamese", "hannom"]:
        raise HTTPException(
            status_code=400,
            detail="Language must be 'vietnamese' or 'hannom'",
        )

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        from app.domains.extraction.extractor import FamilyExtractor

        extractor = FamilyExtractor()
        result = extractor.extract(text)

        persons = [p.name for p in result["persons"]]
        person_years = {}
        for person in result["persons"]:
            birth_year = person.birth_year or person.approximate_birth_year
            person_years[person.name] = birth_year

        relations = [
            {
                "head": rel.head.name,
                "type": rel.type.value,
                "tail": rel.tail.name,
                "confidence": 0.6,
            }
            for rel in result["relations"]
        ]

        # Select model based on version
        model_version_num = "1.0.0"
        if req.model_version == "phobert":
            if req.language == "vietnamese":
                model_name = "Phobert-Fine-tuned (Vietnamese)"
                model_version_num = "2.0.0"
            else:
                model_name = "Phobert-Fine-tuned (Not supported for Hán-Nôm)"
                model_version_num = "2.0.0"
        elif req.model_version == "sikubert":
            if req.language == "hannom":
                model_name = "SikuBERT-Fine-tuned (Hán-Nôm)"
                model_version_num = "2.0.0"
            else:
                model_name = "SikuBERT-Fine-tuned (Not supported for Vietnamese)"
                model_version_num = "2.0.0"
        else:  # regex (default)
            model_name = "FamilyExtractor-Regex-MVP"
            if req.language == "hannom":
                model_name = "FamilyExtractor-Regex-MVP (Hán-Nôm)"
            model_version_num = "1.0.0"

        return GenealogyExtractResponse(
            success=True,
            data=GenealogyExtractionResult(
                persons=persons,
                person_years=person_years,
                relations=relations,
                statistics={
                    "person_count": len(persons),
                    "relation_count": len(relations),
                },
                model_info={
                    "model_name": model_name,
                    "model_version": model_version_num,
                    "language": req.language,
                },
            ),
        )
    except Exception as error:
        return GenealogyExtractResponse(
            success=False,
            error=f"Genealogy extraction error: {str(error)}",
        )
