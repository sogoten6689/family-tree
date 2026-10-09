from __future__ import annotations

import uuid
from pathlib import PurePosixPath

# Ảnh từng trang của bộ gia phả trên MinIO. Key ổn định theo scan + số trang
# (không phụ thuộc đường dẫn nguồn): gia-pha/{scan_id}/pages/{trang:03d}{.ext}.
# Trước khi upload, gia_pha_page.image_file_key chỉ là đường dẫn tương đối
# trong repo (vd data/00_raw/hannom/.../001.jpg) — không hiển thị được.

KEY_PREFIX = "gia-pha/"

CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


def is_storage_key(key: str | None) -> bool:
    return bool(key) and key.startswith(KEY_PREFIX)


def page_image_key(scan_id: int, page_number: int, source_path: str) -> str:
    ext = PurePosixPath(source_path).suffix.lower() or ".jpg"
    return f"{KEY_PREFIX}{scan_id}/pages/{page_number:03d}{ext}"


def content_type_for(path: str) -> str | None:
    return CONTENT_TYPES.get(PurePosixPath(path).suffix.lower())


def sniff_image(data: bytes) -> tuple[str, str] | None:
    """(đuôi, content-type) theo chữ ký đầu file — không tin tên/đuôi người dùng gửi."""
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp", "image/webp"
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return ".tif", "image/tiff"
    return None


def replacement_image_key(scan_id: int, page_number: int, ext: str) -> str:
    """Key MỚI cho ảnh thay thế (có hậu tố ngẫu nhiên) — không đè object cũ nên
    còn hoàn tác được, và link tạm/cache trình duyệt của ảnh cũ không lẫn."""
    return f"{KEY_PREFIX}{scan_id}/pages/{page_number:03d}-{uuid.uuid4().hex[:8]}{ext}"
