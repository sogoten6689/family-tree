from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import User, UserRole
from app.workspace.ma_dinh_danh import build_ma_dinh_danh, letter_for, next_sequence_for_letter
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


# 2 bước do nguồn ngoài (file LLM / engine phiên âm-dịch) thay thế.
TEXT_STEP_TYPES = (PipelineStepType.TRANSLITERATION, PipelineStepType.TRANSLATION)


class UserScanRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_by_user(self, user_id: int, *, include_deleted: bool = False) -> List[UserScan]:
        """Mặc định ẩn bộ đã xoá mềm. Script import phải truyền include_deleted=True
        để nhận ra bộ đã nhập (nếu không sẽ tạo bản trùng)."""
        stmt = select(UserScan).where(UserScan.user_id == user_id)
        if not include_deleted:
            stmt = stmt.where(UserScan.deleted_at.is_(None))
        stmt = stmt.order_by(UserScan.uploaded_at.desc(), UserScan.id.desc())
        return list(self._db.scalars(stmt).all())

    def list_all(self, *, include_deleted: bool = False) -> List[UserScan]:
        stmt = select(UserScan)
        if not include_deleted:
            stmt = stmt.where(UserScan.deleted_at.is_(None))
        stmt = stmt.order_by(UserScan.uploaded_at.desc(), UserScan.id.desc())
        return list(self._db.scalars(stmt).all())

    def list_deleted(self) -> List[UserScan]:
        stmt = (
            select(UserScan)
            .where(UserScan.deleted_at.is_not(None))
            .order_by(UserScan.deleted_at.desc(), UserScan.id.desc())
        )
        return list(self._db.scalars(stmt).all())

    def soft_delete(self, scan: UserScan, *, user_id: int) -> UserScan:
        scan.deleted_at = datetime.now(timezone.utc)
        scan.deleted_by = user_id
        self._db.add(scan)
        self._db.commit()
        self._db.refresh(scan)
        return scan

    def restore(self, scan: UserScan) -> UserScan:
        scan.deleted_at = None
        scan.deleted_by = None
        self._db.add(scan)
        self._db.commit()
        self._db.refresh(scan)
        return scan

    def get(self, scan_id: int) -> Optional[UserScan]:
        return self._db.get(UserScan, scan_id)

    def by_family_tree_ids(self, tree_ids: List[str]) -> dict[str, UserScan]:
        """Scan nguồn của các cây đã dựng (để danh sách Gia phả hiện đúng mã
        định danh của bộ, không phải id kỹ thuật của cây)."""
        if not tree_ids:
            return {}
        stmt = select(UserScan).where(UserScan.family_tree_id.in_(tree_ids), UserScan.deleted_at.is_(None))
        return {scan.family_tree_id: scan for scan in self._db.scalars(stmt).all() if scan.family_tree_id}

    def count_by_user(self, user_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(UserScan)
            .where(UserScan.user_id == user_id, UserScan.deleted_at.is_(None))
        )
        return int(self._db.scalar(stmt) or 0)

    def get_for_user(self, user_id: int, scan_id: int) -> Optional[UserScan]:
        stmt = select(UserScan).where(
            UserScan.id == scan_id, UserScan.user_id == user_id, UserScan.deleted_at.is_(None)
        )
        return self._db.scalar(stmt)

    def get_accessible(self, user: User, scan_id: int) -> Optional[UserScan]:
        """Bộ gia phả `user` được phép mở: Admin mở được mọi bản ghi (khớp
        phạm vi `list_all()` mà `GET /api/gia-pha` trả cho Admin), User chỉ
        mở bản ghi của chính mình."""
        if user.role == UserRole.ADMIN:
            scan = self.get(scan_id)
            return None if scan is None or scan.deleted_at is not None else scan
        return self.get_for_user(user.id, scan_id)

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

    def auto_assign_ma_dinh_danh(self, scan: UserScan, inputs: dict[str, Any], *, nguon: str) -> UserScan:
        """Tự tạo mã định danh từ 5 input (đã kiểm tra) — số 3 chữ số đánh
        RIÊNG theo chữ A–V: số lớn nhất đang có ở chữ đó + 1. Scan đã có mã
        thì giữ nguyên (không bao giờ ghi đè mã đã chốt). Raise ValueError nếu
        input không ra được mã hoặc mã trùng."""
        if scan.ma_dinh_danh:
            return scan
        letter = letter_for(inputs["quy_mo"], inputs["hinh_thuc"])
        if letter is None:
            raise ValueError(f"Không có chữ mã cho ({inputs['quy_mo']}, {inputs['hinh_thuc']}).")
        existing = [
            code
            for code in self._db.scalars(
                select(UserScan.ma_dinh_danh).where(UserScan.ma_dinh_danh.like(f"F-{letter}-%"))
            ).all()
            if code
        ]
        seq = next_sequence_for_letter(existing, letter)
        code = build_ma_dinh_danh(
            inputs["quy_mo"], inputs["hinh_thuc"], inputs["ho_toc"], inputs["dia_danh_ngan"], seq, inputs["nam_soan_goc"]
        )
        if self._db.scalar(select(UserScan).where(UserScan.ma_dinh_danh == code)) is not None:
            raise ValueError(f"Mã {code} đã tồn tại.")
        scan.quy_mo = inputs["quy_mo"]
        scan.hinh_thuc = inputs["hinh_thuc"]
        scan.ho_toc = inputs["ho_toc"]
        scan.nam_soan_goc = inputs["nam_soan_goc"]
        if not scan.dia_danh:
            scan.dia_danh = inputs["dia_danh_ngan"]
        scan.ma_dinh_danh = code
        scan.ma_dinh_danh_nguon = nguon
        self._db.add(scan)
        self._db.commit()
        self._db.refresh(scan)
        return scan

    def set_corpus_identifiers(self, scan: UserScan, fields: dict[str, Any]) -> UserScan:
        """Ghi mã định danh + thông tin đi kèm ĐÃ CHỐT ở catalogue nghiên cứu
        (chép nguyên văn, không tính lại) — chỉ dùng khi import corpus."""
        for key in (
            "ma_dinh_danh",
            "ma_dinh_danh_nguon",
            "quy_mo",
            "hinh_thuc",
            "ho_toc",
            "dia_danh",
            "nam_soan_goc",
            "nien_dai_mo_ta",
        ):
            if key in fields:
                setattr(scan, key, fields[key])
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

    def get_many(self, version_ids: List[int]) -> dict[int, GiaPhaVersion]:
        """Nhiều version trong 1 truy vấn (danh sách Gia phả: tránh N+1)."""
        if not version_ids:
            return {}
        stmt = select(GiaPhaVersion).where(GiaPhaVersion.id.in_(set(version_ids)))
        return {v.id: v for v in self._db.scalars(stmt).all()}

    def steps_for_many(self, version_ids: List[int]) -> dict[int, List[GiaPhaVersionStep]]:
        if not version_ids:
            return {}
        stmt = select(GiaPhaVersionStep).where(GiaPhaVersionStep.version_id.in_(set(version_ids)))
        grouped: dict[int, List[GiaPhaVersionStep]] = {}
        for step in self._db.scalars(stmt).all():
            grouped.setdefault(step.version_id, []).append(step)
        return grouped

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
                    pairs=content.pairs,
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


    def create_derived_version(
        self,
        *,
        user_scan_id: int,
        parent_version_id: int,
        source: str,
        review_status: Optional[str],
        note: Optional[str] = None,
        created_by: Optional[int] = None,
        text_step_status: Optional[str] = "pending",
    ) -> GiaPhaVersion:
        """Version mới từ nguồn ngoài (file LLM / engine phiên âm-dịch): copy
        toàn bộ nội dung version cha (giữ OCR), chưa đổi phiên âm/dịch nghĩa.
        `text_step_status=None` = giữ nguyên trạng thái bước phiên âm/dịch của
        version cha (dùng khi chỉ sửa tay). Không đặt làm version hiện tại;
        version cha giữ nguyên."""
        parent = self._db.get(GiaPhaVersion, parent_version_id)
        if parent is None or parent.user_scan_id != user_scan_id:
            raise ValueError(f"Version cha {parent_version_id} không thuộc bộ gia phả {user_scan_id}")
        version = self.create_version(
            user_scan_id=user_scan_id,
            ocr_engines=parent.ocr_engines,
            parent_version_id=parent.id,
            created_by=created_by,
            note=note,
            make_current=False,
        )
        version.source = source
        version.review_status = review_status
        for base in self._db.scalars(
            select(GiaPhaPageContent).where(GiaPhaPageContent.version_id == parent.id)
        ).all():
            self._db.add(
                GiaPhaPageContent(
                    version_id=version.id,
                    page_id=base.page_id,
                    hannom_text=base.hannom_text,
                    transliteration_text=base.transliteration_text,
                    translation_text=base.translation_text,
                    ocr_bbox=base.ocr_bbox,
                    ocr_vote_meta=base.ocr_vote_meta,
                    pairs=base.pairs,
                )
            )
        parent_steps = {s.step_type: s.status for s in self.steps_for(parent.id)}
        for step in self.steps_for(version.id):
            if step.step_type in TEXT_STEP_TYPES and text_step_status is not None:
                step.status = text_step_status
            else:
                step.status = parent_steps.get(step.step_type, step.status)
            self._db.add(step)
        self._db.add(version)
        self._db.commit()
        self._db.refresh(version)
        return version

    def apply_page_records(self, version_id: int, pages: dict[int, list[dict[str, str]]], page_ids: dict[int, int]) -> None:
        """Ghi kết quả {cn, sv, vi} vào các trang: phiên âm = sv nối dòng,
        dịch nghĩa = vi nối dòng, pairs = các câu (dữ liệu train)."""
        for number, records in pages.items():
            page_id = page_ids[number]
            content = self._db.scalar(
                select(GiaPhaPageContent).where(
                    GiaPhaPageContent.version_id == version_id, GiaPhaPageContent.page_id == page_id
                )
            )
            if content is None:
                content = GiaPhaPageContent(version_id=version_id, page_id=page_id)
            content.transliteration_text = "\n".join(r["sv"] for r in records)
            content.translation_text = "\n".join(r["vi"] for r in records)
            content.pairs = records
            self._db.add(content)
        self._db.commit()

    def set_text_steps(
        self,
        version_id: int,
        status: str,
        *,
        error_message: Optional[str] = None,
        started: bool = False,
        finished: bool = False,
    ) -> None:
        now = datetime.now(timezone.utc)
        for step in self.steps_for(version_id):
            if step.step_type not in TEXT_STEP_TYPES:
                continue
            step.status = status
            step.error_message = error_message[:1024] if error_message else None
            if started:
                step.started_at = now
            if finished:
                step.finished_at = now
            self._db.add(step)
        self._db.commit()

    def create_import_version(
        self,
        *,
        user_scan_id: int,
        parent_version_id: int,
        source: str,
        model_note: Optional[str],
        pages: dict[int, list[dict[str, str]]],
        page_ids: dict[int, int],
        created_by: Optional[int] = None,
    ) -> GiaPhaVersion:
        """Nhập file kết quả LLM: version mới chờ duyệt + ghi các trang được nhập."""
        version = self.create_derived_version(
            user_scan_id=user_scan_id,
            parent_version_id=parent_version_id,
            source=source,
            review_status="pending",
            note=model_note,
            created_by=created_by,
            text_step_status="imported",
        )
        self.apply_page_records(version.id, pages, page_ids)
        self._db.refresh(version)
        return version

    def set_review_status(self, version_id: int, review_status: str) -> GiaPhaVersion:
        version = self._db.get(GiaPhaVersion, version_id)
        if version is None:
            raise ValueError(f"Không tìm thấy version {version_id}")
        version.review_status = review_status
        self._db.add(version)
        self._db.commit()
        self._db.refresh(version)
        return version

    def approved_pairs(self) -> List[dict[str, Any]]:
        """Cặp câu của mọi version nhập đã duyệt — dữ liệu train (kèm nguồn)."""
        stmt = (
            select(GiaPhaVersion, GiaPhaPageContent, GiaPhaPage)
            .join(GiaPhaPageContent, GiaPhaPageContent.version_id == GiaPhaVersion.id)
            .join(GiaPhaPage, GiaPhaPage.id == GiaPhaPageContent.page_id)
            .where(GiaPhaVersion.review_status == "approved")
            .order_by(GiaPhaVersion.user_scan_id, GiaPhaVersion.id, GiaPhaPage.page_number)
        )
        rows: List[dict[str, Any]] = []
        for version, content, page in self._db.execute(stmt).all():
            for pair in content.pairs or []:
                rows.append(
                    {
                        "scan_id": version.user_scan_id,
                        "version_id": version.id,
                        "source": version.source,
                        "page": page.page_number,
                        "cn": pair.get("cn"),
                        "sv": pair.get("sv"),
                        "vi": pair.get("vi"),
                    }
                )
        return rows


class GiaPhaPageRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_by_scan(self, user_scan_id: int, *, include_deleted: bool = False) -> List[GiaPhaPage]:
        """Mặc định ẩn trang đã xoá mềm. Script import truyền include_deleted=True
        để không tạo lại/trùng trang đã xoá."""
        stmt = select(GiaPhaPage).where(GiaPhaPage.user_scan_id == user_scan_id)
        if not include_deleted:
            stmt = stmt.where(GiaPhaPage.deleted_at.is_(None))
        stmt = stmt.order_by(GiaPhaPage.page_number.asc())
        return list(self._db.scalars(stmt).all())

    def list_deleted_by_scan(self, user_scan_id: int) -> List[GiaPhaPage]:
        stmt = (
            select(GiaPhaPage)
            .where(GiaPhaPage.user_scan_id == user_scan_id, GiaPhaPage.deleted_at.is_not(None))
            .order_by(GiaPhaPage.page_number.asc())
        )
        return list(self._db.scalars(stmt).all())

    def sync_page_count(self, user_scan_id: int) -> int:
        """page_count của bộ = số trang đang dùng (không tính trang xoá mềm).
        Bộ chưa có hàng gia_pha_page nào (chưa cấu trúc hoá) giữ nguyên số cũ."""
        total = int(
            self._db.scalar(select(func.count()).select_from(GiaPhaPage).where(GiaPhaPage.user_scan_id == user_scan_id))
            or 0
        )
        scan = self._db.get(UserScan, user_scan_id)
        active = len(self.list_by_scan(user_scan_id))
        if scan is not None and total > 0 and scan.page_count != active:
            scan.page_count = active
            self._db.add(scan)
            self._db.commit()
        return active

    def set_deleted(self, page: GiaPhaPage, *, deleted: bool, user_id: Optional[int] = None) -> GiaPhaPage:
        page.deleted_at = datetime.now(timezone.utc) if deleted else None
        page.deleted_by = user_id if deleted else None
        self._db.add(page)
        self._db.commit()
        self._db.refresh(page)
        return page

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

    def set_image_key(self, page: GiaPhaPage, image_file_key: str) -> GiaPhaPage:
        page.image_file_key = image_file_key
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
        clear_vote_meta: bool = False,
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
        elif clear_vote_meta:
            content.ocr_vote_meta = None
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
