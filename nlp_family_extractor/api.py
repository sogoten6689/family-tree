from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from app.extractor import FamilyExtractor
from app.gemini_service import normalize_balkan_nodes
from app.history_repository import HistoryRepository
from app.validate import (
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


class ClearHistoryResponse(BaseModel):
    cleared: int = Field(description="Số lượng bản ghi lịch sử đã bị xoá.")


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
