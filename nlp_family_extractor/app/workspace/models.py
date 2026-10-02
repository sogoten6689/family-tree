from __future__ import annotations

import enum
from datetime import datetime, timezone

from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OcrStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TreeStatus(str, enum.Enum):
    NONE = "none"
    DRAFT = "draft"
    CREATED = "created"


class UserScan(Base):
    __tablename__ = "user_scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    ocr_status: Mapped[OcrStatus] = mapped_column(
        Enum(OcrStatus),
        nullable=False,
        default=OcrStatus.PENDING,
    )
    tree_status: Mapped[TreeStatus] = mapped_column(
        Enum(TreeStatus),
        nullable=False,
        default=TreeStatus.NONE,
    )
    family_tree_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # LONGTEXT (không phải TEXT — giới hạn 64KB, gia phả dài (vd corpus Hán
    # Nôm nhiều trang) vượt quá dễ dàng và INSERT sẽ lỗi "Data too long").
    source_text: Mapped[str | None] = mapped_column(LONGTEXT, nullable=True)
    source_file_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Văn bản Hán-Nôm gốc (OCR voted_text) và phiên âm Hán-Việt — tách riêng
    # khỏi source_text (dịch nghĩa Quốc ngữ, dùng để trích xuất quan hệ) để
    # hiển thị được cả 3 lớp L1/L2/L3 trong giao diện đọc song song.
    hannom_text: Mapped[str | None] = mapped_column(LONGTEXT, nullable=True)
    transliteration_text: Mapped[str | None] = mapped_column(LONGTEXT, nullable=True)
    # Metadata vote OCR theo trang (vote_method, engines, uncertain_rate,
    # uncertain_spans, structural_diffs) — KHÔNG phải voted_text (đã có ở
    # hannom_text); đây là bằng chứng "đồng thuận đến đâu, chỗ nào chưa chắc"
    # từ scripts/vote_ocr.py, giữ lại để soát lỗi/QA thay vì chỉ giữ kết quả
    # cuối cùng. List[dict] theo đúng thứ tự trang, xem
    # tools/import_hannom_bilingual_corpus.py:_vote_meta.
    ocr_vote_meta: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    # Bounding box OCR (list[{han, confidence, quad, bbox_xyxy, id}]) từ
    # engine kimhannom — xem app/hannom/client.py:normalize_result_bbox.
    ocr_bbox: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    # Version đang hiển thị mặc định (trỏ gia_pha_version.id có is_current=true).
    # NULL nếu bộ gia phả này chưa từng chạy pipeline theo mô hình version mới.
    current_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 5 input bắt buộc để tính mã định danh F-code (xem app/workspace/ma_dinh_danh.py)
    # — chỉ tính được ma_dinh_danh khi cả 5 đã được admin/curator xác nhận.
    quy_mo: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hinh_thuc: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ho_toc: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Toàn văn địa danh như catalogue ghi (có thể dài, vd. "Thôn Trung Tự, tổng
    # Kim Liên, …"); phần rút gọn trong mã (vd "TrungTu") do người đọc chốt.
    dia_danh: Mapped[str | None] = mapped_column(String(512), nullable=True)
    nam_soan_goc: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Mô tả niên đại kèm bằng chứng (vd "Thiệu Trị năm 5 (Ất Tỵ) = 1845 — …").
    nien_dai_mo_ta: Mapped[str | None] = mapped_column(Text, nullable=True)
    ma_dinh_danh: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)


class PipelineStepType(str, enum.Enum):
    OCR = "ocr"
    VOTE = "vote"
    TRANSLITERATION = "transliteration"
    TRANSLATION = "translation"


class GiaPhaPage(Base):
    """Cấu trúc vật lý của 1 trang trong 1 bộ gia phả — không đổi theo version.
    Ảnh/PDF/text độc lập (không loại trừ nhau): 1 trang có thể có cả 3 cùng lúc."""

    __tablename__ = "gia_pha_page"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_scan_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_scans.id"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    image_file_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    pdf_file_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    plain_text: Mapped[str | None] = mapped_column(LONGTEXT, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class GiaPhaVersion(Base):
    """1 lần xử lý (OCR+vote+phiên âm+dịch nghĩa) của cả bộ gia phả. Có thể
    sao chép (fork) từ 1 version khác rồi sửa riêng — không ghi đè bản gốc."""

    __tablename__ = "gia_pha_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_scan_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_scans.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("gia_pha_version.id"), nullable=True
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ocr_engines: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Version nhập từ kết quả LLM bên ngoài (app/workspace/llm_import.py):
    # source = "chatgpt-web"/"gemini-web"…, review_status = pending|approved|
    # rejected. Cả 2 NULL với version do pipeline nội bộ tạo ra. Duyệt KHÔNG
    # tự đặt làm version hiện tại — chỉ quyết định có vào dữ liệu train không.
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    review_status: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)


class GiaPhaVersionStep(Base):
    """1 bước trong pipeline của 1 version — khớp đúng 4 giai đoạn đã build
    trong app/hannom/pipeline.py v2. Tách biệt với bảng genealogy_pipeline_steps
    cũ (bảng đó là tracker cấp hồ sơ, không hỗ trợ version song song)."""

    __tablename__ = "gia_pha_version_step"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_id: Mapped[int] = mapped_column(Integer, ForeignKey("gia_pha_version.id"), nullable=False, index=True)
    step_type: Mapped[PipelineStepType] = mapped_column(Enum(PipelineStepType), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)


class GiaPhaPageContent(Base):
    """Nội dung suy ra cho 1 trang, theo 1 version cụ thể — khớp
    pages[].l1_ocr/l2_phien_am/l3_dich_nghia của corpus JSON nghiên cứu."""

    __tablename__ = "gia_pha_page_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_id: Mapped[int] = mapped_column(Integer, ForeignKey("gia_pha_version.id"), nullable=False, index=True)
    page_id: Mapped[int] = mapped_column(Integer, ForeignKey("gia_pha_page.id"), nullable=False, index=True)
    hannom_text: Mapped[str | None] = mapped_column(LONGTEXT, nullable=True)
    transliteration_text: Mapped[str | None] = mapped_column(LONGTEXT, nullable=True)
    translation_text: Mapped[str | None] = mapped_column(LONGTEXT, nullable=True)
    ocr_bbox: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    ocr_vote_meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # Cặp câu [{cn, sv, vi}] của version nhập từ LLM — nguồn dữ liệu train.
    pairs: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
