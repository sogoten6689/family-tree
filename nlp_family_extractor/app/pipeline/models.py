from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PipelineStepId(str, enum.Enum):
    NAME = "name"
    HANNOM_IMAGE = "hannom_image"
    OCR = "ocr"
    HAN_CHARS = "han_chars"
    QUOC_NGU = "quoc_ngu"
    DISTILLED = "distilled"
    OUTPUT = "output"


class PipelineStepStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    SKIPPED = "skipped"
    ERROR = "error"


PIPELINE_STEP_ORDER: list[PipelineStepId] = [
    PipelineStepId.NAME,
    PipelineStepId.HANNOM_IMAGE,
    PipelineStepId.OCR,
    PipelineStepId.HAN_CHARS,
    PipelineStepId.QUOC_NGU,
    PipelineStepId.DISTILLED,
    PipelineStepId.OUTPUT,
]


class GenealogyPipelineStep(Base):
    __tablename__ = "genealogy_pipeline_steps"
    __table_args__ = (
        UniqueConstraint(
            "family_tree_id",
            "step_id",
            "document_id",
            name="uq_pipeline_step_per_tree",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_tree_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    document_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    step_id: Mapped[PipelineStepId] = mapped_column(
        Enum(PipelineStepId, name="pipeline_step_id", native_enum=False, length=32),
        nullable=False,
    )
    status: Mapped[PipelineStepStatus] = mapped_column(
        Enum(PipelineStepStatus, name="pipeline_step_status", native_enum=False, length=16),
        nullable=False,
        default=PipelineStepStatus.PENDING,
    )
    skipped_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    output_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ResearchSourceLink(Base):
    __tablename__ = "research_source_links"
    __table_args__ = (
        UniqueConstraint(
            "family_tree_id",
            "source_type",
            "external_id",
            name="uq_research_source_link",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_tree_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    external_url: Mapped[str] = mapped_column(String(512), nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
