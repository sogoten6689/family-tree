from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from app.extractor import FamilyExtractor
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
from app.validate import (
    validate_no_duplicate_edges,
    validate_no_self_relationship,
    validate_parent_age_gap,
)
from tools.fetch_vietnamgiapha import run as crawl_vietnamgiapha_run
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


class HistoryResponse(BaseModel):
    total: int = Field(description="Tổng số request đang lưu trong store.")
    items: List[HistoryItem] = Field(description="Danh sách request gần nhất (mới nhất trước).")


class HealthResponse(BaseModel):
    status: str = Field(description="Trạng thái sống của service, hiện tại là `ok`.")
    history_storage: Literal["mysql", "memory"] = Field(
        description="Backend đang lưu lịch sử bằng MySQL hay in-memory."
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


class FamilyTreeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, description="Tên cây gia phả.")
    description: Optional[str] = Field(default=None, description="Mô tả ngắn.")
    nodes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Danh sách node BALKAN khởi tạo ban đầu.",
    )


class FamilyTreeUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = Field(default=None)


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
    sync_db: bool = Field(default=True)


class VietnamGiaPhaCrawlSyncResponse(BaseModel):
    start_id: int
    end_id: int
    output_dir: str
    crawl_success: int
    crawl_errors: int
    sync_upserted: int
    sync_errors: int


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
]

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
)

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
        "history_storage": "mysql" if _history_repo.enabled else "memory",
    }
    payload["tree_storage"] = _family_tree_storage
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
    limit: int = Query(default=20, ge=1, le=100, description="Số lượng item trả về (1–100).")
) -> HistoryResponse:
    """
    Trả về danh sách các request phân tích gần nhất.

    - **limit**: số item muốn lấy, tối thiểu 1, tối đa 100 (mặc định 20).
    - Ưu tiên đọc từ MySQL nếu đã cấu hình; fallback sang in-memory store.
    """
    safe_limit = max(1, min(limit, 100))

    # Prefer durable MySQL history when available
    if _history_repo.enabled:
        total, db_items = _history_repo.list_recent(safe_limit)
        if total > 0 or db_items:
            return HistoryResponse(total=total, items=[HistoryItem(**item) for item in db_items])

    with _history_lock:
        snapshot = list(_history_store)

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
def clear_history() -> ClearHistoryResponse:
    """
    Xoá toàn bộ lịch sử request khỏi store (MySQL hoặc in-memory).

    Trả về `{ "cleared": <số lượng> }`.
    """
    if _history_repo.enabled:
        removed = _history_repo.clear()
        if removed is not None:
            with _history_lock:
                _history_store.clear()
                _detail_store.clear()
                _detail_order.clear()
            return ClearHistoryResponse(cleared=removed)

    with _history_lock:
        removed = len(_history_store)
        _history_store.clear()
        _detail_store.clear()
        _detail_order.clear()
    return ClearHistoryResponse(cleared=removed)


@app.get(
    "/api/family-trees",
    response_model=FamilyTreeListResponse,
    tags=["FamilyTrees"],
    summary="Danh sách cây gia phả",
)
def list_family_trees() -> FamilyTreeListResponse:
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
def create_family_tree(req: FamilyTreeCreateRequest) -> FamilyTreeDocument:
    try:
        created = _family_tree_store.create_tree(
            name=req.name,
            description=req.description,
            nodes=req.nodes,
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
def get_family_tree(tree_id: str) -> FamilyTreeDocument:
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
def update_family_tree(tree_id: str, req: FamilyTreeUpdateRequest) -> FamilyTreeDocument:
    if req.name is None and req.description is None:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        item = _family_tree_store.update_tree(
            tree_id,
            name=req.name,
            description=req.description,
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
def replace_family_tree_document(tree_id: str, req: FamilyTreeReplaceRequest) -> FamilyTreeDocument:
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
def delete_family_tree(tree_id: str) -> FamilyTreeDeleteResponse:
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
def add_family_tree_node(tree_id: str, req: FamilyTreeNodeRequest) -> FamilyTreeDocument:
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
def delete_family_tree_node(tree_id: str, node_id: int) -> FamilyTreeDocument:
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
def create_family_tree_link(tree_id: str, req: FamilyTreeLinkRequest) -> FamilyTreeDocument:
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
def delete_family_tree_link(tree_id: str, req: FamilyTreeLinkRequest) -> FamilyTreeDocument:
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
) -> VietnamGiaPhaCrawlSyncResponse:
    if req.start_id > req.end_id:
        raise HTTPException(status_code=400, detail="start_id must be <= end_id")

    output_dir = Path(__file__).resolve().parent / "data" / "vietnamgiapha"

    try:
        crawl_summary = crawl_vietnamgiapha_run(
            start_id=req.start_id,
            end_id=req.end_id,
            output_dir=output_dir,
            save_html=False,
            delay_seconds=req.delay_seconds,
            timeout_seconds=20.0,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Crawl failed: {exc}") from exc

    sync_upserted = 0
    sync_errors = 0
    if req.sync_db:
        try:
            sync_report = sync_vietnamgiapha_to_db(
                input_dir=output_dir / "json",
                db_cfg=_default_db_config(),
                dry_run=False,
            )
            sync_upserted = len(sync_report.get("upserted", []))
            sync_errors = len(sync_report.get("errors", []))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"DB sync failed: {exc}") from exc

    return VietnamGiaPhaCrawlSyncResponse(
        start_id=req.start_id,
        end_id=req.end_id,
        output_dir=str(output_dir),
        crawl_success=len(crawl_summary.get("success", [])),
        crawl_errors=len(crawl_summary.get("errors", [])),
        sync_upserted=sync_upserted,
        sync_errors=sync_errors,
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
def analyze_family_text(req: AnalyzeRequest) -> AnalyzeResponse:
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
        }
    )

    return response_payload
