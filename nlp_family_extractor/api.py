from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.extractor import FamilyExtractor
from app.history_repository import HistoryRepository
from app.tree_builder import build_nested_tree, build_tree_architecture
from app.validate import (
    validate_no_duplicate_edges,
    validate_no_self_relationship,
    validate_parent_age_gap,
)


class AnalyzeRequest(BaseModel):
    model_config = {
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
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata tuỳ ý đính kèm request (tên file, ngôn ngữ, …).",
    )


class AnalyzeResponse(BaseModel):
    request_id: str = Field(description="UUID duy nhất cho mỗi request.")
    created_at: str = Field(description="Thời điểm xử lý (UTC ISO-8601).")
    source: str = Field(description="Caller source được echo lại.")
    metadata: Dict[str, Any] = Field(description="Metadata được echo lại từ request.")
    people_count: int = Field(description="Số lượng người được trích xuất.")
    relationship_count: int = Field(description="Số lượng quan hệ được trích xuất.")
    warnings: List[str] = Field(
        description=(
            "Danh sách cảnh báo validation: tự quan hệ với bản thân, "
            "cạnh trùng lặp, hoặc khoảng cách tuổi cha-con bất thường."
        )
    )
    extraction: Dict[str, Any] = Field(
        description=(
            "Kết quả trích xuất thô gồm hai key: "
            "`people` (danh sách người) và `relationships` (danh sách quan hệ)."
        )
    )
    tree_architecture: Dict[str, Any] = Field(
        description=(
            "Cấu trúc cây phẳng gồm: `roots` (danh sách node gốc), "
            "`children_map` (ánh xạ id → danh sách id con), "
            "`nodes` (ánh xạ id → thông tin node)."
        )
    )
    tree: List[Dict[str, Any]] = Field(
        description="Cây lồng nhau sẵn sàng để frontend render trực tiếp."
    )


class HistoryItem(BaseModel):
    request_id: str = Field(description="UUID của request.")
    created_at: str = Field(description="Thời điểm xử lý (UTC ISO-8601).")
    source: str = Field(description="Caller source.")
    metadata: Dict[str, Any] = Field(description="Metadata đính kèm.")
    people_count: int = Field(description="Số người trích xuất được.")
    relationship_count: int = Field(description="Số quan hệ trích xuất được.")
    warning_count: int = Field(description="Số lượng cảnh báo validation.")


class HistoryResponse(BaseModel):
    total: int = Field(description="Tổng số request đang lưu trong store.")
    items: List[HistoryItem] = Field(description="Danh sách request gần nhất (mới nhất trước).")


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

Phân tích văn bản gia phả (tiếng Việt) theo quy tắc NLP rule-based,
trả về danh sách người, quan hệ và cấu trúc cây JSON để frontend render.

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
    tags=["System"],
    summary="Health check",
    response_description="Trạng thái hệ thống và chế độ lưu lịch sử.",
)
def health() -> Dict[str, str]:
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
    return payload


@app.get(
    "/api/family-tree/history",
    response_model=HistoryResponse,
    tags=["History"],
    summary="Danh sách request gần nhất",
    response_description="Danh sách HistoryItem mới nhất trước.",
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
    response_description="Kết quả phân tích đầy đủ của request.",
    responses={404: {"description": "request_id không tồn tại trong store."}},
)
def get_history_detail(request_id: str) -> AnalyzeResponse:
    """
    Lấy lại kết quả phân tích đầy đủ của một request cụ thể.

    - **request_id**: UUID trả về từ `POST /api/family-tree/analyze`.
    - Trả về **404** nếu request_id không tìm thấy.
    """
    detail = _history_repo.get_detail(request_id) if _history_repo.enabled else None
    if detail:
        return AnalyzeResponse(**detail)

    with _history_lock:
        cached = _detail_store.get(request_id)

    if cached:
        return cached

    raise HTTPException(status_code=404, detail="History request_id not found")


@app.delete(
    "/api/family-tree/history",
    tags=["History"],
    summary="Xoá toàn bộ lịch sử",
    response_description="Số lượng item đã xoá.",
)
def clear_history() -> Dict[str, int]:
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
            return {"cleared": removed}

    with _history_lock:
        removed = len(_history_store)
        _history_store.clear()
        _detail_store.clear()
        _detail_order.clear()
    return {"cleared": removed}


@app.post(
    "/api/family-tree/analyze",
    response_model=AnalyzeResponse,
    tags=["Analysis"],
    summary="Phân tích văn bản gia phả",
    response_description="Kết quả trích xuất người, quan hệ và cây gia đình.",
    status_code=200,
)
def analyze_family_text(req: AnalyzeRequest) -> AnalyzeResponse:
    """
    Phân tích văn bản gia phả và trả về:

    - **extraction.people** — danh sách người (`id`, `full_name`, `birth_year`, `death_year`, `gender`).
    - **extraction.relationships** — danh sách quan hệ (`from_id`, `to_id`, `type`, `confidence`).
      - `type` nhận một trong: `parent_of`, `spouse_of`.
    - **tree_architecture** — cấu trúc cây phẳng (`roots`, `children_map`, `nodes`).
    - **tree** — cây lồng nhau để frontend render trực tiếp.
    - **warnings** — cảnh báo validation (tự quan hệ, trùng cạnh, khoảng tuổi bất thường).
    """
    request_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    extractor = FamilyExtractor()
    extraction = extractor.parse(req.text)

    warnings: List[str] = []
    warnings.extend(validate_no_self_relationship(extraction))
    warnings.extend(validate_no_duplicate_edges(extraction))
    warnings.extend(validate_parent_age_gap(extraction))

    arch = build_tree_architecture(extraction)
    tree = build_nested_tree(arch)

    response_payload = AnalyzeResponse(
        request_id=request_id,
        created_at=created_at,
        source=req.source or "frontend",
        metadata=req.metadata,
        people_count=len(extraction.get("people", [])),
        relationship_count=len(extraction.get("relationships", [])),
        warnings=warnings,
        extraction=extraction,
        tree_architecture=arch,
        tree=tree,
    )

    history_item = HistoryItem(
        request_id=request_id,
        created_at=created_at,
        source=req.source or "frontend",
        metadata=req.metadata,
        people_count=len(extraction.get("people", [])),
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
