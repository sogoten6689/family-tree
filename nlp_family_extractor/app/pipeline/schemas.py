from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PipelineStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_id: str
    status: str
    skipped_reason: Optional[str] = None
    input_ref: Optional[str] = None
    output_ref: Optional[str] = None
    content_hash: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    document_id: int = 0


class PipelineResponse(BaseModel):
    family_tree_id: str
    steps: List[PipelineStepResponse]


class PipelineSkipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(default="user_skip", max_length=64)


class PipelineRunAllResponse(BaseModel):
    family_tree_id: str
    ran: List[str]
    skipped: List[str]
    errors: List[str]
