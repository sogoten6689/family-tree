from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.workspace.models import OcrStatus, TreeStatus, UserScan


class UserScanRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_by_user(self, user_id: int) -> List[UserScan]:
        stmt = (
            select(UserScan)
            .where(UserScan.user_id == user_id)
            .order_by(UserScan.uploaded_at.desc(), UserScan.id.desc())
        )
        return list(self._db.scalars(stmt).all())

    def count_by_user(self, user_id: int) -> int:
        stmt = select(func.count()).select_from(UserScan).where(UserScan.user_id == user_id)
        return int(self._db.scalar(stmt) or 0)

    def get_for_user(self, user_id: int, scan_id: int) -> Optional[UserScan]:
        stmt = select(UserScan).where(UserScan.id == scan_id, UserScan.user_id == user_id)
        return self._db.scalar(stmt)

    def create(
        self,
        *,
        user_id: int,
        title: str,
        file_name: str,
        file_type: str,
        page_count: int = 1,
        source_text: Optional[str] = None,
    ) -> UserScan:
        scan = UserScan(
            user_id=user_id,
            title=title.strip(),
            file_name=file_name.strip(),
            file_type=file_type.strip() or "unknown",
            page_count=max(1, page_count),
            source_text=source_text,
            uploaded_at=datetime.now(timezone.utc),
        )
        self._db.add(scan)
        self._db.commit()
        self._db.refresh(scan)
        return scan

    def update(
        self,
        scan: UserScan,
        *,
        title: Optional[str] = None,
        ocr_status: Optional[OcrStatus] = None,
        tree_status: Optional[TreeStatus] = None,
        family_tree_id: Optional[str] = None,
        request_id: Optional[str] = None,
        source_text: Optional[str] = None,
    ) -> UserScan:
        if title is not None:
            scan.title = title.strip()
        if ocr_status is not None:
            scan.ocr_status = ocr_status
        if tree_status is not None:
            scan.tree_status = tree_status
        if family_tree_id is not None:
            scan.family_tree_id = family_tree_id or None
        if request_id is not None:
            scan.request_id = request_id or None
        if source_text is not None:
            scan.source_text = source_text
        self._db.add(scan)
        self._db.commit()
        self._db.refresh(scan)
        return scan
