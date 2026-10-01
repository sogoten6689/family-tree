from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.workspace.ma_dinh_danh import build_ma_dinh_danh
from app.workspace.models import (
    GiaPhaPage,
    GiaPhaPageContent,
    GiaPhaVersion,
    GiaPhaVersionStep,
    OcrStatus,
    PipelineStepType,
    TreeStatus,
    UserScan,
)


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

    def list_all(self) -> List[UserScan]:
        stmt = select(UserScan).order_by(UserScan.uploaded_at.desc(), UserScan.id.desc())
        return list(self._db.scalars(stmt).all())

    def get(self, scan_id: int) -> Optional[UserScan]:
        return self._db.get(UserScan, scan_id)

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
        hannom_text: Optional[str] = None,
        transliteration_text: Optional[str] = None,
        ocr_vote_meta: Optional[List[dict[str, Any]]] = None,
        ocr_bbox: Optional[List[dict[str, Any]]] = None,
    ) -> UserScan:
        scan = UserScan(
            user_id=user_id,
            title=title.strip(),
            file_name=file_name.strip(),
            file_type=file_type.strip() or "unknown",
            page_count=max(1, page_count),
            source_text=source_text,
            hannom_text=hannom_text,
            transliteration_text=transliteration_text,
            ocr_vote_meta=ocr_vote_meta,
            ocr_bbox=ocr_bbox,
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
        source_file_key: Optional[str] = None,
        hannom_text: Optional[str] = None,
        transliteration_text: Optional[str] = None,
        ocr_vote_meta: Optional[List[dict[str, Any]]] = None,
        ocr_bbox: Optional[List[dict[str, Any]]] = None,
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
        if source_file_key is not None:
            scan.source_file_key = source_file_key or None
        if hannom_text is not None:
            scan.hannom_text = hannom_text
        if transliteration_text is not None:
            scan.transliteration_text = transliteration_text
        if ocr_vote_meta is not None:
            scan.ocr_vote_meta = ocr_vote_meta
        if ocr_bbox is not None:
            scan.ocr_bbox = ocr_bbox
        self._db.add(scan)
        self._db.commit()
        self._db.refresh(scan)
        return scan

    def set_ma_dinh_danh_inputs(
        self,
        scan: UserScan,
        *,
        quy_mo: str,
        hinh_thuc: str,
        ho_toc: str,
        dia_danh: str,
        nam_soan_goc: int,
    ) -> UserScan:
        """Lưu 5 input đã xác nhận và tính lại ma_dinh_danh (F-code). Số thứ tự
        3 chữ số = đếm số ma_dinh_danh đã có trong hệ thống +1 (tăng dần theo
        thứ tự xác nhận thật, không suy đoán trước)."""
        scan.quy_mo = quy_mo
        scan.hinh_thuc = hinh_thuc
        scan.ho_toc = ho_toc
        scan.dia_danh = dia_danh
        scan.nam_soan_goc = nam_soan_goc
        existing_count = int(
            self._db.scalar(
                select(func.count()).select_from(UserScan).where(UserScan.ma_dinh_danh.isnot(None))
            )
            or 0
        )
        id_seq = existing_count + 1
        scan.ma_dinh_danh = build_ma_dinh_danh(quy_mo, hinh_thuc, ho_toc, dia_danh, id_seq, nam_soan_goc)
        self._db.add(scan)
        self._db.commit()
        self._db.refresh(scan)
        return scan


class GiaPhaVersionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_by_scan(self, user_scan_id: int) -> List[GiaPhaVersion]:
        stmt = (
            select(GiaPhaVersion)
            .where(GiaPhaVersion.user_scan_id == user_scan_id)
            .order_by(GiaPhaVersion.version_number.desc())
        )
        return list(self._db.scalars(stmt).all())

    def get(self, version_id: int) -> Optional[GiaPhaVersion]:
        return self._db.get(GiaPhaVersion, version_id)

    def get_current(self, user_scan_id: int) -> Optional[GiaPhaVersion]:
        stmt = select(GiaPhaVersion).where(
            GiaPhaVersion.user_scan_id == user_scan_id, GiaPhaVersion.is_current.is_(True)
        )
        return self._db.scalar(stmt)

    def steps_for(self, version_id: int) -> List[GiaPhaVersionStep]:
        stmt = select(GiaPhaVersionStep).where(GiaPhaVersionStep.version_id == version_id)
        return list(self._db.scalars(stmt).all())

    def create_version(
        self,
        *,
        user_scan_id: int,
        ocr_engines: Optional[List[str]] = None,
        parent_version_id: Optional[int] = None,
        created_by: Optional[int] = None,
        note: Optional[str] = None,
        make_current: bool = True,
    ) -> GiaPhaVersion:
        last_number = int(
            self._db.scalar(
                select(func.max(GiaPhaVersion.version_number)).where(
                    GiaPhaVersion.user_scan_id == user_scan_id
                )
            )
            or 0
        )
        version = GiaPhaVersion(
            user_scan_id=user_scan_id,
            version_number=last_number + 1,
            parent_version_id=parent_version_id,
            ocr_engines=ocr_engines,
            created_by=created_by,
            note=note,
            is_current=False,
            status="draft",
        )
        self._db.add(version)
        self._db.flush()
        for step_type in PipelineStepType:
            self._db.add(GiaPhaVersionStep(version_id=version.id, step_type=step_type, status="pending"))
        if make_current:
            self.set_current(user_scan_id, version.id)
        self._db.commit()
        self._db.refresh(version)
        return version

    def set_current(self, user_scan_id: int, version_id: int) -> None:
        stmt = select(GiaPhaVersion).where(GiaPhaVersion.user_scan_id == user_scan_id)
        for version in self._db.scalars(stmt).all():
            version.is_current = version.id == version_id
            self._db.add(version)
        scan = self._db.get(UserScan, user_scan_id)
        if scan is not None:
            scan.current_version_id = version_id
            self._db.add(scan)

    def clone_version(self, source_version_id: int, *, created_by: Optional[int] = None) -> GiaPhaVersion:
        """Sao chép 1 version: tạo version mới cùng engine list, copy toàn bộ
        gia_pha_page_content sang version mới. Version nguồn giữ nguyên."""
        source = self._db.get(GiaPhaVersion, source_version_id)
        if source is None:
            raise ValueError(f"Không tìm thấy version {source_version_id}")
        new_version = self.create_version(
            user_scan_id=source.user_scan_id,
            ocr_engines=source.ocr_engines,
            parent_version_id=source.id,
            created_by=created_by,
            make_current=False,
        )
        source_contents = self._db.scalars(
            select(GiaPhaPageContent).where(GiaPhaPageContent.version_id == source.id)
        ).all()
        for content in source_contents:
            self._db.add(
                GiaPhaPageContent(
                    version_id=new_version.id,
                    page_id=content.page_id,
                    hannom_text=content.hannom_text,
                    transliteration_text=content.transliteration_text,
                    translation_text=content.translation_text,
                    ocr_bbox=content.ocr_bbox,
                    ocr_vote_meta=content.ocr_vote_meta,
                )
            )
        for source_step in self._db.scalars(
            select(GiaPhaVersionStep).where(GiaPhaVersionStep.version_id == source.id)
        ).all():
            new_step = self._db.scalar(
                select(GiaPhaVersionStep).where(
                    GiaPhaVersionStep.version_id == new_version.id,
                    GiaPhaVersionStep.step_type == source_step.step_type,
                )
            )
            if new_step is not None:
                new_step.status = source_step.status
                new_step.started_at = source_step.started_at
                new_step.finished_at = source_step.finished_at
                self._db.add(new_step)
        self._db.commit()
        self._db.refresh(new_version)
        return new_version


class GiaPhaPageRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_by_scan(self, user_scan_id: int) -> List[GiaPhaPage]:
        stmt = (
            select(GiaPhaPage)
            .where(GiaPhaPage.user_scan_id == user_scan_id)
            .order_by(GiaPhaPage.page_number.asc())
        )
        return list(self._db.scalars(stmt).all())

    def create_page(
        self,
        *,
        user_scan_id: int,
        page_number: int,
        image_file_key: Optional[str] = None,
        pdf_file_key: Optional[str] = None,
        plain_text: Optional[str] = None,
    ) -> GiaPhaPage:
        page = GiaPhaPage(
            user_scan_id=user_scan_id,
            page_number=page_number,
            image_file_key=image_file_key,
            pdf_file_key=pdf_file_key,
            plain_text=plain_text,
        )
        self._db.add(page)
        self._db.commit()
        self._db.refresh(page)
        return page

    def upsert_content(
        self,
        *,
        version_id: int,
        page_id: int,
        hannom_text: Optional[str] = None,
        transliteration_text: Optional[str] = None,
        translation_text: Optional[str] = None,
        ocr_bbox: Optional[List[dict[str, Any]]] = None,
        ocr_vote_meta: Optional[dict[str, Any]] = None,
    ) -> GiaPhaPageContent:
        content = self._db.scalar(
            select(GiaPhaPageContent).where(
                GiaPhaPageContent.version_id == version_id, GiaPhaPageContent.page_id == page_id
            )
        )
        if content is None:
            content = GiaPhaPageContent(version_id=version_id, page_id=page_id)
        if hannom_text is not None:
            content.hannom_text = hannom_text
        if transliteration_text is not None:
            content.transliteration_text = transliteration_text
        if translation_text is not None:
            content.translation_text = translation_text
        if ocr_bbox is not None:
            content.ocr_bbox = ocr_bbox
        if ocr_vote_meta is not None:
            content.ocr_vote_meta = ocr_vote_meta
        self._db.add(content)
        self._db.commit()
        self._db.refresh(content)
        return content

    def list_content_for_version(self, version_id: int) -> List[GiaPhaPageContent]:
        stmt = select(GiaPhaPageContent).where(GiaPhaPageContent.version_id == version_id)
        return list(self._db.scalars(stmt).all())

    def sync_flat_cache(self, scan_repo: "UserScanRepository", user_scan_id: int, version_id: int) -> None:
        """Dồn nội dung theo trang của 1 version thành cache phẳng trên
        UserScan (tương thích ngược cho ReaderWorkspace/PipelineStepsPanel)."""
        pages = self.list_by_scan(user_scan_id)
        contents = {c.page_id: c for c in self.list_content_for_version(version_id)}
        hannom_parts, translit_parts, translation_parts = [], [], []
        for page in pages:
            content = contents.get(page.id)
            if content is None:
                continue
            if content.hannom_text:
                hannom_parts.append(content.hannom_text)
            if content.transliteration_text:
                translit_parts.append(content.transliteration_text)
            if content.translation_text:
                translation_parts.append(content.translation_text)
        scan = self._db.get(UserScan, user_scan_id)
        if scan is None:
            return
        sep = "\n\n---\n\n"
        if hannom_parts:
            scan.hannom_text = sep.join(hannom_parts)
        if translit_parts:
            scan.transliteration_text = sep.join(translit_parts)
        if translation_parts:
            scan.source_text = sep.join(translation_parts)
        self._db.add(scan)
        self._db.commit()
