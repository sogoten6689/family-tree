from __future__ import annotations

from sqlalchemy import text

from app.database import Base, get_engine


def ensure_documents_schema() -> None:
    # Import models so SQLAlchemy registers metadata before create_all.
    from app.documents import models as _documents_models  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _migrate_documents_columns(engine)
    _migrate_document_files_columns(engine)


def _migrate_documents_columns(engine) -> None:
    with engine.begin() as conn:
        exists = conn.execute(
            text(
                "SELECT COUNT(*) AS cnt FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'documents' "
                "AND COLUMN_NAME = 'subtype'"
            )
        ).scalar()
        if not exists:
            conn.execute(text("ALTER TABLE documents ADD COLUMN subtype VARCHAR(64) NULL"))


def _migrate_document_files_columns(engine) -> None:
    """Kết quả OCR v2 (bbox, dịch nghĩa, vote meta, pipeline version) trên
    file kết quả transcription — xem app/documents/models.py:DocumentFile."""
    with engine.begin() as conn:
        existing = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'document_files'"
                )
            ).fetchall()
        }
        if "ocr_bbox" not in existing:
            conn.execute(text("ALTER TABLE document_files ADD COLUMN ocr_bbox JSON NULL"))
        if "ocr_translation_text" not in existing:
            conn.execute(text("ALTER TABLE document_files ADD COLUMN ocr_translation_text LONGTEXT NULL"))
        if "ocr_vote_meta" not in existing:
            conn.execute(text("ALTER TABLE document_files ADD COLUMN ocr_vote_meta JSON NULL"))
        if "ocr_pipeline_version" not in existing:
            conn.execute(text("ALTER TABLE document_files ADD COLUMN ocr_pipeline_version VARCHAR(16) NULL"))


def bootstrap_documents() -> None:
    ensure_documents_schema()
