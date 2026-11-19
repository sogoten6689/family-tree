"""Tiến độ khung chữ (công khai, chỉ đọc) cho trang /nghien-cuu/tien-do.

Số liệu đếm thẳng từ <cuon>/khung/<trang>.json (ô máy do tools/tao_khung_doi_chieu.py tạo), nên mỗi trang khung
vừa được đẩy lên máy chủ (tools/dong_bo_khung.py) là lần làm mới kế tiếp của web đã thấy. Từng tệp được nhớ theo
(mtime, cỡ) để trang tự làm mới vài giây một lần không phải đọc lại hàng trăm nghìn ô.

Phần "Xong / Đang làm / Chờ quyết" là ghi chú người làm đặt ở <DOI_CHIEU_DIR>/tien_do.json:
{"cap_nhat": "...", "xong": ["..."], "dang_lam": ["..."], "cho_quyet": ["..."]}.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from app.doi_chieu import service

STATUS_NAME = "tien_do.json"
STATUS_KEYS = ("xong", "dang_lam", "cho_quyet")
_page_cache: dict[str, tuple[int, int, dict]] = {}
_lock = Lock()


def _count(path: Path) -> dict | None:
    """Số ô của một trang: chữ có khung, trong đó bao nhiêu ô ước lượng (u=1), và số chữ chưa có khung."""
    st = path.stat()
    key = str(path)
    with _lock:
        hit = _page_cache.get(key)
    if hit and hit[:2] == (st.st_mtime_ns, st.st_size):
        return hit[2]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None  # tệp đang được ghi dở: lần làm mới sau sẽ đọc lại
    cells = [*data.get("chu", []), *((data.get("ban_tam") or {}).get("chu", []))]
    stats = {
        "chu": len(cells),
        "uoc": sum(1 for c in cells if c.get("u")),
        "thieu": int(data.get("thieu", 0)) + int((data.get("ban_tam") or {}).get("thieu", 0)),
    }
    with _lock:
        _page_cache[key] = (st.st_mtime_ns, st.st_size, stats)
    return stats


def book_progress(bdir: Path) -> dict | None:
    """Tiến độ khung của một cuốn; None khi cuốn chưa có trang khung nào."""
    khung = bdir / "khung"
    if not khung.is_dir():
        return None
    files = [p for p in khung.iterdir() if p.suffix == ".json" and service.PAGE_RE.fullmatch(p.stem)]
    if not files:
        return None
    chu = uoc = thieu = pages = 0
    latest = 0.0
    for path in files:
        stats = _count(path)
        if stats is None:
            continue
        pages += 1
        chu += stats["chu"]
        uoc += stats["uoc"]
        thieu += stats["thieu"]
        latest = max(latest, path.stat().st_mtime)
    return {
        "trang_anh": len(service.page_names(bdir)),
        "trang_khung": pages,
        "chu": chu,
        "uoc": uoc,
        "thieu": thieu,
        "cap_nhat": datetime.fromtimestamp(latest, timezone.utc).isoformat(timespec="seconds") if latest else None,
    }


def _status(root: Path) -> dict | None:
    path = root / STATUS_NAME
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    status = {k: [str(x) for x in raw.get(k, []) if isinstance(x, (str, int, float))] for k in STATUS_KEYS}
    cap_nhat = raw.get("cap_nhat")
    status["cap_nhat"] = str(cap_nhat) if cap_nhat else None
    return status


def overview(root: Path | None) -> dict:
    books = []
    if root is not None:
        names = service.catalogue(root)
        for sdir in sorted(p for p in root.iterdir() if p.is_dir() and service.is_slug(p.name)):
            for bdir in sorted(p for p in sdir.iterdir() if p.is_dir() and service.is_slug(p.name)):
                progress = book_progress(bdir)
                if progress is not None:
                    books.append({"student": sdir.name, "book": bdir.name, "ten": names.get(bdir.name, {}).get("ten"), **progress})
    return {
        "luc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "trang_thai": _status(root) if root is not None else None,
        "cuon": books,
    }
