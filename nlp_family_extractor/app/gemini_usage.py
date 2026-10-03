from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Integer, String, case, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.database import Base

# Ghi số token của MỖI lần gọi Gemini (bước 0 của phân tích "dùng Gemini hiệu
# quả", 03/10/2026) — để đo chi phí thật theo loại việc trước khi tối ưu
# (thinking, cache, Batch API, đổi model). Ghi là "best effort": lỗi DB không
# bao giờ làm hỏng lần gọi Gemini.

TASKS = ("ocr_vision", "translate", "tree_extract", "ma_dinh_danh", "generic")


class GeminiUsage(Base):
    __tablename__ = "gemini_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )
    task: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thinking_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cached_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    finish_reason: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


def usage_from_response(response: Any) -> dict[str, Any]:
    """Đọc usage_metadata + finish_reason; trường thiếu (khác phiên bản
    google-genai) → 0/None."""
    meta = getattr(response, "usage_metadata", None)

    def count(name: str) -> int:
        return int(getattr(meta, name, None) or 0)

    finish = None
    candidates = getattr(response, "candidates", None) or []
    if candidates:
        reason = getattr(candidates[0], "finish_reason", None)
        finish = (getattr(reason, "name", None) or str(reason))[:32] if reason is not None else None
    return {
        "prompt_tokens": count("prompt_token_count"),
        "output_tokens": count("candidates_token_count"),
        "thinking_tokens": count("thoughts_token_count"),
        "cached_tokens": count("cached_content_token_count"),
        "total_tokens": count("total_token_count"),
        "finish_reason": finish,
    }


def record_usage(*, task: str, model: str, duration_ms: int, ok: bool, error: Optional[str] = None, **usage: Any) -> None:
    try:
        from app.database import database_enabled, session_scope

        if not database_enabled():
            print(f"[gemini-usage] {task} {model} ok={ok} {usage}")
            return
        with session_scope() as db:
            db.add(
                GeminiUsage(
                    task=task if task in TASKS else "generic",
                    model=model[:64],
                    duration_ms=duration_ms,
                    ok=ok,
                    error=(error or None) and error[:255],
                    **{k: v for k, v in usage.items() if k in GeminiUsage.__table__.columns},
                )
            )
    except Exception as exc:  # noqa: BLE001 — không được làm hỏng lần gọi Gemini
        print(f"[gemini-usage] không ghi được: {exc}")


def summarize(db: Session, *, days: int = 30) -> dict[str, Any]:
    """Tổng hợp theo loại việc trong `days` ngày gần nhất."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(
            GeminiUsage.task,
            func.count(),
            func.sum(case((GeminiUsage.ok.is_(False), 1), else_=0)),
            func.sum(GeminiUsage.prompt_tokens),
            func.sum(GeminiUsage.output_tokens),
            func.sum(GeminiUsage.thinking_tokens),
            func.sum(GeminiUsage.total_tokens),
            func.avg(GeminiUsage.duration_ms),
        )
        .where(GeminiUsage.created_at >= since)
        .group_by(GeminiUsage.task)
        .order_by(func.sum(GeminiUsage.total_tokens).desc())
    ).all()
    tasks = [
        {
            "task": task,
            "calls": int(calls or 0),
            "errors": int(errors or 0),
            "prompt_tokens": int(p or 0),
            "output_tokens": int(o or 0),
            "thinking_tokens": int(t or 0),
            "total_tokens": int(total or 0),
            "avg_tokens_per_call": round((total or 0) / calls) if calls else 0,
            "avg_duration_ms": round(avg_ms or 0),
        }
        for task, calls, errors, p, o, t, total, avg_ms in rows
    ]
    return {
        "days": days,
        "tasks": tasks,
        "total_tokens": sum(t["total_tokens"] for t in tasks),
        "total_calls": sum(t["calls"] for t in tasks),
    }


def bootstrap_gemini_usage() -> None:
    from app.database import database_enabled, get_engine

    if database_enabled():
        Base.metadata.create_all(get_engine(), tables=[GeminiUsage.__table__])
