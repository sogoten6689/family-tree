from __future__ import annotations

import json
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from app.auth.bootstrap import bootstrap_auth
from app.auth.dependencies import AdminUser, CurrentUser, OptionalUser
from app.auth.router import router as auth_router
from app.database import database_enabled, database_init_error, get_db, init_database
from app.documents.bootstrap import bootstrap_documents
from app.documents.router import create_documents_router
from app.documents.storage import ObjectStorage
from app.hannom.router import router as hannom_developer_router
from app.pipeline.bootstrap import bootstrap_pipeline
from app.pipeline.router import create_pipeline_router
from app.vgp.bootstrap import bootstrap_vgp
from app.vgp.crawl_service import VgpCrawlOptions, VgpCrawlService
from app.workspace.bootstrap import bootstrap_workspace
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
from tools.fetch_vietnamgiapha import run as crawl_vietnamgiapha_run
from app.nomfoundation.import_service import default_nom_tree_id, import_nom_volume
from app.nomfoundation.jobs import get_job, start_nom_import_job
from tools.sync_vietnamgiapha_documents import attach_documents_batch
from tools.sync_vietnamgiapha_to_db import _default_db_config, sync as sync_vietnamgiapha_to_db


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


class VietnamGiaPhaCrawlSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_id: int = Field(default=100, ge=1, le=100000)
    end_id: int = Field(default=200, ge=1, le=100000)
    delay_seconds: float = Field(default=0.2, ge=0.0, le=5.0)
    crawl_version: Literal["v1", "v2"] = Field(default="v2")
    modules: List[Literal["giapha", "pha_ky", "pha_he", "images"]] = Field(
        default_factory=lambda: ["giapha", "pha_ky", "pha_he", "images"]
    )
    sync_db: bool = Field(default=True)
    skip_unchanged: bool = Field(default=True)
    sync_pipeline: bool = Field(default=True)
    export_text: bool = Field(default=False, description="V1 only — ghi text/ local")
    attach_documents: bool = Field(default=True)


class VietnamGiaPhaCrawlSyncResponse(BaseModel):
    crawl_version: str
    start_id: int
    end_id: int
    output_dir: Optional[str] = None
    crawl_success: int
    crawl_skipped: int
    crawl_skipped_unchanged: int
    crawl_errors: int
    text_built: int
    sync_upserted: int
    sync_skipped: int
    sync_errors: int
    text_attached: int
    text_attach_skipped: int
    text_attach_errors: int
    error_details: List[Dict[str, Any]] = Field(default_factory=list)


class NomFoundationCrawlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collection_id: int = Field(default=2, ge=1)
    volume_id: int = Field(ge=1)
    delay_seconds: float = Field(default=0.3, ge=0.0, le=5.0)
    max_pages: int = Field(default=100, ge=1, le=200)
    image_variant: Literal["large", "jpeg"] = Field(default="large")
    page_start: int = Field(default=1, ge=1, description="Trang bắt đầu (inclusive)")
    page_end: Optional[int] = Field(default=None, ge=1, description="Trang kết thúc (inclusive)")
    save_to_system: bool = Field(
        default=True,
        description="Lưu ảnh MinIO + tạo cây gia phả (nom-{volume_id})",
    )
    crawl_only: bool = Field(default=False, description="Chỉ tải ảnh local, không MinIO/tree")
    attach_only: bool = Field(default=False, description="Chỉ upload ảnh local đã có lên MinIO")
    background: bool = Field(default=False, description="Chạy job nền, tránh timeout HTTP")
    run_ocr: bool = Field(default=True, description="OCR batch từ MinIO sau khi attach (chậm, cần token)")
    run_analyze: bool = Field(default=False, description="Phân tích text OCR ghép → balkan_nodes (cần Gemini)")
    tree_id: Optional[str] = Field(
        default=None,
        description="ID cây tùy chỉnh; mặc định nom-{volume_id}",
    )
    tree_name: Optional[str] = Field(default=None, description="Tên cây; mặc định lấy từ metadata Nom")
    sync_pipeline: bool = Field(default=True)
    force_documents: bool = Field(default=False)
    link_tree_id: Optional[str] = Field(
        default=None,
        description="Deprecated alias của tree_id",
    )


class NomFoundationCrawlResponse(BaseModel):
    collection_id: int
    volume_id: int
    output_dir: str
    downloaded_pages: int
    page_count: int
    errors: int
    catalog_slug: Optional[str] = None
    title: Optional[str] = None
    tree_id: Optional[str] = None
    tree_name: Optional[str] = None
    images_document_id: Optional[int] = None
    images_attached: int = 0
    pipeline_synced: bool = False
    job_id: Optional[str] = None
    job_status: Optional[str] = None
    ocr_processed: int = 0
    ocr_errors: int = 0
    merged_pages: int = 0
    analyze_node_count: int = 0
    analyze_error: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None


class NomFoundationJobResponse(BaseModel):
    job_id: str
    status: str
    type: str
    params: Dict[str, Any] = Field(default_factory=dict)
    progress: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


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
        "name": "Crawlers",
        "description": "Tiện ích crawl dữ liệu nguồn ngoài và đồng bộ vào database.",
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


@asynccontextmanager
async def _lifespan(_: FastAPI):
    init_database()
    if database_enabled():
        bootstrap_auth()
        bootstrap_documents()
        bootstrap_pipeline()
        bootstrap_vgp()
        bootstrap_workspace()
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
    "/api/vietnamgiapha/crawl-sync",
    response_model=VietnamGiaPhaCrawlSyncResponse,
    tags=["Crawlers"],
    summary="Crawl vietnamgiapha và đồng bộ DB",
)
def crawl_and_sync_vietnamgiapha(
    req: VietnamGiaPhaCrawlSyncRequest,
    _: AdminUser,
) -> VietnamGiaPhaCrawlSyncResponse:
    if req.start_id > req.end_id:
        raise HTTPException(status_code=400, detail="start_id must be <= end_id")

    if req.crawl_version == "v2":
        return _crawl_and_sync_vietnamgiapha_v2(req)

    return _crawl_and_sync_vietnamgiapha_v1(req)


def _crawl_and_sync_vietnamgiapha_v2(req: VietnamGiaPhaCrawlSyncRequest) -> VietnamGiaPhaCrawlSyncResponse:
    if not database_enabled():
        raise HTTPException(status_code=503, detail="V2 crawl requires MySQL — thiết lập MYSQL_*.")

    storage: Optional[ObjectStorage] = None
    if req.attach_documents:
        storage = ObjectStorage.from_env()
        if not storage.config.enabled:
            raise HTTPException(
                status_code=503,
                detail="attach_documents requires MinIO — thiết lập MINIO_*.",
            )

    from sqlalchemy.orm import Session

    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        service = VgpCrawlService(
            db=db,
            storage=storage,
            get_tree=_get_family_tree_document,
        )
        summary = service.crawl_range(
            start_id=req.start_id,
            end_id=req.end_id,
            options=VgpCrawlOptions(
                modules=set(req.modules),
                skip_unchanged=req.skip_unchanged,
                sync_pipeline=req.sync_pipeline,
                attach_documents=req.attach_documents,
                delay_seconds=req.delay_seconds,
            ),
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"V2 crawl failed: {exc}") from exc
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    documents_attached = 0
    documents_skipped = 0
    document_errors = len(summary.get("document_errors", []))
    for item in summary.get("upserted", []):
        docs = item.get("documents") or {}
        for doc_result in docs.values():
            if doc_result.get("attached"):
                documents_attached += 1
            else:
                documents_skipped += 1

    return VietnamGiaPhaCrawlSyncResponse(
        crawl_version="v2",
        start_id=req.start_id,
        end_id=req.end_id,
        output_dir=None,
        crawl_success=len(summary.get("upserted", [])),
        crawl_skipped=len(summary.get("skipped_empty", [])),
        crawl_skipped_unchanged=len(summary.get("skipped_unchanged", [])),
        crawl_errors=len(summary.get("errors", [])),
        text_built=0,
        sync_upserted=len(summary.get("upserted", [])),
        sync_skipped=len(summary.get("skipped_unchanged", [])) + len(summary.get("skipped_empty", [])),
        sync_errors=len(summary.get("errors", [])),
        text_attached=documents_attached,
        text_attach_skipped=documents_skipped,
        text_attach_errors=document_errors,
        error_details=summary.get("errors", []),
    )


def _crawl_and_sync_vietnamgiapha_v1(req: VietnamGiaPhaCrawlSyncRequest) -> VietnamGiaPhaCrawlSyncResponse:
    output_dir = Path(__file__).resolve().parent / "data" / "vietnamgiapha"

    try:
        crawl_summary = crawl_vietnamgiapha_run(
            start_id=req.start_id,
            end_id=req.end_id,
            output_dir=output_dir,
            save_html=False,
            fetch_detail=True,
            detail_delay_seconds=req.delay_seconds,
            delay_seconds=req.delay_seconds,
            timeout_seconds=20.0,
            skip_unchanged=req.skip_unchanged,
            export_text=req.export_text,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Crawl failed: {exc}") from exc

    sync_upserted = 0
    sync_skipped = 0
    sync_errors = 0
    sync_report: Dict[str, Any] = {}
    if req.sync_db:
        try:
            sync_report = sync_vietnamgiapha_to_db(
                input_dir=output_dir / "json",
                db_cfg=_default_db_config(),
                dry_run=False,
            )
            sync_upserted = len(sync_report.get("upserted", []))
            sync_skipped = len(sync_report.get("skipped", []))
            sync_errors = len(sync_report.get("errors", []))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"DB sync failed: {exc}") from exc

    text_attached = 0
    text_attach_skipped = 0
    text_attach_errors = 0
    if req.attach_documents:
        if not database_enabled():
            raise HTTPException(
                status_code=503,
                detail="attach_documents requires MySQL — thiết lập MYSQL_*.",
            )
        storage = ObjectStorage.from_env()
        if not storage.config.enabled:
            raise HTTPException(
                status_code=503,
                detail="attach_documents requires MinIO — thiết lập MINIO_*.",
            )

        tree_ids = list(range(req.start_id, req.end_id + 1))
        from sqlalchemy.orm import Session

        db_gen = get_db()
        db: Session = next(db_gen)
        try:
            attach_report = attach_documents_batch(
                db=db,
                storage=storage,
                get_tree=_get_family_tree_document,
                text_root=output_dir / "text",
                tree_ids=tree_ids,
            )
            db.commit()
            text_attached = len(attach_report.get("attached", []))
            text_attach_skipped = len(attach_report.get("skipped", []))
            text_attach_errors = len(attach_report.get("errors", []))
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Attach documents failed: {exc}") from exc
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

        if text_attached > 0:
            for item in sync_report.get("upserted", []):
                store_id = item.get("store_id")
                if not store_id:
                    continue
                try:
                    _family_tree_store.update_tree(
                        store_id,
                        has_source_document=True,
                    )
                except Exception:
                    pass
            for item in sync_report.get("skipped", []):
                store_id = item.get("store_id")
                if not store_id:
                    continue
                try:
                    _family_tree_store.update_tree(
                        store_id,
                        has_source_document=True,
                    )
                except Exception:
                    pass

    return VietnamGiaPhaCrawlSyncResponse(
        crawl_version="v1",
        start_id=req.start_id,
        end_id=req.end_id,
        output_dir=str(output_dir),
        crawl_success=len(crawl_summary.get("success", [])),
        crawl_skipped=len(crawl_summary.get("skipped", [])),
        crawl_skipped_unchanged=len(crawl_summary.get("skipped_unchanged", [])),
        crawl_errors=len(crawl_summary.get("errors", [])),
        text_built=len(crawl_summary.get("text_built", [])),
        sync_upserted=sync_upserted,
        sync_skipped=sync_skipped,
        sync_errors=sync_errors,
        text_attached=text_attached,
        text_attach_skipped=text_attach_skipped,
        text_attach_errors=text_attach_errors,
    )


@app.post(
    "/api/nomfoundation/crawl-volume",
    response_model=NomFoundationCrawlResponse,
    tags=["Crawlers"],
    summary="Crawl Nom Foundation volume",
)
def crawl_nomfoundation_volume(
    req: NomFoundationCrawlRequest,
    _: AdminUser,
) -> NomFoundationCrawlResponse:
    output_dir = Path(__file__).resolve().parent / "data" / "nomfoundation"
    resolved_tree_id = (req.tree_id or req.link_tree_id or default_nom_tree_id(req.volume_id)).strip()

    if req.attach_only and req.crawl_only:
        raise HTTPException(status_code=400, detail="attach_only và crawl_only không dùng cùng lúc.")

    try:
        if req.crawl_only or not req.save_to_system:
            from tools.fetch_nomfoundation import run as crawl_nomfoundation_run

            summary = crawl_nomfoundation_run(
                collection_id=req.collection_id,
                volume_id=req.volume_id,
                output_dir=output_dir,
                delay_seconds=req.delay_seconds,
                max_pages=req.max_pages,
                image_variant=req.image_variant,
                page_start=req.page_start,
                page_end=req.page_end,
            )
        elif req.save_to_system:
            if not database_enabled():
                raise HTTPException(
                    status_code=400,
                    detail="save_to_system requires MySQL — thiết lập MYSQL_*.",
                )
            storage = ObjectStorage.from_env()
            if not storage.config.enabled:
                raise HTTPException(
                    status_code=400,
                    detail="save_to_system requires MinIO — thiết lập MINIO_*.",
                )

            if req.background:
                job_params = req.model_dump()
                job_params["resolved_tree_id"] = resolved_tree_id

                def _runner(job_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
                    from app.nomfoundation.jobs import _update_job

                    db_gen = get_db()
                    db = next(db_gen)
                    try:
                        def _on_progress(patch: Dict[str, Any]) -> None:
                            _update_job(output_dir, job_id, progress=patch)

                        result = import_nom_volume(
                            collection_id=params["collection_id"],
                            volume_id=params["volume_id"],
                            output_dir=output_dir,
                            db=db,
                            storage=storage,
                            store=_family_tree_store,
                            get_tree=_get_family_tree_document,
                            delay_seconds=params.get("delay_seconds", 0.3),
                            max_pages=params.get("max_pages", 100),
                            image_variant=params.get("image_variant", "large"),
                            page_start=params.get("page_start", 1),
                            page_end=params.get("page_end"),
                            family_tree_id=params.get("resolved_tree_id"),
                            tree_name=params.get("tree_name"),
                            sync_pipeline=params.get("sync_pipeline", True),
                            force_documents=params.get("force_documents", False),
                            crawl_only=False,
                            attach_only=params.get("attach_only", False),
                            run_ocr=params.get("run_ocr", True),
                            run_analyze=params.get("run_analyze", False),
                            job_id=job_id,
                            on_progress=_on_progress,
                        )
                        _upsert_nom_research_source_link(
                            db,
                            family_tree_id=params["resolved_tree_id"],
                            collection_id=params["collection_id"],
                            volume_id=params["volume_id"],
                            page_count=int(result.get("page_count", 0)),
                        )
                        db.commit()
                        return result
                    finally:
                        try:
                            next(db_gen)
                        except StopIteration:
                            pass

                job = start_nom_import_job(output_dir=output_dir, params=job_params, runner=_runner)
                return NomFoundationCrawlResponse(
                    collection_id=req.collection_id,
                    volume_id=req.volume_id,
                    output_dir=str(output_dir),
                    downloaded_pages=0,
                    page_count=0,
                    errors=0,
                    tree_id=resolved_tree_id,
                    job_id=job["job_id"],
                    job_status=job["status"],
                    page_start=req.page_start,
                    page_end=req.page_end,
                )

            db_gen = get_db()
            db = next(db_gen)
            try:
                summary = import_nom_volume(
                    collection_id=req.collection_id,
                    volume_id=req.volume_id,
                    output_dir=output_dir,
                    db=db,
                    storage=storage,
                    store=_family_tree_store,
                    get_tree=_get_family_tree_document,
                    delay_seconds=req.delay_seconds,
                    max_pages=req.max_pages,
                    image_variant=req.image_variant,
                    page_start=req.page_start,
                    page_end=req.page_end,
                    family_tree_id=resolved_tree_id,
                    tree_name=req.tree_name,
                    sync_pipeline=req.sync_pipeline,
                    force_documents=req.force_documents,
                    crawl_only=False,
                    attach_only=req.attach_only,
                    run_ocr=req.run_ocr,
                    run_analyze=req.run_analyze,
                )
                if not req.attach_only:
                    _upsert_nom_research_source_link(
                        db,
                        family_tree_id=resolved_tree_id,
                        collection_id=req.collection_id,
                        volume_id=req.volume_id,
                        page_count=int(summary.get("page_count", 0)),
                    )
                db.commit()
            finally:
                try:
                    next(db_gen)
                except StopIteration:
                    pass
        else:
            raise HTTPException(status_code=400, detail="save_to_system=false requires crawl_only or local crawl.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Nom crawl failed: {exc}") from exc

    images_doc = summary.get("images_document") or {}
    ocr_result = summary.get("ocr_result") or {}
    analyze_result = summary.get("analyze_result") or {}
    return NomFoundationCrawlResponse(
        collection_id=req.collection_id,
        volume_id=req.volume_id,
        output_dir=str(output_dir),
        downloaded_pages=len(summary.get("downloaded_pages", [])),
        page_count=int(summary.get("page_count", 0)),
        errors=len(summary.get("errors", [])),
        catalog_slug=summary.get("catalog_slug"),
        title=summary.get("title") or summary.get("tree_name"),
        tree_id=summary.get("tree_id"),
        tree_name=summary.get("tree_name"),
        images_document_id=images_doc.get("document_id"),
        images_attached=int(images_doc.get("uploaded_count") or images_doc.get("file_count") or 0),
        pipeline_synced=bool(summary.get("pipeline_synced")),
        ocr_processed=int(ocr_result.get("processed") or 0),
        ocr_errors=len(ocr_result.get("errors") or []),
        merged_pages=int(ocr_result.get("merged_page_count") or 0),
        analyze_node_count=int(analyze_result.get("node_count") or 0),
        analyze_error=analyze_result.get("gemini_error"),
        page_start=summary.get("page_start", req.page_start),
        page_end=summary.get("page_end", req.page_end),
    )


@app.get(
    "/api/nomfoundation/jobs/{job_id}",
    response_model=NomFoundationJobResponse,
    tags=["Crawlers"],
    summary="Trạng thái job crawl/import Nom Foundation",
)
def get_nomfoundation_job(job_id: str, _: AdminUser) -> NomFoundationJobResponse:
    output_dir = Path(__file__).resolve().parent / "data" / "nomfoundation"
    job = get_job(output_dir, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return NomFoundationJobResponse(**job)


def _upsert_nom_research_source_link(
    db,
    *,
    family_tree_id: str,
    collection_id: int,
    volume_id: int,
    page_count: int,
) -> None:
    from sqlalchemy import text as sql_text

    volume_url = f"https://lib.nomfoundation.org/collection/{collection_id}/volume/{volume_id}/"
    db.execute(
        sql_text(
            """
            INSERT INTO research_source_links
                (family_tree_id, source_type, external_id, external_url, metadata_json, created_at)
            VALUES
                (:family_tree_id, 'nomfoundation', :external_id, :external_url, :metadata_json, UTC_TIMESTAMP())
            ON DUPLICATE KEY UPDATE
                external_url = VALUES(external_url),
                metadata_json = VALUES(metadata_json)
            """
        ),
        {
            "family_tree_id": family_tree_id,
            "external_id": str(volume_id),
            "external_url": volume_url,
            "metadata_json": json.dumps(
                {
                    "collection_id": collection_id,
                    "volume_id": volume_id,
                    "page_count": page_count,
                },
                ensure_ascii=False,
            ),
        },
    )


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
    request_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    extractor = FamilyExtractor()
    extraction = extractor.parse(req.text)

    warnings: List[str] = []
    warnings.extend(validate_no_self_relationship(extraction))
    warnings.extend(validate_no_duplicate_edges(extraction))
    warnings.extend(validate_parent_age_gap(extraction))

    balkan_nodes, gemini_err = normalize_balkan_nodes(req.text, extraction)
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
        source=req.source or "frontend",
        metadata=req.metadata,
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
