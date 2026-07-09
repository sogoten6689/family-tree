from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


PipelineStepStatusValue = Literal["pending", "running", "done", "skipped", "error"]

SKIPPED_REASON_VALUES = (
    "already_exists",
    "not_applicable",
    "user_skip",
    "source_has_later_step",
    "vgp_entry",
)


class PipelineStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_id: str
    status: str
    skipped_reason: Optional[str] = None
    input_ref: Optional[str] = None
    output_ref: Optional[str] = None
    content_hash: Optional[str] = None
    error_message: Optional[str] = None
    manual_override: bool = False
    admin_note: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    document_id: int = 0


class PipelineContextResponse(BaseModel):
    family_tree_id: str
    tree_name: Optional[str] = None
    external_url: Optional[str] = None
    source_type: Optional[str] = None
    node_count: int = 0


class PipelineResponse(BaseModel):
    family_tree_id: str
    context: PipelineContextResponse
    steps: List[PipelineStepResponse]


class PipelineSkipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(default="user_skip", max_length=64)


class PipelineRunAllResponse(BaseModel):
    family_tree_id: str
    ran: List[str]
    skipped: List[str]
    errors: List[str]


class PipelineArtifactFileResponse(BaseModel):
    id: int
    filename: str
    mime_type: str
    url: Optional[str] = None
    size: int = 0


class PipelineArtifactResponse(BaseModel):
    kind: Literal["none", "text", "document", "family_tree"] = "none"
    message: Optional[str] = None
    document_id: Optional[int] = None
    title: Optional[str] = None
    type: Optional[str] = None
    preview_text: Optional[str] = None
    node_count: Optional[int] = None
    files: List[PipelineArtifactFileResponse] = Field(default_factory=list)


class PipelineStepDetailResponse(PipelineStepResponse):
    artifact: PipelineArtifactResponse
    context: PipelineContextResponse


class PipelineStepUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Optional[PipelineStepStatusValue] = None
    skipped_reason: Optional[str] = Field(default=None, max_length=64)
    input_ref: Optional[str] = Field(default=None, max_length=512)
    output_ref: Optional[str] = Field(default=None, max_length=512)
    error_message: Optional[str] = None
    document_id: Optional[int] = Field(default=None, ge=0)
    admin_note: Optional[str] = None

    @model_validator(mode="after")
    def validate_skipped_reason(self) -> "PipelineStepUpdateRequest":
        if self.status == "skipped" and not self.skipped_reason:
            raise ValueError("skipped_reason is required when status is skipped")
        if self.skipped_reason and self.skipped_reason not in SKIPPED_REASON_VALUES:
            raise ValueError(f"Invalid skipped_reason: {self.skipped_reason}")
        return self


class PipelineResyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: Optional[str] = None
