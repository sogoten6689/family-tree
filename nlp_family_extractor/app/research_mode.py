"""Chế độ nghiên cứu (RESEARCH_MODE=1): web chỉ phục vụ nghiên cứu.

Mọi request ghi (không phải GET/HEAD/OPTIONS) bị từ chối, trừ đăng nhập và phần
soát đối chiếu (vẫn đòi quyền admin như cũ). Chặn theo danh sách CHO PHÉP, nên
route ghi thêm sau này mặc định cũng bị khoá — kể cả route gọi dịch vụ tốn phí.
Tắt cờ (mặc định) thì mọi thứ như trước.
"""

import os

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
ALLOWED_WRITE_PATHS = frozenset({"/api/login"})
ALLOWED_WRITE_PREFIXES = ("/api/doi-chieu/",)
BLOCKED_MESSAGE = "Web đang ở chế độ nghiên cứu: tính năng này đã đóng, chỉ xem."


def research_mode() -> bool:
    return os.getenv("RESEARCH_MODE", "").strip().lower() in {"1", "true", "yes"}


def is_blocked(method: str, path: str) -> bool:
    if method.upper() in SAFE_METHODS:
        return False
    return path not in ALLOWED_WRITE_PATHS and not path.startswith(ALLOWED_WRITE_PREFIXES)
