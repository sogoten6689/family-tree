from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class VgpCrawl(Base):
    __tablename__ = "vgp_crawl"

    family_tree_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    vgp_tree_id: Mapped[int] = mapped_column(Integer, nullable=False)
    crawl_version: Mapped[str] = mapped_column(String(8), nullable=False, default="v2")
    manifest_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    nodes_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    pha_ky_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fetched_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)
