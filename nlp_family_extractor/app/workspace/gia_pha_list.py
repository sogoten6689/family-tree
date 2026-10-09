"""Danh sách Gia phả phía backend: chuẩn hoá tìm kiếm, lọc, phân trang và cache ngắn hạn.

Trước đây backend trả TOÀN BỘ danh sách và frontend tự lọc/cắt trang. Giờ backend làm việc đó
(`GET /api/gia-pha?page=&page_size=&q=&status=&code=&source=`), nên số lượng bộ tăng lên vài
nghìn vẫn gửi mỗi lần chỉ một trang.
"""
from __future__ import annotations

import threading
import time
import unicodedata
from typing import Any, Callable, Dict, Generic, List, Optional, Sequence, TypeVar

T = TypeVar("T")

STATUS_VALUES = {"all", "built", "pending"}
CODE_VALUES = {"all", "has", "none"}
SOURCE_VALUES = {"all", "catalogue", "gemini"}
MAX_PAGE_SIZE = 200


def normalize_for_search(text: str) -> str:
    """Bỏ dấu tiếng Việt, đ→d, chữ thường — khớp đúng với normalizeForSearch ở frontend
    (gõ "phan gia" khớp "Phan gia công phả"); chữ Hán giữ nguyên."""
    decomposed = unicodedata.normalize("NFD", text or "")
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return stripped.replace("đ", "d").replace("Đ", "d").lower().strip()


def filter_items(
    items: Sequence[Any],
    *,
    q: str = "",
    status: str = "all",
    code: str = "all",
    source: str = "all",
) -> List[Any]:
    """Lọc theo từ khoá (mọi từ phải khớp mã/tên/họ) + trạng thái + có/chưa có mã + nguồn mã."""
    terms = [t for t in normalize_for_search(q).split() if t]
    result = []
    for item in items:
        if status != "all" and item.status != status:
            continue
        has_code = not item.ma_dinh_danh_pending
        if code == "has" and not has_code:
            continue
        if code == "none" and has_code:
            continue
        if source != "all" and item.ma_dinh_danh_nguon != source:
            continue
        if terms:
            haystack = normalize_for_search(" ".join([item.id, item.title, item.ho_toc or ""]))
            if not all(term in haystack for term in terms):
                continue
        result.append(item)
    return result


def paginate(items: Sequence[T], page: int, page_size: int) -> List[T]:
    """page bắt đầu từ 1; page_size <= 0 = không phân trang (trả hết, tương thích cũ)."""
    if page_size <= 0:
        return list(items)
    start = (max(page, 1) - 1) * page_size
    return list(items[start : start + page_size])


class TtlCache(Generic[T]):
    """Cache trong bộ nhớ tiến trình, hết hạn theo giây, an toàn đa luồng.
    Dùng cho danh sách chưa lọc theo từng phạm vi (khách / admin / từng user)."""

    def __init__(self, ttl_seconds: float, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._data: Dict[str, tuple[float, T]] = {}

    def get(self, key: str) -> Optional[T]:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            stamp, value = entry
            if self._clock() - stamp > self._ttl:
                del self._data[key]
                return None
            return value

    def set(self, key: str, value: T) -> None:
        with self._lock:
            self._data[key] = (self._clock(), value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


# 20 giây: đủ để lướt/lọc/đổi trang mượt, đủ ngắn cho thay đổi do job nền (engine chạy xong).
# Mọi request ghi (POST/PUT/PATCH/DELETE vào /api/…) thành công sẽ xoá cache ngay (xem api.py).
GIA_PHA_CACHE: TtlCache[list] = TtlCache(ttl_seconds=20)
