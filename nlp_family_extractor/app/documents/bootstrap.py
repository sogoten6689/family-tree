from __future__ import annotations

from app.database import Base, get_engine


def ensure_documents_schema() -> None:
    # Import models so SQLAlchemy registers metadata before create_all.
    from app.documents import models as _documents_models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())


def bootstrap_documents() -> None:
    ensure_documents_schema()
