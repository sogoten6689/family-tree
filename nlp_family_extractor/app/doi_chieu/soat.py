"""Soát cặp câu ngay trên web (chỉ admin): lưu nháp theo trang, rồi nộp thành TSV.

Nháp nằm ở <cuon>/soat_nhap.json, không được tính vào số liệu đối chiếu. Khi nộp, chỉ những dòng
thuộc trang người soát đã xác nhận mới vào <cuon>/<ma-cuon>_parallel.tsv, để bản máy chưa ai soát
không bao giờ được đếm là cặp hợp lệ. Tệp TSV cũ được giữ lại trong <cuon>/lich_su/.
"""
from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from app.doi_chieu import service

DRAFT_NAME = "soat_nhap.json"
SUGGESTION_NAME = "goi_y.json"
HISTORY_DIR = "lich_su"
_CELL_BREAK_RE = re.compile(r"\s*[\t\r\n]+\s*")
_write_lock = Lock()


class VersionConflict(Exception):
    """Nháp trên máy chủ đã đổi kể từ lúc người soát tải về."""


class SubmittedOutsideDraft(Exception):
    """Cuốn đã có bài nộp từ nguồn khác: bắt đầu nháp từ bản máy sẽ ghi đè mất bài đó."""


def positions(bdir: Path, page: str) -> dict | None:
    """Vị trí chữ của một trang, do tools/tao_khung_doi_chieu.py tạo; chưa có thì None."""
    if not service.PAGE_RE.fullmatch(page):
        return None
    path = bdir / "khung" / f"{page}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _read_draft(bdir: Path) -> dict | None:
    path = bdir / DRAFT_NAME
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _read_suggestions(bdir: Path) -> dict:
    """Gợi ý do tools/bo_sung_danh_dau.py tạo, theo mã dòng. Tệp riêng để không đụng vào bài người soát đang sửa."""
    path = bdir / SUGGESTION_NAME
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def load(bdir: Path) -> dict:
    """Nháp hiện có; chưa có thì dựng từ bản máy, mỗi cột chữ một dòng."""
    draft = _read_draft(bdir)
    if draft is not None:
        return {"ban_tam": {}, **draft, "goi_y": _read_suggestions(bdir)}
    if service.load_book(bdir)["tsv"]:
        raise SubmittedOutsideDraft
    rows = [
        {"trang": r["trang"], "han": r["han"], "viet": r["viet"], "bo": False}
        for r in service.read_machine(bdir / "cap_cau.csv")
    ]
    return {"rows": rows, "da_soat": [], "phien_ban": 0, "ban_tam": {}, "goi_y": _read_suggestions(bdir)}


def save(
    bdir: Path, rows: list[dict], da_soat: list[str], phien_ban: int, nguoi_soat: str, ban_tam: dict[str, str] | None = None
) -> dict:
    """`ban_tam`: chữ bản tâm đã sửa theo trang, không bao giờ vào TSV. None nghĩa là giữ nguyên (trang web bản cũ)."""
    with _write_lock:
        current = _read_draft(bdir)
        if (current["phien_ban"] if current else 0) != phien_ban:
            raise VersionConflict
        if current is None and service.load_book(bdir)["tsv"]:
            raise SubmittedOutsideDraft
        draft = {
            "rows": rows,
            "da_soat": sorted(set(da_soat)),
            "phien_ban": phien_ban + 1,
            "ban_tam": ban_tam if ban_tam is not None else (current or {}).get("ban_tam", {}),
            "nguoi_soat": nguoi_soat,
            "luu_luc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        _write_atomic(bdir / DRAFT_NAME, json.dumps(draft, ensure_ascii=False, indent=1))
    return draft


def _clean_cell(text: str) -> str:
    return _CELL_BREAK_RE.sub(" ", text).strip()


def build_tsv(draft: dict) -> tuple[list[dict], str]:
    """Các dòng sẽ nộp (trang đã xác nhận, không bị bỏ, không rỗng) và nội dung TSV của chúng."""
    confirmed = set(draft["da_soat"])
    kept = []
    for row in draft["rows"]:
        han, viet = _clean_cell(row["han"]), _clean_cell(row["viet"])
        if row["trang"] in confirmed and not row["bo"] and (han or viet):
            kept.append({"trang": row["trang"], "han": han, "viet": viet})
    return kept, "".join(f"{r['han']}\t{r['viet']}\n" for r in kept)


def submit(bdir: Path, book: str) -> dict:
    """Kiểm tra định dạng rồi ghi TSV. Còn lỗi thì không ghi gì, trả về từng dòng lỗi."""
    with _write_lock:
        draft = _read_draft(bdir)
        if draft is None:
            return {"nop": False, "so_cap": 0, "loi": [], "ly_do": "Chưa có nháp đã lưu."}
        kept, text = build_tsv(draft)
        if not kept:
            return {"nop": False, "so_cap": 0, "loi": [], "ly_do": "Chưa có trang nào được xác nhận đã soát."}
        errors = [
            {"trang": row["trang"], "han": row["han"], "viet": row["viet"], "loi": pair.errors}
            for row, pair in zip(kept, service.parse_tsv(text))
            if pair.errors
        ]
        if errors:
            return {"nop": False, "so_cap": len(kept), "loi": errors, "ly_do": "Còn dòng sai định dạng."}

        target = bdir / f"{book}_parallel.tsv"
        old_files = sorted(p for p in bdir.glob("*.tsv") if p.is_file())
        if old_files:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            history = bdir / HISTORY_DIR
            history.mkdir(exist_ok=True)
            for old in old_files:
                shutil.copy2(old, history / f"{old.stem}.{stamp}{old.suffix}")
        _write_atomic(target, text)
        for old in old_files:
            if old != target:
                old.unlink()
    return {"nop": True, "so_cap": len(kept), "loi": [], "ly_do": None, "tsv": target.name}
