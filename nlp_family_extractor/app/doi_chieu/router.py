from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, StringConstraints

from app.auth.dependencies import AdminUser
from app.doi_chieu import cham_mau, nhan_xet, service, soat, vote

# Công khai, không cần đăng nhập (theo yêu cầu): chỉ đọc. Phần ghi nằm ở admin_router bên dưới.
# Chưa đặt DOI_CHIEU_DIR (hoặc thư mục không tồn tại) thì trả danh sách rỗng.
router = APIRouter(prefix="/api/public/doi-chieu", tags=["Đối chiếu dóng hàng"])


def _root():
    root = service.data_dir()
    if root is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Chưa có dữ liệu đối chiếu.")
    return root


@router.get("")
def get_overview() -> dict:
    root = service.data_dir()
    if root is None:
        return {"target": service.TARGET_PAIRS, "error_threshold": service.ERROR_THRESHOLD, "students": []}
    return service.overview(root)


@router.get("/{student}/{book}")
def get_book(student: str, book: str) -> dict:
    root = _root()
    bdir = service.book_dir(root, student, book)
    if bdir is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cuốn.")
    detail = service.load_book(bdir)
    return {
        "student": student,
        "book": book,
        **service.book_info(root, book),
        **detail,
        "pages": service.page_names(bdir),
        # Chỉ phần tổng hợp; nhãn từng dòng chỉ admin đọc (GET .../cham-mau).
        "cham": cham_mau.summary(bdir, detail["pairs"], service.ERROR_THRESHOLD),
        "vote": vote.summary(bdir),
    }


@router.get("/{student}/{book}/vote")
def get_vote(student: str, book: str) -> dict:
    """Kết quả vote OCR từng trang (nặng, tải riêng khi mở tab)."""
    bdir = service.book_dir(_root(), student, book)
    pages = vote.pages(bdir) if bdir else None
    if pages is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Cuốn này chưa có kết quả vote.")
    return {"summary": vote.summary(bdir), "pages": pages}


@router.get("/{student}/{book}/anh/{page}")
def get_page_image(student: str, book: str, page: str) -> FileResponse:
    path = service.page_image(_root(), student, book, page)
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không có ảnh trang.")
    return FileResponse(path)


admin_router = APIRouter(prefix="/api/doi-chieu", tags=["Đối chiếu dóng hàng"])


class SoatRow(BaseModel):
    trang: str = Field(pattern=f"^{service.PAGE_RE.pattern}$")
    han: str = Field(max_length=5000)
    viet: str = Field(max_length=10000)
    bo: bool = False
    # Đánh dấu để chạy bổ sung; không vào TSV. `ma` nối dòng với gợi ý, vì dòng có thể bị ghép, tách, sửa.
    danh_dau: Literal["chua_dich", "ocr"] | None = None
    ghi_chu: str | None = Field(default=None, max_length=500)
    ma: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,40}$")
    bo_goi_y: int | None = Field(default=None, ge=0)


_Page = Annotated[str, StringConstraints(pattern=f"^{service.PAGE_RE.pattern}$")]
_BanTam = Annotated[str, StringConstraints(max_length=500)]
_BanTamViet = Annotated[str, StringConstraints(max_length=1000)]


class SoatDraft(BaseModel):
    rows: list[SoatRow] = Field(max_length=50000)
    da_soat: list[str] = Field(max_length=5000)
    phien_ban: int = Field(ge=0)
    ban_tam: dict[_Page, _BanTam] | None = Field(default=None, max_length=5000)
    ban_tam_viet: dict[_Page, _BanTamViet] | None = Field(default=None, max_length=5000)


class KhungChu(BaseModel):
    c: str = Field(min_length=1, max_length=4)
    b: tuple[int, int, int, int]
    u: int | None = None
    # Ô do người soát chỉnh ("sua") hoặc thêm ("them"); ô máy thì không có.
    n: Literal["sua", "them"] | None = None
    # Người soát gán tay: N là dòng thứ N của trang, 0 là bản tâm; không có thì máy dóng theo chữ.
    d: int | None = Field(default=None, ge=0, le=100000)


class KhungSua(BaseModel):
    chu: list[KhungChu] = Field(max_length=20000)
    ban_tam_chu: list[KhungChu] | None = Field(default=None, max_length=2000)
    phien_ban: int = Field(ge=0)


def _book_dir(student: str, book: str):
    bdir = service.book_dir(_root(), student, book)
    if bdir is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cuốn.")
    return bdir


_SUBMITTED = "Cuốn này đã có bài nộp từ nguồn khác; soát từ bản máy sẽ ghi đè mất bài đó."
_NOT_WRITABLE = "Máy chủ không ghi được vào thư mục dữ liệu đối chiếu."


@admin_router.get("/{student}/{book}/soat")
def get_soat(student: str, book: str, _: AdminUser) -> dict:
    try:
        return soat.load(_book_dir(student, book))
    except soat.SubmittedOutsideDraft as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=_SUBMITTED) from exc


@admin_router.get("/{student}/{book}/soat/khung/{page}")
def get_khung(student: str, book: str, page: str, _: AdminUser) -> dict:
    data = soat.positions(_book_dir(student, book), page)
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Trang này chưa có dữ liệu vị trí chữ.")
    return data


_NO_POSITIONS = "Trang này chưa có dữ liệu vị trí chữ."
_BOX_CONFLICT = "Ô chữ trang này đã được lưu ở nơi khác (tab hoặc máy khác). Tải lại trang rồi làm tiếp."


@admin_router.put("/{student}/{book}/soat/khung/{page}")
def put_khung(student: str, book: str, page: str, payload: KhungSua, user: AdminUser) -> dict:
    chu = [cell.model_dump(exclude_none=True) for cell in payload.chu]
    gutter = None if payload.ban_tam_chu is None else [cell.model_dump(exclude_none=True) for cell in payload.ban_tam_chu]
    try:
        return soat.save_positions(_book_dir(student, book), page, chu, gutter, payload.phien_ban, user.email)
    except soat.NoPositions as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=_NO_POSITIONS) from exc
    except soat.VersionConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=_BOX_CONFLICT) from exc
    except soat.BoxOutsidePage as exc:
        raise HTTPException(422, detail="Có ô chữ nằm ngoài ảnh.") from exc
    except OSError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NOT_WRITABLE) from exc


@admin_router.delete("/{student}/{book}/soat/khung/{page}")
def delete_khung(student: str, book: str, page: str, phien_ban: int, _: AdminUser) -> dict:
    """Khôi phục ô máy; bản đã sửa được giữ lại trong lịch sử."""
    try:
        return soat.restore_positions(_book_dir(student, book), page, phien_ban)
    except soat.NoPositions as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=_NO_POSITIONS) from exc
    except soat.VersionConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=_BOX_CONFLICT) from exc
    except OSError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NOT_WRITABLE) from exc


@admin_router.put("/{student}/{book}/soat")
def put_soat(student: str, book: str, payload: SoatDraft, user: AdminUser) -> dict:
    rows = [row.model_dump(exclude_none=True) for row in payload.rows]
    try:
        return soat.save(
            _book_dir(student, book), rows, payload.da_soat, payload.phien_ban, user.email, payload.ban_tam, payload.ban_tam_viet
        )
    except soat.VersionConflict as exc:
        detail = "Nháp đã được lưu ở nơi khác (tab hoặc máy khác). Tải lại trang rồi làm tiếp."
        raise HTTPException(status.HTTP_409_CONFLICT, detail=detail) from exc
    except soat.SubmittedOutsideDraft as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=_SUBMITTED) from exc
    except OSError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NOT_WRITABLE) from exc


@admin_router.post("/{student}/{book}/soat/nop")
def post_nop(student: str, book: str, _: AdminUser) -> dict:
    try:
        return soat.submit(_book_dir(student, book), book)
    except OSError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NOT_WRITABLE) from exc


_LoaiNhanXet = Literal["OMISSION", "ADDITION", "MISSING", "chu_han", "ten_rieng", "dinh_dang", "bao_cao", "khac"]


class MucNhanXet(BaseModel):
    # Số dòng trong tệp TSV của bài nộp; không có thì là nhận xét chung cho cả bài.
    dong: int | None = Field(default=None, ge=1, le=1000000)
    loai: _LoaiNhanXet = "khac"
    noi_dung: str = Field(min_length=1, max_length=4000)


class NhanXet(BaseModel):
    trang_thai: Literal["nhap", "da_duyet", "da_gui"] = "nhap"
    mo_dau: str = Field(default="", max_length=4000)
    muc: list[MucNhanXet] = Field(default_factory=list, max_length=500)
    ket: str = Field(default="", max_length=4000)
    phien_ban: int = Field(ge=0)


_NHAN_XET_CONFLICT = "Nhận xét đã được lưu ở nơi khác (tab hoặc máy khác). Tải lại trang rồi sửa tiếp."


@admin_router.get("/{student}/{book}/nhan-xet")
def get_nhan_xet(student: str, book: str, _: AdminUser) -> dict:
    return nhan_xet.load(_book_dir(student, book))


@admin_router.put("/{student}/{book}/nhan-xet")
def put_nhan_xet(student: str, book: str, payload: NhanXet, user: AdminUser) -> dict:
    data = payload.model_dump(exclude={"phien_ban"})
    try:
        return nhan_xet.save(_book_dir(student, book), data, payload.phien_ban, user.email)
    except nhan_xet.VersionConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=_NHAN_XET_CONFLICT) from exc
    except OSError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NOT_WRITABLE) from exc


_Verdict = Literal["dung", "OMISSION", "ADDITION", "MISSING"]


class ChamMau(BaseModel):
    # Khoá là số dòng trong TSV của bài nộp (JSON chỉ cho khoá chuỗi; pydantic đổi sang int).
    nhan: dict[int, _Verdict] = Field(max_length=5000)
    phien_ban: int = Field(ge=0)


_CHAM_CONFLICT = "Kết quả chấm đã được lưu ở nơi khác (tab hoặc máy khác). Tải lại trang rồi chấm tiếp."


@admin_router.get("/{student}/{book}/cham-mau")
def get_cham_mau(student: str, book: str, _: AdminUser) -> dict:
    """Nhãn còn khớp bài nộp hiện tại, kèm phiên bản để lưu tiếp."""
    bdir = _book_dir(student, book)
    data = cham_mau.load(bdir)
    pairs = service.load_book(bdir)["pairs"]
    return {
        "nhan": cham_mau.current_verdicts(data, pairs),
        "phien_ban": data.get("phien_ban", 0),
        "nguoi_sua": data.get("nguoi_sua"),
        "luu_luc": data.get("luu_luc"),
    }


@admin_router.put("/{student}/{book}/cham-mau")
def put_cham_mau(student: str, book: str, payload: ChamMau, user: AdminUser) -> dict:
    bdir = _book_dir(student, book)
    pairs = service.load_book(bdir)["pairs"]
    try:
        saved = cham_mau.save(bdir, dict(payload.nhan), pairs, payload.phien_ban, user.email)
    except cham_mau.UnknownLine as exc:
        raise HTTPException(422, detail=f"Dòng {exc.args[0]} không phải cặp hợp lệ của bài nộp hiện tại.") from exc
    except cham_mau.luu_tru.VersionConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=_CHAM_CONFLICT) from exc
    except OSError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NOT_WRITABLE) from exc
    return {
        "nhan": cham_mau.current_verdicts(saved, pairs),
        "phien_ban": saved["phien_ban"],
        "nguoi_sua": saved["nguoi_sua"],
        "luu_luc": saved["luu_luc"],
    }
