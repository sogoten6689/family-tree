"""Thống kê tóm tắt cho trang Gia phả và Tổng quan: gộp số liệu từ danh sách Gia phả (đã cache)
và vài truy vấn tổng hợp SQL, rồi cache ngắn hạn. Không đọc nội dung văn bản nặng."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Sequence

from app.workspace.gia_pha_list import GIA_PHA_CACHE, TtlCache

# 30 giây cho số liệu tổng hợp (đổi chậm hơn danh sách). Cùng cơ chế xoá khi có request ghi.
STATS_CACHE: TtlCache[Any] = TtlCache(ttl_seconds=30)

TOP_HO_TOC = 8


def invalidate_all() -> None:
    """Gọi sau mọi request ghi thành công (api.py): xoá cả cache danh sách lẫn cache thống kê."""
    GIA_PHA_CACHE.clear()
    STATS_CACHE.clear()


def percent(part: int, total: int) -> float:
    return round(100.0 * part / total, 1) if total > 0 else 0.0


def summarize_items(items: Sequence[Any]) -> Dict[str, Any]:
    """Đếm theo trạng thái dựng cây, có/chưa có mã định danh (và nguồn mã), cây công khai,
    tổng số nhân vật và các họ tộc nhiều bộ nhất — từ danh sách GiaPhaItem chưa lọc."""
    built = sum(1 for i in items if i.status == "built")
    with_code = sum(1 for i in items if not i.ma_dinh_danh_pending)
    sources = Counter(i.ma_dinh_danh_nguon for i in items if not i.ma_dinh_danh_pending)
    ho = Counter((i.ho_toc or "").strip() for i in items if (i.ho_toc or "").strip())
    return {
        "total": len(items),
        "built": built,
        "pending": len(items) - built,
        "with_code": with_code,
        "without_code": len(items) - with_code,
        "code_source": {
            "catalogue": sources.get("catalogue", 0),
            "gemini": sources.get("gemini", 0),
            "other": with_code - sources.get("catalogue", 0) - sources.get("gemini", 0),
        },
        "public_trees": sum(1 for i in items if i.is_public),
        "nodes": sum(int(i.node_count or 0) for i in items),
        "top_ho_toc": [{"ho_toc": name, "count": count} for name, count in ho.most_common(TOP_HO_TOC)],
    }


def page_progress(raw: Dict[str, int]) -> Dict[str, Any]:
    """Từ tổng trang và số trang đã có OCR/phiên âm/dịch (ước tính theo bộ) → phần trăm."""
    pages = int(raw.get("pages", 0))
    return {
        "scans": int(raw.get("scans", 0)),
        "pages": pages,
        "ocr_pages": int(raw.get("ocr_pages", 0)),
        "transliteration_pages": int(raw.get("transliteration_pages", 0)),
        "translation_pages": int(raw.get("translation_pages", 0)),
        "ocr_percent": percent(int(raw.get("ocr_pages", 0)), pages),
        "transliteration_percent": percent(int(raw.get("transliteration_pages", 0)), pages),
        "translation_percent": percent(int(raw.get("translation_pages", 0)), pages),
    }


def top_list(counter: Dict[str, int], limit: int = TOP_HO_TOC) -> List[Dict[str, Any]]:
    return [{"name": k, "count": v} for k, v in sorted(counter.items(), key=lambda kv: -kv[1])[:limit]]
