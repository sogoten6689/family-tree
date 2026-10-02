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
    _migrate_user_scans_columns(engine)
    _migrate_source_text_to_longtext(engine)
    Base.metadata.create_all(
        bind=engine,
        tables=[
            models.GiaPhaPage.__table__,
            models.GiaPhaVersion.__table__,
            models.GiaPhaVersionStep.__table__,
            models.GiaPhaPageContent.__table__,
        ],
    )
    _migrate_gia_pha_columns(engine)
    _migrate_llm_import_columns(engine)
    _migrate_identifier_columns(engine)


def _migrate_gia_pha_columns(engine) -> None:
    """Cột mới trên user_scans cho mô hình version + mã định danh F-code
    (xem app/workspace/ma_dinh_danh.py). Idempotent."""
    with engine.begin() as conn:
        existing = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_scans'"
                )
            ).fetchall()
        }
        if "current_version_id" not in existing:
            conn.execute(text("ALTER TABLE user_scans ADD COLUMN current_version_id INT NULL"))
        if "quy_mo" not in existing:
            conn.execute(text("ALTER TABLE user_scans ADD COLUMN quy_mo VARCHAR(32) NULL"))
        if "hinh_thuc" not in existing:
            conn.execute(text("ALTER TABLE user_scans ADD COLUMN hinh_thuc VARCHAR(32) NULL"))
        if "ho_toc" not in existing:
            conn.execute(text("ALTER TABLE user_scans ADD COLUMN ho_toc VARCHAR(64) NULL"))
        if "dia_danh" not in existing:
            conn.execute(text("ALTER TABLE user_scans ADD COLUMN dia_danh VARCHAR(128) NULL"))
        if "nam_soan_goc" not in existing:
            conn.execute(text("ALTER TABLE user_scans ADD COLUMN nam_soan_goc INT NULL"))
        if "ma_dinh_danh" not in existing:
            conn.execute(text("ALTER TABLE user_scans ADD COLUMN ma_dinh_danh VARCHAR(64) NULL"))
            conn.execute(text("CREATE INDEX ix_user_scans_ma_dinh_danh ON user_scans (ma_dinh_danh)"))


def _existing_columns(conn, table: str) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            text(
                "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table"
            ),
            {"table": table},
        ).fetchall()
    }


def _migrate_llm_import_columns(engine) -> None:
    """Cột cho version nhập từ LLM (app/workspace/llm_import.py). Idempotent."""
    with engine.begin() as conn:
        version_cols = _existing_columns(conn, "gia_pha_version")
        if "source" not in version_cols:
            conn.execute(text("ALTER TABLE gia_pha_version ADD COLUMN source VARCHAR(64) NULL"))
        if "review_status" not in version_cols:
            conn.execute(text("ALTER TABLE gia_pha_version ADD COLUMN review_status VARCHAR(16) NULL"))
            conn.execute(
                text("CREATE INDEX ix_gia_pha_version_review_status ON gia_pha_version (review_status)")
            )
        if "pairs" not in _existing_columns(conn, "gia_pha_page_content"):
            conn.execute(text("ALTER TABLE gia_pha_page_content ADD COLUMN pairs JSON NULL"))


def _migrate_identifier_columns(engine) -> None:
    """dia_danh 128 -> 512 (catalogue ghi toàn văn địa danh, có bản ~170 ký tự)
    + nien_dai_mo_ta. Idempotent."""
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT COLUMN_NAME, CHARACTER_MAXIMUM_LENGTH FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_scans'"
            )
        ).fetchall()
        lengths = {row[0]: row[1] for row in rows}
        if "dia_danh" in lengths and (lengths["dia_danh"] or 0) < 512:
            conn.execute(text("ALTER TABLE user_scans MODIFY COLUMN dia_danh VARCHAR(512) NULL"))
        if "nien_dai_mo_ta" not in lengths:
            conn.execute(text("ALTER TABLE user_scans ADD COLUMN nien_dai_mo_ta TEXT NULL"))
        if "ma_dinh_danh_nguon" not in lengths:
            conn.execute(text("ALTER TABLE user_scans ADD COLUMN ma_dinh_danh_nguon VARCHAR(16) NULL"))


def _migrate_user_scans_columns(engine) -> None:
    with engine.begin() as conn:
        existing = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_scans'"
                )
            ).fetchall()
        }
        if "source_file_key" not in existing:
            conn.execute(text("ALTER TABLE user_scans ADD COLUMN source_file_key VARCHAR(512) NULL"))
        if "hannom_text" not in existing:
            conn.execute(text("ALTER TABLE user_scans ADD COLUMN hannom_text LONGTEXT NULL"))
        if "transliteration_text" not in existing:
            conn.execute(text("ALTER TABLE user_scans ADD COLUMN transliteration_text LONGTEXT NULL"))
        if "ocr_vote_meta" not in existing:
            conn.execute(text("ALTER TABLE user_scans ADD COLUMN ocr_vote_meta JSON NULL"))
        if "ocr_bbox" not in existing:
            conn.execute(text("ALTER TABLE user_scans ADD COLUMN ocr_bbox JSON NULL"))


def bootstrap_workspace() -> None:
    if not database_enabled():
        return
    ensure_workspace_schema()
    # Hàng đợi engine phiên âm/dịch nằm trong bộ nhớ → job dở dang lúc tắt
    # server đã mất; đánh dấu lỗi để version không treo ở "running".
    from app.database import session_scope
    from app.hannom.text_engine_runner import fail_interrupted_runs

    with session_scope() as db:
        fail_interrupted_runs(db)
