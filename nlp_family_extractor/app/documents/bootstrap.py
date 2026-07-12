from __future__ import annotations

from sqlalchemy import text

from app.database import Base, get_engine


def ensure_documents_schema() -> None:
    # Import models so SQLAlchemy registers metadata before create_all.
    from app.documents import models as _documents_models  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _migrate_documents_columns(engine)


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


def bootstrap_documents() -> None:
    ensure_documents_schema()
