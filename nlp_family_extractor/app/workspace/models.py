from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OcrStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TreeStatus(str, enum.Enum):
    NONE = "none"
    DRAFT = "draft"
    CREATED = "created"


class UserScan(Base):
    __tablename__ = "user_scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    ocr_status: Mapped[OcrStatus] = mapped_column(
        Enum(OcrStatus),
        nullable=False,
        default=OcrStatus.PENDING,
    )
    tree_status: Mapped[TreeStatus] = mapped_column(
        Enum(TreeStatus),
        nullable=False,
        default=TreeStatus.NONE,
    )
    family_tree_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
