from __future__ import annotations

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
