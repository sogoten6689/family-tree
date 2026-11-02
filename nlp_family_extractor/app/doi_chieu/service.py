"""Đọc thư mục đối chiếu, kiểm tra định dạng TSV theo Guideline CV và ghép bản máy theo chữ Hán.

Bố cục thư mục (không nằm trong git, đặt qua biến môi trường DOI_CHIEU_DIR):

    <DOI_CHIEU_DIR>/danh_muc.json                    {"<ma-cuon>": {"ten", "link"}}  (tuỳ chọn)
    <DOI_CHIEU_DIR>/<sinh-vien>/meta.json            {"ten": "Họ tên"}  (tuỳ chọn)
    <DOI_CHIEU_DIR>/<sinh-vien>/<ma-cuon>/*.tsv      bài nộp: <Hán>\t<Việt> mỗi dòng
    <DOI_CHIEU_DIR>/<sinh-vien>/<ma-cuon>/cap_cau.csv  bản máy từ gói lab (mỗi dòng một cột chữ)
    <DOI_CHIEU_DIR>/<sinh-vien>/<ma-cuon>/anh/<trang>.jpg  ảnh trang (tuỳ chọn)

Bản máy được ghép với bài nộp bằng cách dóng chuỗi chữ Hán của hai bên (difflib), không dựa vào
số thứ tự dòng: mỗi cặp của sinh viên nhận các cột máy có chữ Hán trùng với vế Hán của cặp đó.
"""
from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from threading import Lock

TARGET_PAIRS = 2000
ERROR_THRESHOLD = 0.30
MIN_BLOCK = 3

SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
PAGE_RE = re.compile(r"[0-9A-Za-z_-]{1,20}")
IMAGE_EXTS = (".jpg", ".jpeg", ".png")
HAN_RE = re.compile(r"[㐀-䶿一-鿿豈-﫿\U00020000-\U0003ffff]")
_cache: dict[tuple, dict] = {}
_cache_lock = Lock()


def data_dir() -> Path | None:
    raw = os.getenv("DOI_CHIEU_DIR")
    if not raw:
        default = Path(__file__).resolve().parents[2] / "data" / "doi_chieu"
        return default if default.is_dir() else None
    path = Path(raw)
    return path if path.is_dir() else None


def is_slug(value: str) -> bool:
    return bool(SLUG_RE.match(value)) and ".." not in value


def han_only(text: str) -> str:
    return "".join(HAN_RE.findall(text))


@dataclass
class Pair:
    line: int
    han: str
    viet: str
    errors: list[str] = field(default_factory=list)


def parse_tsv(text: str) -> list[Pair]:
    """Kiểm tra từng dòng theo Guideline CV mục 3: đúng một tab, không vế rỗng,
    vế Hán có chữ Hán, vế Việt không lẫn chữ Hán, không trùng cặp."""
    pairs: list[Pair] = []
    seen: dict[tuple[str, str], int] = {}
    for i, raw in enumerate(text.lstrip("﻿").splitlines(), 1):
        if not raw.strip():
            continue
        parts = raw.split("\t")
        if len(parts) != 2:
            pairs.append(Pair(i, raw.strip(), "", [f"có {len(parts) - 1} tab, cần đúng 1"]))
            continue
        han, viet = parts[0].strip(), parts[1].strip()
        pair = Pair(i, han, viet)
        if not han or not viet:
            pair.errors.append("thiếu một vế")
        if han and not HAN_RE.search(han):
            pair.errors.append("vế Hán không có chữ Hán")
        if HAN_RE.search(viet):
            pair.errors.append("vế Việt lẫn chữ Hán")
        key = (han, viet)
        if key in seen:
            pair.errors.append(f"trùng dòng {seen[key]}")
        else:
            seen[key] = i
        pairs.append(pair)
    return pairs


def read_machine(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f)]
    return [
        {"trang": r.get("trang", ""), "dong": r.get("dong", ""), "han": r.get("han", ""), "viet": r.get("viet_may", "")}
        for r in rows
    ]


def align(pairs: list[Pair], machine: list[dict]) -> tuple[list[dict], list[int]]:
    """Dóng chuỗi chữ Hán sinh viên với chuỗi chữ Hán OCR.

    Trả về, cho từng cặp: các cột máy chạm tới, tỷ lệ chữ Hán của cặp tìm thấy trong OCR;
    và danh sách chỉ số cột máy không cặp nào chạm tới (ứng viên thiếu – MISSING).
    """
    s_chars: list[int] = []  # chỉ số cặp của từng chữ Hán sinh viên
    s_text = []
    for idx, p in enumerate(pairs):
        h = han_only(p.han)
        s_text.append(h)
        s_chars.extend([idx] * len(h))
    m_chars: list[int] = []
    m_text = []
    for idx, r in enumerate(machine):
        h = han_only(r["han"])
        m_text.append(h)
        m_chars.extend([idx] * len(h))

    hits: list[dict[int, int]] = [{} for _ in pairs]
    matched = [0] * len(pairs)
    touched: set[int] = set()
    if s_chars and m_chars:
        sm = SequenceMatcher(None, "".join(s_text), "".join(m_text), autojunk=False)
        for a, b, size in sm.get_matching_blocks():
            if size < MIN_BLOCK:  # khối 1–2 chữ thường là chữ hay gặp (之, 公) khớp nhầm chỗ khác
                continue
            for k in range(size):
                p_idx, m_idx = s_chars[a + k], m_chars[b + k]
                hits[p_idx][m_idx] = hits[p_idx].get(m_idx, 0) + 1
                matched[p_idx] += 1
                touched.add(m_idx)

    result = []
    for idx, p in enumerate(pairs):
        n = len(han_only(p.han))
        rows = sorted(hits[idx])
        result.append({"rows": rows, "coverage": round(matched[idx] / n, 3) if n else 0.0})
    missing = [i for i, t in enumerate(m_text) if t and i not in touched]
    return result, missing


def _student_tsv(book_dir: Path) -> Path | None:
    files = sorted(p for p in book_dir.glob("*.tsv") if p.is_file())
    return files[0] if files else None


def _signature(book_dir: Path) -> tuple:
    parts = []
    for p in [_student_tsv(book_dir), book_dir / "cap_cau.csv"]:
        if p and p.is_file():
            st = p.stat()
            parts.append((p.name, st.st_mtime_ns, st.st_size))
    return (str(book_dir), tuple(parts))


def load_book(book_dir: Path) -> dict:
    """Kết quả đầy đủ của một cuốn; lưu đệm theo mtime để không dóng lại mỗi lần xem."""
    sig = _signature(book_dir)
    with _cache_lock:
        if sig in _cache:
            return _cache[sig]

    tsv = _student_tsv(book_dir)
    pairs = parse_tsv(tsv.read_text(encoding="utf-8")) if tsv else []
    machine = read_machine(book_dir / "cap_cau.csv")
    links, missing = align(pairs, machine)

    out_pairs = []
    for p, link in zip(pairs, links):
        rows = [machine[i] for i in link["rows"]]
        out_pairs.append(
            {
                "line": p.line,
                "han": p.han,
                "viet": p.viet,
                "errors": p.errors,
                "may_han": "".join(r["han"] for r in rows),
                "may_viet": " ".join(r["viet"].strip() for r in rows if r["viet"].strip()),
                "trang": sorted({r["trang"] for r in rows if r["trang"]}),
                "coverage": link["coverage"],
            }
        )
    m_total = sum(len(han_only(r["han"])) for r in machine)
    m_missing = sum(len(han_only(machine[i]["han"])) for i in missing)
    book = {
        "tsv": tsv.name if tsv else None,
        "pairs": out_pairs,
        "missing": [machine[i] | {"index": i} for i in missing],
        "stats": {
            "pairs": len(pairs),
            "valid": sum(1 for p in pairs if not p.errors),
            "format_errors": sum(1 for p in pairs if p.errors),
            "machine_rows": len(machine),
            "machine_pages": len({r["trang"] for r in machine if r["trang"]}),
            # Tỷ lệ chữ Hán OCR của cuốn đã có cặp sinh viên phủ tới.
            "ocr_coverage": round(1 - m_missing / m_total, 3) if m_total else None,
        },
    }
    with _cache_lock:
        _cache[sig] = book
    return book


def _student_name(student_dir: Path) -> str:
    meta = student_dir / "meta.json"
    if meta.is_file():
        try:
            name = json.loads(meta.read_text(encoding="utf-8")).get("ten")
            if isinstance(name, str) and name.strip():
                return name.strip()
        except (ValueError, OSError):
            pass
    return student_dir.name


def catalogue(root: Path) -> dict[str, dict]:
    """Tên đầy đủ và link bản gốc của từng cuốn, đọc từ <root>/danh_muc.json:
    {"<ma-cuon>": {"ten": "...", "link": "https://..."}}. Thiếu tệp hoặc hỏng → {}."""
    path = root / "danh_muc.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    out = {}
    for key, item in data.items():
        if not isinstance(item, dict):
            continue
        link = item.get("link")
        out[key] = {
            "ten": item.get("ten") if isinstance(item.get("ten"), str) else None,
            "link": link if isinstance(link, str) and link.startswith("https://") else None,
        }
    return out


def book_info(root: Path, book: str) -> dict:
    return catalogue(root).get(book, {"ten": None, "link": None})


def overview(root: Path) -> dict:
    students = []
    names = catalogue(root)
    for sdir in sorted(p for p in root.iterdir() if p.is_dir() and is_slug(p.name)):
        books = []
        for bdir in sorted(p for p in sdir.iterdir() if p.is_dir() and is_slug(p.name)):
            book = load_book(bdir)
            info = names.get(bdir.name, {"ten": None, "link": None})
            books.append(
                {"id": bdir.name, **info, "tsv": book["tsv"], **book["stats"], "image_pages": len(page_names(bdir))}
            )
        valid = sum(b["valid"] for b in books)
        students.append(
            {
                "id": sdir.name,
                "ten": _student_name(sdir),
                "books": books,
                "valid": valid,
                "pairs": sum(b["pairs"] for b in books),
                "format_errors": sum(b["format_errors"] for b in books),
                "submitted": sum(1 for b in books if b["tsv"]),
            }
        )
    return {"target": TARGET_PAIRS, "error_threshold": ERROR_THRESHOLD, "students": students}


def book_dir(root: Path, student: str, book: str) -> Path | None:
    if not (is_slug(student) and is_slug(book)):
        return None
    path = root / student / book
    return path if path.is_dir() else None


def page_names(bdir: Path) -> list[str]:
    """Tên các trang có ảnh, để xem ảnh cả khi cuốn chưa có bản máy."""
    anh = bdir / "anh"
    if not anh.is_dir():
        return []
    return sorted(p.stem for p in anh.iterdir() if p.suffix.lower() in IMAGE_EXTS and PAGE_RE.fullmatch(p.stem))


def page_image(root: Path, student: str, book: str, page: str) -> Path | None:
    bdir = book_dir(root, student, book)
    if bdir is None or not PAGE_RE.fullmatch(page):
        return None
    for ext in IMAGE_EXTS:
        path = bdir / "anh" / f"{page}{ext}"
        if path.is_file():
            return path
    return None
