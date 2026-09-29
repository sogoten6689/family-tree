from __future__ import annotations

from sqlalchemy import text

from app.database import Base, database_enabled, get_engine


def _migrate_source_text_to_longtext(engine) -> None:
    """user_scans.source_text từng là TEXT (giới hạn 64KB) — gia phả dài
    (vd import corpus Hán Nôm, hoặc User dán văn bản dài) vượt quá dễ dàng,
    INSERT sẽ lỗi "Data too long". Nới lên LONGTEXT, idempotent (chỉ ALTER
    khi cột hiện tại chưa phải longtext)."""
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT DATA_TYPE FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_scans' "
                "AND COLUMN_NAME = 'source_text'"
            )
        ).fetchone()
        if row is not None and row[0] != "longtext":
            conn.execute(text("ALTER TABLE user_scans MODIFY COLUMN source_text LONGTEXT NULL"))


def ensure_workspace_schema() -> None:
    if not database_enabled():
        return
    engine = get_engine()
    if engine is None:
        return
    from app.workspace import models  # noqa: F401

    Base.metadata.create_all(bind=engine, tables=[models.UserScan.__table__])
    _migrate_source_text_to_longtext(engine)


def bootstrap_workspace() -> None:
    if not database_enabled():
        return
    ensure_workspace_schema()
