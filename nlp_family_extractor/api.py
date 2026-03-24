from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI
from fastapi import HTTPException
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
    text: str = Field(min_length=1, description="Raw family document text extracted by frontend")
    source: Optional[str] = Field(default="frontend", description="Caller source")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnalyzeResponse(BaseModel):
    request_id: str
    created_at: str
    source: str
    metadata: Dict[str, Any]
    people_count: int
    relationship_count: int
    warnings: List[str]
    extraction: Dict[str, Any]
    tree_architecture: Dict[str, Any]
    tree: List[Dict[str, Any]]


class HistoryItem(BaseModel):
    request_id: str
    created_at: str
    source: str
    metadata: Dict[str, Any]
    people_count: int
    relationship_count: int
    warning_count: int


class HistoryResponse(BaseModel):
    total: int
    items: List[HistoryItem]


app = FastAPI(
    title="Family Tree Analyzer API",
    version="1.0.0",
    description="Analyze genealogy text and return normalized people/relationships + JSON tree architecture.",
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


@app.get("/health")
def health() -> Dict[str, str]:
    payload = {
        "status": "ok",
        "history_storage": "mysql" if _history_repo.enabled else "memory",
    }
    if _history_repo.init_error:
        payload["history_init_error"] = _history_repo.init_error
    return payload


@app.get("/api/family-tree/history", response_model=HistoryResponse)
def get_history(limit: int = 20) -> HistoryResponse:
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


@app.get("/api/family-tree/history/{request_id}", response_model=AnalyzeResponse)
def get_history_detail(request_id: str) -> AnalyzeResponse:
    detail = _history_repo.get_detail(request_id) if _history_repo.enabled else None
    if detail:
        return AnalyzeResponse(**detail)

    with _history_lock:
        cached = _detail_store.get(request_id)

    if cached:
        return cached

    raise HTTPException(status_code=404, detail="History request_id not found")


@app.delete("/api/family-tree/history")
def clear_history() -> Dict[str, int]:
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


@app.post("/api/family-tree/analyze", response_model=AnalyzeResponse)
def analyze_family_text(req: AnalyzeRequest) -> AnalyzeResponse:
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
