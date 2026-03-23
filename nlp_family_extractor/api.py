from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.extractor import FamilyExtractor
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


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/family-tree/history", response_model=HistoryResponse)
def get_history(limit: int = 20) -> HistoryResponse:
    safe_limit = max(1, min(limit, 100))
    with _history_lock:
        snapshot = list(_history_store)

    items = list(reversed(snapshot))[:safe_limit]
    return HistoryResponse(total=len(snapshot), items=items)


@app.delete("/api/family-tree/history")
def clear_history() -> Dict[str, int]:
    with _history_lock:
        removed = len(_history_store)
        _history_store.clear()
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

    return AnalyzeResponse(
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
