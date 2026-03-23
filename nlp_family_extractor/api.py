from __future__ import annotations

from typing import Any, Dict, List, Optional

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
    source: str
    metadata: Dict[str, Any]
    people_count: int
    relationship_count: int
    warnings: List[str]
    extraction: Dict[str, Any]
    tree_architecture: Dict[str, Any]
    tree: List[Dict[str, Any]]


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


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/family-tree/analyze", response_model=AnalyzeResponse)
def analyze_family_text(req: AnalyzeRequest) -> AnalyzeResponse:
    extractor = FamilyExtractor()
    extraction = extractor.parse(req.text)

    warnings: List[str] = []
    warnings.extend(validate_no_self_relationship(extraction))
    warnings.extend(validate_no_duplicate_edges(extraction))
    warnings.extend(validate_parent_age_gap(extraction))

    arch = build_tree_architecture(extraction)
    tree = build_nested_tree(arch)

    return AnalyzeResponse(
        source=req.source or "frontend",
        metadata=req.metadata,
        people_count=len(extraction.get("people", [])),
        relationship_count=len(extraction.get("relationships", [])),
        warnings=warnings,
        extraction=extraction,
        tree_architecture=arch,
        tree=tree,
    )
