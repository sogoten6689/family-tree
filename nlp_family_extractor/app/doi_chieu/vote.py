"""Kết quả vote OCR (nhiều engine bỏ phiếu theo dòng nền) của một cuốn, chỉ đọc.

File <cuon>/vote.json do công cụ vote ngoài repo sinh ra (vote_dong_v2, chốt 17/11/2026): danh sách trang
  [{"page_id", "nen", "so_phieu", "paddle_khop"?, "trang_soat_tay"?, "dong": [
      {"nen": "<dòng chữ Hán>", "chu": [{"vi_tri", "nen", "phieu": {chữ: số phiếu}, "kq"}]}   # dòng ≥ 3 chữ
      {"nen": "<dòng ngắn>", "kq": "dong_y" | "soat_tay_dong_ngan" | "mot_phieu"}              # dòng < 3 chữ
  ]}]
Dòng dài chỉ liệt kê chữ khác "dong_y"; chữ không liệt kê là mọi phiếu đồng ý.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

FILE_NAME = "vote.json"
KINDS = ("dong_y", "de_xuat_sua", "can_soat", "soat_tay_dong_ngan", "mot_phieu")


def _path(bdir: Path) -> Path:
    return bdir / FILE_NAME


@lru_cache(maxsize=64)
def _read(path: str, mtime_ns: int, size: int) -> tuple[list[dict], dict]:
    pages = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(pages, list):
        raise ValueError("vote.json phải là danh sách trang")
    return pages, _summarize(pages)


def _load(bdir: Path) -> tuple[list[dict], dict] | None:
    path = _path(bdir)
    try:
        st = path.stat()
        return _read(str(path), st.st_mtime_ns, st.st_size)
    except (OSError, ValueError):
        return None


def _summarize(pages: list[dict]) -> dict:
    chars = dict.fromkeys(KINDS, 0)
    pages_review = 0
    for page in pages:
        if page.get("trang_soat_tay"):
            pages_review += 1
        for line in page.get("dong") or []:
            text = line.get("nen") or ""
            if "kq" in line:
                kind = line["kq"] if line["kq"] in chars else "can_soat"
                chars[kind] += len(text)
                continue
            flagged = line.get("chu") or []
            for c in flagged:
                kind = c.get("kq") if c.get("kq") in chars else "can_soat"
                chars[kind] += 1
            chars["dong_y"] += max(0, len(text) - len(flagged))
    total = sum(chars.values())
    voted = total - chars["mot_phieu"]
    return {
        "pages": len(pages),
        "pages_review": pages_review,
        "chars": total,
        **chars,
        # Tỷ lệ đồng ý chỉ tính trên chữ có ≥ 2 phiếu.
        "agree_rate": round(chars["dong_y"] / voted, 4) if voted else None,
    }


def summary(bdir: Path) -> dict | None:
    loaded = _load(bdir)
    return loaded[1] if loaded else None


def pages(bdir: Path) -> list[dict] | None:
    loaded = _load(bdir)
    return loaded[0] if loaded else None
