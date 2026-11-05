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
GUTTER_TRANSLATION_NAME = "ban_tam_dich.json"
HISTORY_DIR = "lich_su"
BOX_EDIT_DIR = "khung_sua"
BOX_ADDED = "them"
_CELL_BREAK_RE = re.compile(r"\s*[\t\r\n]+\s*")
_write_lock = Lock()


class VersionConflict(Exception):
    """Nháp trên máy chủ đã đổi kể từ lúc người soát tải về."""


class SubmittedOutsideDraft(Exception):
    """Cuốn đã có bài nộp từ nguồn khác: bắt đầu nháp từ bản máy sẽ ghi đè mất bài đó."""


class NoPositions(Exception):
    """Trang chưa có dữ liệu vị trí chữ của máy nên chưa biết kích thước ảnh."""


class BoxOutsidePage(Exception):
    """Ô chữ nằm ngoài ảnh hoặc có toạ độ ngược."""


def _machine_positions(bdir: Path, page: str) -> dict | None:
    if not service.PAGE_RE.fullmatch(page):
        return None
    path = bdir / "khung" / f"{page}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _box_edit_path(bdir: Path, page: str) -> Path:
    return bdir / BOX_EDIT_DIR / f"{page}.json"


def _read_box_edit(bdir: Path, page: str) -> dict | None:
    path = _box_edit_path(bdir, page)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _still_missing(machine_missing: int, cells: list[dict]) -> int:
    """Ô người thêm là chữ máy chưa định vị được, nên số chữ còn thiếu giảm theo."""
    return max(0, machine_missing - sum(cell.get("n") == BOX_ADDED for cell in cells))


def _apply_box_edit(machine: dict, edit: dict | None) -> dict:
    """Ô người soát đã sửa thay cho ô máy; tệp của máy giữ nguyên để khôi phục và tạo lại không mất bài."""
    if edit is None:
        return machine
    merged = {
        **machine,
        "chu": edit["chu"],
        "thieu": _still_missing(machine.get("thieu", 0), edit["chu"]),
        "da_sua": True,
        "phien_ban": edit["phien_ban"],
        "nguoi_soat": edit["nguoi_soat"],
        "luu_luc": edit["luu_luc"],
    }
    gutter = machine.get("ban_tam")
    if gutter and edit.get("ban_tam_chu") is not None:
        cells = edit["ban_tam_chu"]
        merged["ban_tam"] = {**gutter, "chu": cells, "thieu": _still_missing(gutter.get("thieu", 0), cells)}
    return merged


def positions(bdir: Path, page: str) -> dict | None:
    """Vị trí chữ của một trang: ô máy do tools/tao_khung_doi_chieu.py tạo, cộng phần người soát đã sửa; chưa có thì None."""
    machine = _machine_positions(bdir, page)
    return None if machine is None else _apply_box_edit(machine, _read_box_edit(bdir, page))


def _check_boxes(cells: list[dict], width: int, height: int) -> None:
    for cell in cells:
        x0, y0, x1, y1 = cell["b"]
        if not (0 <= x0 <= x1 <= width and 0 <= y0 <= y1 <= height):
            raise BoxOutsidePage


def save_positions(
    bdir: Path, page: str, chu: list[dict], ban_tam_chu: list[dict] | None, phien_ban: int, nguoi_soat: str
) -> dict:
    with _write_lock:
        machine = _machine_positions(bdir, page)
        if machine is None:
            raise NoPositions
        current = _read_box_edit(bdir, page)
        if (current["phien_ban"] if current else 0) != phien_ban:
            raise VersionConflict
        _check_boxes([*chu, *(ban_tam_chu or [])], machine["rong"], machine["cao"])
        edit = {
            "chu": chu,
            "ban_tam_chu": ban_tam_chu,
            "phien_ban": phien_ban + 1,
            "nguoi_soat": nguoi_soat,
            "luu_luc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        path = _box_edit_path(bdir, page)
        path.parent.mkdir(exist_ok=True)
        _write_atomic(path, json.dumps(edit, ensure_ascii=False, indent=1))
    return _apply_box_edit(machine, edit)


def restore_positions(bdir: Path, page: str, phien_ban: int) -> dict:
    """Quay về ô máy. Bản đã sửa được chuyển vào khung_sua/lich_su/, không xoá."""
    with _write_lock:
        machine = _machine_positions(bdir, page)
        if machine is None:
            raise NoPositions
        current = _read_box_edit(bdir, page)
        if (current["phien_ban"] if current else 0) != phien_ban:
            raise VersionConflict
        if current is not None:
            history = bdir / BOX_EDIT_DIR / HISTORY_DIR
            history.mkdir(exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            os.replace(_box_edit_path(bdir, page), history / f"{page}_{stamp}_v{phien_ban}.json")
    return machine


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


def machine_gutters(bdir: Path) -> dict[str, dict]:
    """Bản tâm máy đọc theo trang (khung/<trang>.json), kèm bản dịch soạn sẵn ở ban_tam_dich.json nếu có."""
    path = bdir / GUTTER_TRANSLATION_NAME
    translations = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    gutters = {}
    for page_file in sorted((bdir / "khung").glob("*.json")):
        page = page_file.stem
        text = (_machine_positions(bdir, page) or {}).get("ban_tam", {}).get("text")
        if text:
            gutters[page] = {"han": text, **({"viet": translations[page]} if translations.get(page) else {})}
    return gutters


def load(bdir: Path) -> dict:
    """Nháp hiện có; chưa có thì dựng từ bản máy, mỗi cột chữ một dòng."""
    draft = _read_draft(bdir)
    if draft is not None:
        return {
            "ban_tam": {},
            "ban_tam_viet": {},
            **draft,
            "ban_tam_may": machine_gutters(bdir),
            "goi_y": _read_suggestions(bdir),
        }
    if service.load_book(bdir)["tsv"]:
        raise SubmittedOutsideDraft
    rows = [
        {"trang": r["trang"], "han": r["han"], "viet": r["viet"], "bo": False}
        for r in service.read_machine(bdir / "cap_cau.csv")
    ]
    return {
        "rows": rows,
        "da_soat": [],
        "phien_ban": 0,
        "ban_tam": {},
        "ban_tam_viet": {},
        "ban_tam_may": machine_gutters(bdir),
        "goi_y": _read_suggestions(bdir),
    }


def save(
    bdir: Path,
    rows: list[dict],
    da_soat: list[str],
    phien_ban: int,
    nguoi_soat: str,
    ban_tam: dict[str, str] | None = None,
    ban_tam_viet: dict[str, str] | None = None,
) -> dict:
    """`ban_tam`, `ban_tam_viet`: chữ bản tâm và bản dịch đã sửa theo trang. None nghĩa là giữ nguyên (trang web bản cũ)."""
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
            "ban_tam_viet": ban_tam_viet if ban_tam_viet is not None else (current or {}).get("ban_tam_viet", {}),
            "nguoi_soat": nguoi_soat,
            "luu_luc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        _write_atomic(bdir / DRAFT_NAME, json.dumps(draft, ensure_ascii=False, indent=1))
    return draft


def _clean_cell(text: str) -> str:
    return _CELL_BREAK_RE.sub(" ", text).strip()


def _gutter_pair(draft: dict, machine: dict[str, dict], page: str) -> dict | None:
    """Cặp bản tâm của một trang. Chưa có đủ hai vế thì chưa thành cặp, nên cuốn chưa dịch bản tâm vẫn nộp được."""
    base = machine.get(page, {})
    han = _clean_cell(draft.get("ban_tam", {}).get(page, base.get("han", "")))
    viet = _clean_cell(draft.get("ban_tam_viet", {}).get(page, base.get("viet", "")))
    return {"trang": page, "han": han, "viet": viet} if han and viet else None


def build_tsv(draft: dict, gutters: dict[str, dict] | None = None) -> tuple[list[dict], str]:
    """Các dòng sẽ nộp (trang đã xác nhận, không bị bỏ, không rỗng) và nội dung TSV của chúng; cặp bản tâm đứng đầu trang."""
    confirmed = set(draft["da_soat"])
    gutters = gutters or {}
    kept = []
    seen = set()

    def add_gutter(page: str) -> None:
        seen.add(page)
        pair = _gutter_pair(draft, gutters, page)
        if pair:
            kept.append(pair)

    for row in draft["rows"]:
        han, viet = _clean_cell(row["han"]), _clean_cell(row["viet"])
        if row["trang"] in confirmed and not row["bo"] and (han or viet):
            if row["trang"] not in seen:
                add_gutter(row["trang"])
            kept.append({"trang": row["trang"], "han": han, "viet": viet})
    for page in sorted(confirmed - seen):
        add_gutter(page)
    return kept, "".join(f"{r['han']}\t{r['viet']}\n" for r in kept)


def submit(bdir: Path, book: str) -> dict:
    """Kiểm tra định dạng rồi ghi TSV. Còn lỗi thì không ghi gì, trả về từng dòng lỗi."""
    with _write_lock:
        draft = _read_draft(bdir)
        if draft is None:
            return {"nop": False, "so_cap": 0, "loi": [], "ly_do": "Chưa có nháp đã lưu."}
        kept, text = build_tsv(draft, machine_gutters(bdir))
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
