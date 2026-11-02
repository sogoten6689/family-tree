from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.doi_chieu import service

# Công khai, không cần đăng nhập (theo yêu cầu): chỉ đọc, không có endpoint ghi.
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
    bdir = service.book_dir(_root(), student, book)
    if bdir is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cuốn.")
    return {"student": student, "book": book, **service.load_book(bdir)}


@router.get("/{student}/{book}/anh/{page}")
def get_page_image(student: str, book: str, page: str) -> FileResponse:
    path = service.page_image(_root(), student, book, page)
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không có ảnh trang.")
    return FileResponse(path)
