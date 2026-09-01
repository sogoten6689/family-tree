#!/usr/bin/env python3
"""Scan local Hán-Nôm books and write data/00_raw/hannom/books_catalog.json.

From repo root:

  python nlp_family_extractor/tools/build_hannom_catalog.py
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZipFile
import xml.etree.ElementTree as ET

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
CJK_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\U00020000-\U0002eeef]")
W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

CLAN_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("chu", ("chu tộc", "朱族")),
    ("le", ("lê tộc", "黎族", "黎氏")),
    ("doan", ("đoàn", "段族", "段譜")),
    ("pham", ("phạm", "họ phạm", "范氏", "范族")),
    ("nguyen", ("nguyễn", "阮族", "阮堂", "阮文")),
    ("giang", ("giang", "江氏")),
    ("dang", ("đặng", "鄧")),
    ("mai", ("mai thị", "梅氏")),
    ("la", ("là thị", "罗氏", "羅氏")),
    ("tran", ("trần thị", "họ trần", "gia phả họ trần", "陈氏", "陳氏")),
    ("thuy_ung", ("thuỵ ứng", "瑞應")),
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def count_images(folder: Path) -> int:
    if not folder.is_dir():
        return 0
    return sum(1 for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)


def split_nom_title(title: str) -> tuple[str, str]:
    cleaned = (title or "").strip().strip("[]")
    if "|" in cleaned:
        han, vn = (part.strip(" []") for part in cleaned.split("|", 1))
        return han, vn
    return "", cleaned


def clan_key(*parts: str) -> str:
    blob = " ".join(parts).lower()
    for key, needles in CLAN_RULES:
        if any(n.lower() in blob for n in needles):
            return key
    return "unknown"


def fold_name(name: str) -> str:
    nfd = unicodedata.normalize("NFD", name).lower()
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def find_named_dir(parent: Path, *needles: str) -> Path | None:
    if not parent.is_dir():
        return None
    for path in parent.iterdir():
        if not path.is_dir():
            continue
        key = fold_name(path.name)
        if all(token in key for token in needles):
            return path
    return None


def count_digit_stem_images(folder: Path) -> int:
    if not folder.is_dir():
        return 0
    return sum(
        1
        for path in folder.iterdir()
        if path.is_file()
        and path.suffix.lower() in IMAGE_SUFFIXES
        and re.fullmatch(r"\d+", path.stem)
    )


def count_jpg_exclude_paren1(folder: Path) -> tuple[int, int]:
    """Return (unique_source_jpg, paren1_dupes) in a folder (not recursive)."""
    if not folder.is_dir():
        return 0, 0
    total = 0
    dupes = 0
    for path in folder.iterdir():
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if re.search(r"\(\s*1\s*\)", path.name, re.I):
            dupes += 1
            continue
        total += 1
    return total, dupes


def read_docx_paras(path: Path) -> list[str]:
    with ZipFile(path) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
    paras: list[str] = []
    for p in root.iter(f"{W_NS}p"):
        text = "".join((t.text or "") for t in p.iter(f"{W_NS}t")).strip()
        if text:
            paras.append(unicodedata.normalize("NFC", text))
    return paras


def read_docx_app_props(path: Path) -> dict[str, str]:
    props: dict[str, str] = {}
    with ZipFile(path) as zf:
        if "docProps/app.xml" not in zf.namelist():
            return props
        root = ET.fromstring(zf.read("docProps/app.xml"))
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag in ("Pages", "Words", "Characters", "Paragraphs", "Lines") and el.text:
            props[tag.lower()] = el.text
    return props


def text_stats(paras: list[str]) -> dict[str, Any]:
    blob = "\n".join(paras)
    cjk = CJK_RE.findall(blob)
    n_cjk = len(cjk)
    return {
        "paras": len(paras),
        "chars": len(blob),
        "cjk_chars": n_cjk,
        "unique_cjk": len(set(cjk)),
        "cjk_ratio": round(n_cjk / max(len(blob), 1), 4),
        "latin_letters": len(re.findall(r"[A-Za-zÀ-ỹ]", blob)),
    }


def pdf_page_count(path: Path) -> int | None:
    try:
        from pypdf import PdfReader  # type: ignore

        return len(PdfReader(str(path)).pages)
    except Exception:
        pass
    try:
        import pypdfium2 as pdfium  # type: ignore

        doc = pdfium.PdfDocument(str(path))
        n = len(doc)
        doc.close()
        return n
    except Exception:
        return None


def nom_books(repo: Path) -> list[dict[str, Any]]:
    catalog = load_json(repo / "data/00_raw/hannom/nomfoundation/catalog.json") or {}
    volumes_root = repo / "data/00_raw/hannom/nomfoundation/volumes"
    review_root = repo / "data/03_derived/review_corpus/hannom"
    books: list[dict[str, Any]] = []
    for item in catalog.get("volumes") or []:
        vid = int(item.get("volume_id") or 0)
        meta = load_json(volumes_root / str(vid) / "metadata.json") or {}
        raw_title = str(item.get("title") or meta.get("title") or "")
        title_han = item.get("title_han") or meta.get("title_han") or ""
        title_vn = item.get("title_vn") or meta.get("title_vn") or ""
        if "|" in raw_title:
            han, vn = split_nom_title(raw_title)
            title_han = title_han or han
            title_vn = title_vn or vn
        elif not title_vn:
            title_vn = re.sub(r"^\[|\]$", "", raw_title).strip()
        cat_pages = item.get("page_count")
        if cat_pages is None:
            cat_pages = meta.get("page_count")
        jpg_src = count_images(volumes_root / str(vid) / "pages") or count_images(volumes_root / str(vid))
        jpg_review = count_images(review_root / str(vid) / "pages") or count_images(review_root / str(vid))
        pages_dir = volumes_root / str(vid) / "pages"
        if not pages_dir.is_dir():
            pages_dir = volumes_root / str(vid)
        paddle_dir = volumes_root / str(vid) / "paddleocr"
        dich_dir = volumes_root / str(vid) / "dich"
        n_pad = len(list(paddle_dir.glob("*-paddleocr.json"))) if paddle_dir.is_dir() else 0
        n_dich = len(list(dich_dir.glob("*-dich.md"))) if dich_dir.is_dir() else 0
        n_lab = len(list(pages_dir.glob("*-ocr-raw.json"))) if pages_dir.is_dir() else 0
        jpg = jpg_src or jpg_review
        flags: list[str] = []
        if jpg == 0:
            flags.append("missing_pages")
        if cat_pages not in (None, 0) and jpg and int(cat_pages) != jpg:
            flags.append("mismatch")
        kind = "su_lieu" if vid == 130 else "gia_pha"
        books.append(
            {
                "book_id": f"nom-{vid}",
                "source": "nomfoundation",
                "volume_id": vid,
                "collection_id": item.get("collection_id") or meta.get("collection_id"),
                "title_han": title_han,
                "title_vn": re.sub(r"^\[|\]$", "", title_vn).strip(),
                "clan_key": "—" if kind == "su_lieu" else clan_key(title_han, title_vn),
                "kind": kind,
                "loai": [],
                "layout_tags": [],
                "language": "han",
                "script_hint": "unknown",
                "catalog_code": item.get("catalog_code") or meta.get("catalog_code") or "",
                "page_count": jpg if jpg else int(cat_pages or 0),
                "page_count_catalog": cat_pages,
                "jpg_source": jpg_src,
                "jpg_review": jpg_review,
                "page_count_source": "jpg_count" if jpg else "metadata",
                "flags": flags,
                "paths": {
                    "root": f"data/00_raw/hannom/nomfoundation/volumes/{vid}",
                    "pages": f"data/00_raw/hannom/nomfoundation/volumes/{vid}/pages",
                    "review": f"data/03_derived/review_corpus/hannom/{vid}",
                    "url": item.get("url") or meta.get("url") or "",
                },
                "ocr": {
                    "lab": bool(jpg) and n_lab >= jpg,
                    "paddle": bool(jpg) and n_pad >= jpg,
                    "dich": bool(jpg) and n_dich >= jpg,
                    "lab_pages": n_lab,
                    "paddle_pages": n_pad,
                    "dich_pages": n_dich,
                },
                "notes": "Không phải gia phả — Việt sử kính" if vid == 130 else "",
            }
        )
    books.sort(key=lambda b: int(b["volume_id"]))
    return books


def gpc_book(repo: Path) -> dict[str, Any]:
    book_dir = repo / "data/00_raw/du_lieu_han_nom_moi/gia_pha_chi"
    pages = sorted(
        p for p in book_dir.glob("*.jpg") if p.stem.isdigit() and "boundingbox" not in p.name
    )
    lab = sum(1 for p in pages if (book_dir / f"{p.stem}-ocr-raw.json").exists() or (book_dir / f"{p.stem}-boundingbox.json").exists())
    paddle = sum(1 for p in pages if (book_dir / "paddleocr" / f"{p.stem}-paddleocr.json").exists())
    dich = sum(1 for p in pages if (book_dir / f"{p.stem}-dich.md").exists())
    n = len(pages)
    return {
        "book_id": "gpc-dang-1928",
        "source": "local_scan",
        "volume_id": None,
        "collection_id": None,
        "title_han": "家譜誌",
        "title_vn": "Gia phả chí (họ Đặng, Bảo Đại 1928)",
        "clan_key": "dang",
        "kind": "gia_pha",
        "loai": ["chi_pha", "ho_pha"],
        "layout_tags": ["bia", "tua", "tho_tu_than", "pha_ky", "doi_sau", "van_te"],
        "language": "han",
        "script_hint": "mixed",
        "catalog_code": "",
        "page_count": n,
        "page_count_catalog": n,
        "jpg_source": n,
        "jpg_review": n,
        "page_count_source": "jpg_count",
        "flags": [],
        "read_status": "da_doc",
        "paths": {
            "root": "data/00_raw/du_lieu_han_nom_moi/gia_pha_chi",
            "pages": "data/00_raw/du_lieu_han_nom_moi/gia_pha_chi",
            "review": "data/00_raw/du_lieu_han_nom_moi/gia_pha_chi",
            "paddleocr": "data/00_raw/du_lieu_han_nom_moi/gia_pha_chi/paddleocr",
            "url": "",
        },
        "ocr": {
            "lab": lab == n and n > 0,
            "paddle": paddle == n and n > 0,
            "dich": dich == n and n > 0,
            "lab_pages": lab,
            "paddle_pages": paddle,
            "dich_pages": dich,
        },
        "notes": "Chi/hộ phả; cuốn duy nhất đã A/B lab vs Paddle vs dịch.",
    }


def huong_books(repo: Path) -> list[dict[str, Any]]:
    """Lô Hương 25/08 — kế ước Hán-Nôm + ảnh gia phả Quốc ngữ (không OCR)."""
    week = repo / "data/00_raw/du_lieu_han_nom_moi/25_8_2026"
    huong = find_named_dir(week, "huong")
    if huong is None:
        return []
    books: list[dict[str, Any]] = []
    han = find_named_dir(huong, "han")
    if han is not None:
        pages_dir = han / "pages"
        jpg_n = count_digit_stem_images(pages_dir)
        paddle_dir = han / "paddleocr"
        n_pad = len(list(paddle_dir.glob("*-paddleocr.json"))) if paddle_dir.is_dir() else 0
        n_lab = len(list(pages_dir.glob("*-ocr-raw.json"))) if pages_dir.is_dir() else 0
        oco = next((p for p in han.iterdir() if p.suffix.lower() == ".docx" and "co" in fold_name(p.name)), None)
        rel_root = han.relative_to(repo).as_posix()
        books.append(
            {
                "book_id": "nguyen-ke-han-nom",
                "source": "local_scan",
                "volume_id": None,
                "collection_id": None,
                "title_han": "阮計漢喃契約",
                "title_vn": "Nguyễn Kế Hán-Nôm — kế ước / văn khế đất (Diên Khánh)",
                "clan_key": "nguyen",
                "kind": "ke_uoc",
                "loai": ["ke_uoc"],
                "layout_tags": ["van_khe", "phan_gia", "tuyet_mai"],
                "language": "han",
                "script_hint": "handwritten",
                "catalog_code": "huong-2026-08-25",
                "page_count": jpg_n,
                "page_count_catalog": jpg_n,
                "jpg_source": jpg_n,
                "jpg_review": jpg_n,
                "page_count_source": "jpg_count",
                "flags": ["doi_soat_oco"],
                "read_status": "da_doc",
                "paths": {
                    "root": rel_root,
                    "pages": f"{rel_root}/pages",
                    "review": None,
                    "paddleocr": f"{rel_root}/paddleocr",
                    "url": "",
                    "docx": oco.relative_to(repo).as_posix() if oco else None,
                    "analysis": (huong / "doi_soat_oco.md").relative_to(repo).as_posix(),
                },
                "ocr": {
                    "lab": n_lab >= jpg_n and jpg_n > 0,
                    "paddle": n_pad >= jpg_n and jpg_n > 0,
                    "dich": False,
                    "lab_pages": n_lab,
                    "paddle_pages": n_pad,
                    "dich_pages": 0,
                },
                "notes": (
                    "15 trang scan thảo/khế. Paddle PP-OCRv6 mean ~0.70. Lab Kim Hán Nôm 15/15 "
                    "(ocr_id=1, có bbox). Ảnh gốc chỉ trong pages/ (đã gỡ IMG_* trùng). "
                    "Gold sát: bằng khoán; Ô.cố = ghi chú lỏng."
                ),
            }
        )
    gia = find_named_dir(huong, "gia")
    if gia is not None:
        jpg_n, dupes = count_jpg_exclude_paren1(gia)
        rel_root = gia.relative_to(repo).as_posix()
        bang = next((p for p in gia.iterdir() if p.suffix.lower() == ".docx"), None)
        books.append(
            {
                "book_id": "nguyen-ke-gia-pha",
                "source": "local_scan",
                "volume_id": None,
                "collection_id": None,
                "title_han": "",
                "title_vn": "Nguyễn Kế gia phả — ảnh Quốc ngữ (+ bằng khoán Diên Khánh)",
                "clan_key": "nguyen",
                "kind": "gia_pha_photo",
                "loai": ["toc_pha"],
                "layout_tags": ["photo", "bang_khoan"],
                "language": "vi",
                "script_hint": "quoc_ngu",
                "catalog_code": "huong-2026-08-25-qn",
                "page_count": jpg_n,
                "page_count_catalog": jpg_n + dupes,
                "jpg_source": jpg_n,
                "jpg_review": 0,
                "page_count_source": "jpg_count",
                "flags": ["skip_ocr", "skip_ocr_hannom", "paren1_dupes"],
                "read_status": "da_doc",
                "paths": {
                    "root": rel_root,
                    "pages": None,
                    "review": None,
                    "url": "",
                    "docx": bang.relative_to(repo).as_posix() if bang else None,
                },
                "ocr": {
                    "lab": False,
                    "paddle": False,
                    "dich": False,
                    "lab_pages": 0,
                    "paddle_pages": 0,
                    "dich_pages": 0,
                },
                "notes": (
                    f"Ảnh gia phả Quốc ngữ; {dupes} file (1) trùng. Đã gỡ OCR nhầm 25/08. "
                    "DOCX bằng khoán trùng bản ở root Hương."
                ),
            }
        )
    return books


def nguyen_phuc_book(repo: Path) -> dict[str, Any] | None:
    """Sách Quốc ngữ in 1995 — không phải tông phả Hán 13/08."""
    folder = repo / "data/00_raw/du_lieu_han_nom_moi/28_8_2026"
    if not folder.is_dir():
        return None
    pdf = next(
        (p for p in folder.iterdir() if p.suffix.lower() == ".pdf" and "nguyen" in fold_name(p.name)),
        None,
    )
    if pdf is None:
        return None
    pages = pdf_page_count(pdf)
    preview = folder / "preview"
    jpg_n = count_digit_stem_images(preview)
    rel = pdf.relative_to(repo).as_posix()
    return {
        "book_id": "pdf-nguyen-phuc-the-pha",
        "source": "quoc_ngu_print",
        "volume_id": None,
        "collection_id": None,
        "title_han": "阮福族世譜",
        "title_vn": "Nguyễn Phúc tộc thế phả (Nxb Thuận Hóa, 1995)",
        "clan_key": "nguyen",
        "kind": "the_pha_print",
        "loai": ["tong_pha", "the_pha"],
        "layout_tags": ["thuy_to_pha", "vuong_pha", "de_pha", "he_phong_chi"],
        "language": "vi",
        "script_hint": "printed",
        "catalog_code": "1995-thuan-hoa",
        "page_count": pages,
        "page_count_catalog": pages,
        "jpg_source": jpg_n,
        "jpg_review": jpg_n,
        "page_count_source": "pdf_pages" if pages is not None else "unknown",
        "flags": ["skip_ocr_hannom", "image_only_pdf", "not_tong_pho_pdf"],
        "read_status": "da_doc",
        "paths": {
            "root": "data/00_raw/du_lieu_han_nom_moi/28_8_2026",
            "pages": "data/00_raw/du_lieu_han_nom_moi/28_8_2026/preview",
            "review": None,
            "url": "",
            "pdf": rel,
            "analysis": "data/00_raw/du_lieu_han_nom_moi/28_8_2026/phan_tich.md",
        },
        "ocr": {
            "lab": False,
            "paddle": False,
            "dich": False,
            "lab_pages": 0,
            "paddle_pages": 0,
            "dich_pages": 0,
        },
        "notes": (
            "Quốc ngữ in 1995 (namkyluctinh.org digitize), 477 trang ảnh, 0 lớp text. "
            "Cấu trúc Hệ→Phòng→Chi. CẤM catalog như tong_pho_pdf Hán (Mai/Là/Trần 13/08). "
            "Không OCR Hán; không OCR hết 477 trang tuần này."
        ),
        "bytes": pdf.stat().st_size,
    }


def phan_gia_book(repo: Path) -> dict[str, Any] | None:
    """Ấn bản học 2006: dịch QN + facsimile Hán — không phải lý thuyết, không tông phả Trung."""
    folder = repo / "data/00_raw/du_lieu_han_nom_moi/31_8_2026"
    if not folder.is_dir():
        return None
    pdf = next(
        (
            p
            for p in folder.iterdir()
            if p.suffix.lower() == ".pdf" and "phan" in fold_name(p.name) and "cong" in fold_name(p.name)
        ),
        None,
    )
    if pdf is None:
        return None
    pages = pdf_page_count(pdf)
    preview = folder / "preview"
    jpg_n = count_digit_stem_images(preview)
    rel = pdf.relative_to(repo).as_posix()
    return {
        "book_id": "pdf-phan-gia-cong-pha",
        "source": "an_ban_hoc",
        "volume_id": None,
        "collection_id": None,
        "title_han": "潘家公譜",
        "title_vn": "Phan gia công phả (Gia Thiện – Hà Tĩnh; Nxb Thế Giới, 2006)",
        "clan_key": "phan",
        "kind": "cong_pha_an_ban",
        "loai": ["toc_pha", "cong_pha"],
        "layout_tags": ["pha_ky", "pha_he", "pha_do", "sach_dan", "nguyen_van_han"],
        "language": "vi+han",
        "script_hint": "printed+manuscript_facsimile",
        "catalog_code": "2006-the-gioi-ctncgpvn-8",
        "page_count": pages,
        "page_count_catalog": pages,
        "jpg_source": jpg_n,
        "jpg_review": jpg_n,
        "page_count_source": "pdf_pages" if pages is not None else "unknown",
        "flags": [
            "image_only_pdf",
            "has_vn_translation",
            "has_han_facsimile",
            "skip_ocr_hannom_on_vn",
            "not_tong_pho_pdf",
            "not_ly_thuyet",
        ],
        "read_status": "da_doc",
        "paths": {
            "root": "data/00_raw/du_lieu_han_nom_moi/31_8_2026",
            "pages": "data/00_raw/du_lieu_han_nom_moi/31_8_2026/preview",
            "review": None,
            "url": "",
            "pdf": rel,
            "analysis": "data/00_raw/du_lieu_han_nom_moi/31_8_2026/phan_tich.md",
        },
        "ocr": {
            "lab": False,
            "paddle": False,
            "dich": False,
            "lab_pages": 0,
            "paddle_pages": 0,
            "dich_pages": 0,
        },
        "notes": (
            "CTNC Gia phả VN tập 8. Dịch+chú Nguyễn Ngọc Nhuận, hiệu đính Phan Huy Lê. "
            "169 trang PDF ảnh, 0 lớp text; trang in tới 327 (spread). "
            "Dịch QN p.in 33–120; sơ đồ 121; facsimile Hán p.in 141–310; sách dẫn 311. "
            "CẤM catalog ly_thuyet / tong_pho_pdf. Không OCR trang dịch; facsimile mới là ứng viên OCR."
        ),
        "bytes": pdf.stat().st_size,
    }


def pdf_books(repo: Path) -> list[dict[str, Any]]:
    pdf_dir = repo / "data/00_raw/du_lieu_han_nom_moi/13_8_2026"
    if not pdf_dir.is_dir():
        return []
    mapping = [
        ("1000", "pdf-1000-mai", "梅氏宗譜", "Mai thị tông phả — tập 1", "mai"),
        ("1001", "pdf-1001-la", "罗氏宗譜", "Là thị tông phả — tập 1", "la"),
        ("1005", "pdf-1005-tran", "陈氏宗譜", "Trần thị tông phả — tập 1", "tran"),
    ]
    books: list[dict[str, Any]] = []
    files = {p.name: p for p in pdf_dir.iterdir() if p.suffix.lower() == ".pdf"}
    for prefix, book_id, han, vn, clan in mapping:
        path = next((p for name, p in files.items() if name.startswith(prefix)), None)
        if path is None:
            continue
        pages = pdf_page_count(path)
        rel = path.relative_to(repo).as_posix()
        rendered = repo / "data/00_raw/du_lieu_han_nom_moi/13_8_2026" / book_id / "pages"
        jpg_n = count_images(rendered)
        paddle_dir = repo / "data/00_raw/du_lieu_han_nom_moi/13_8_2026" / book_id / "paddleocr"
        dich_dir = repo / "data/00_raw/du_lieu_han_nom_moi/13_8_2026" / book_id / "dich"
        n_pad = len(list(paddle_dir.glob("*-paddleocr.json"))) if paddle_dir.is_dir() else 0
        n_dich = len(list(dich_dir.glob("*-dich.md"))) if dich_dir.is_dir() else 0
        n_lab = len(list(rendered.glob("*-ocr-raw.json"))) if rendered.is_dir() else 0
        flags: list[str] = []
        if pages is None and jpg_n == 0:
            flags.append("pdf_pages_unknown")
        books.append(
            {
                "book_id": book_id,
                "source": "tong_pho_pdf",
                "volume_id": None,
                "collection_id": None,
                "title_han": han,
                "title_vn": vn,
                "clan_key": clan,
                "kind": "tong_pho_pdf",
                "loai": ["tong_pha"],
                "layout_tags": [],
                "language": "han",
                "script_hint": "printed",
                "catalog_code": prefix,
                "page_count": jpg_n or pages,
                "page_count_catalog": pages,
                "jpg_source": jpg_n,
                "jpg_review": jpg_n,
                "page_count_source": "jpg_count" if jpg_n else ("pdf_pages" if pages is not None else "unknown"),
                "flags": flags,
                "paths": {
                    "root": f"data/00_raw/du_lieu_han_nom_moi/13_8_2026/{book_id}",
                    "pages": f"data/00_raw/du_lieu_han_nom_moi/13_8_2026/{book_id}/pages",
                    "review": None,
                    "url": "",
                    "pdf": rel,
                },
                "ocr": {
                    "lab": bool(jpg_n) and n_lab >= jpg_n,
                    "paddle": bool(jpg_n) and n_pad >= jpg_n,
                    "dich": bool(jpg_n) and n_dich >= jpg_n,
                    "lab_pages": n_lab,
                    "paddle_pages": n_pad,
                    "dich_pages": n_dich,
                },
                "notes": "PDF tông phả — render JPG rồi OCR.",
                "bytes": path.stat().st_size,
            }
        )
    return books


DOCX_24_8: list[dict[str, Any]] = [
    {
        "match": ("pham", "pho"),
        "book_id": "docx-pham-1876",
        "title_han": "范氏家譜 · 范族副意",
        "title_vn": "Gia phả + Phó ý họ Phạm (biên dịch 2018)",
        "clan_key": "pham",
        "language": "vi",
        "script_hint": "quoc_ngu",
        "catalog_code": "",
        "loai": ["toc_pha"],
        "layout_tags": ["tua", "pha_ky", "phien_am", "pho_y"],
        "year_source": 1876,
        "year_translate": 2018,
        "notes": (
            "Bản dịch Quốc ngữ (Phạm Văn Tiệp, Biên Hòa 2018; Trung tâm NCTH Gia phả TP.HCM, "
            "Lâm Hoài Phương). Gốc Hán ~1876 (Tự Đức 30), thôn Tiên Lã, xã An Trung. "
            "Hai phần: gia phả (4 thế hệ, Phạm Hữu Huân) + phó ý cúng 7 chi. "
            "Trong Word: dịch nghĩa + phiên âm (Phạm gia phả ký / Phạm tộc phó ý)."
        ),
    },
    {
        "match": ("nguyen",),
        "book_id": "docx-nguyen-van",
        "title_han": "阮文族譜",
        "title_vn": "Gia phả Nguyễn Văn (dịch nghĩa + phiên âm + Hán)",
        "clan_key": "nguyen",
        "language": "mixed",
        "script_hint": "mixed",
        "catalog_code": "",
        "loai": ["chi_pha"],
        "layout_tags": ["dich_nghia", "phien_am", "han"],
        "year_source": 1975,
        "year_translate": None,
        "notes": (
            "Một file ba lớp: I dịch nghĩa, II phiên âm, III chữ Hán (陽曆 1975, Ất Mão). "
            "Sao bởi Nguyễn Văn Líu (chi 1) và Thích Từ Bảo. Khoảng 7 đời, ~400 người "
            "(theo lời Hán). Địa danh: Hội Sơn, Đồng Lành, Lạc Câu. Chưa có ảnh scan gốc."
        ),
    },
    {
        "match": ("tran",),
        "book_id": "docx-tran-200",
        "title_han": "陳氏家譜",
        "title_vn": "Gia phả họ Trần — Thanh Thủy Thượng, Hương Thủy, TT-Huế",
        "clan_key": "tran",
        "language": "vi",
        "script_hint": "quoc_ngu",
        "catalog_code": "GSL HN.2011.11.200",
        "loai": ["toc_pha"],
        "layout_tags": ["dich_nghia", "phien_am", "nhan_xet"],
        "year_source": 1890,
        "year_translate": 2018,
        "notes": (
            "Biên dịch 05/2018 (Lâm Hoài Phương, CLB Hán Nôm / Thư viện KHTH / NCTH Gia phả). "
            "Gốc tu phổ Thành Thái 2 (1890), đời 1–16, thủy tổ Trần Khánh Hữu. "
            "Tục biên 1920: GSL HN.2011.11.119. Phả đồ (phần III) không có trong Word. "
            "Người dịch: đời 6–10 liệt kê ~130 vị ít liên kết."
        ),
    },
]


def docx_books(repo: Path) -> list[dict[str, Any]]:
    folder = repo / "data/00_raw/du_lieu_han_nom_moi/24_8_2026"
    if not folder.is_dir():
        return []
    files = [p for p in folder.iterdir() if p.suffix.lower() == ".docx" and not p.name.startswith("~$")]
    books: list[dict[str, Any]] = []
    used: set[Path] = set()
    for spec in DOCX_24_8:
        path = None
        for candidate in files:
            key = fold_name(candidate.name)
            if all(token in key for token in spec["match"]):
                path = candidate
                break
        if path is None:
            continue
        used.add(path)
        paras = read_docx_paras(path)
        stats = text_stats(paras)
        app = read_docx_app_props(path)
        word_pages = int(app["pages"]) if app.get("pages", "").isdigit() else None
        rel = path.relative_to(repo).as_posix()
        books.append(
            {
                "book_id": spec["book_id"],
                "source": "local_docx",
                "volume_id": None,
                "collection_id": None,
                "title_han": spec["title_han"],
                "title_vn": spec["title_vn"],
                "clan_key": spec["clan_key"],
                "kind": "gia_pha_dich",
                "loai": spec["loai"],
                "layout_tags": spec["layout_tags"],
                "language": spec["language"],
                "script_hint": spec["script_hint"],
                "catalog_code": spec["catalog_code"],
                "page_count": word_pages or stats["paras"],
                "page_count_catalog": word_pages,
                "jpg_source": 0,
                "jpg_review": 0,
                "page_count_source": "docx_pages" if word_pages else "docx_paras",
                "flags": ["no_scan", "da_doc"],
                "read_status": "da_doc",
                "paths": {
                    "root": "data/00_raw/du_lieu_han_nom_moi/24_8_2026",
                    "pages": None,
                    "review": None,
                    "url": "",
                    "docx": rel,
                    "analysis": f"data/00_raw/du_lieu_han_nom_moi/24_8_2026/{spec['book_id']}.md",
                    "fulltext": f"data/00_raw/du_lieu_han_nom_moi/24_8_2026/{spec['book_id']}-toan-van.md",
                },
                "ocr": {
                    "lab": False,
                    "paddle": False,
                    "dich": True,
                    "lab_pages": 0,
                    "paddle_pages": 0,
                    "dich_pages": 1,
                },
                "text_stats": {
                    **stats,
                    "word_pages": word_pages,
                    "word_words": int(app["words"]) if app.get("words", "").isdigit() else None,
                    "word_characters": int(app["characters"]) if app.get("characters", "").isdigit() else None,
                },
                "year_source": spec["year_source"],
                "year_translate": spec["year_translate"],
                "notes": spec["notes"],
                "bytes": path.stat().st_size,
            }
        )
    for path in files:
        if path in used:
            continue
        rel = path.relative_to(repo).as_posix()
        paras = read_docx_paras(path)
        stats = text_stats(paras)
        app = read_docx_app_props(path)
        word_pages = int(app["pages"]) if app.get("pages", "").isdigit() else None
        stem = fold_name(path.stem)
        slug = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")[:40]
        books.append(
            {
                "book_id": f"docx-{slug}",
                "source": "local_docx",
                "volume_id": None,
                "collection_id": None,
                "title_han": "",
                "title_vn": path.name,
                "clan_key": clan_key(path.name),
                "kind": "gia_pha_dich",
                "loai": [],
                "layout_tags": [],
                "language": "unknown",
                "script_hint": "quoc_ngu",
                "catalog_code": "",
                "page_count": word_pages or stats["paras"],
                "page_count_catalog": word_pages,
                "jpg_source": 0,
                "jpg_review": 0,
                "page_count_source": "docx_pages" if word_pages else "docx_paras",
                "flags": ["no_scan", "unmapped"],
                "paths": {
                    "root": "data/00_raw/du_lieu_han_nom_moi/24_8_2026",
                    "pages": None,
                    "review": None,
                    "url": "",
                    "docx": rel,
                },
                "ocr": {
                    "lab": False,
                    "paddle": False,
                    "dich": True,
                    "lab_pages": 0,
                    "paddle_pages": 0,
                    "dich_pages": 1,
                },
                "text_stats": {**stats, "word_pages": word_pages},
                "notes": "DOCX chưa map metadata tay.",
                "bytes": path.stat().st_size,
            }
        )
    return books


def theory_books(repo: Path) -> list[dict[str, Any]]:
    """Sách lý thuyết đã đọc — không phải corpus Hán-Nôm để OCR."""
    folder = repo / "data/04_external/sach"
    if not folder.is_dir():
        return []
    specs = [
        {
            "match": ("tinh", "hoa"),
            "book_id": "sach-gia-pha-hoc-tinh-hoa",
            "title_han": "",
            "title_vn": "Gia phả học tinh hoa",
            "notes": (
                "Sách lý thuyết Quốc ngữ hiện đại — đối chiếu loại/tộc/tông/chi, bố cục phả "
                "(tuần 17/08: glossary với Lâm Hoài Phương). Không OCR, không đếm trang ảnh corpus."
            ),
        },
        {
            "match": ("3742",),
            "book_id": "sach-huong-dan-viet-gia-pha",
            "title_han": "",
            "title_vn": "Hướng dẫn viết gia phả (PDF 3742)",
            "notes": (
                "Metadata PDF: «HƯỚNG DẪN VIẾT GIA PHẢ». Sách hướng dẫn soạn phả, không phải bản Hán-Nôm. "
                "Dùng khi gắn tag loại/bố cục."
            ),
        },
    ]
    files = [p for p in folder.iterdir() if p.suffix.lower() == ".pdf"]
    books: list[dict[str, Any]] = []
    for spec in specs:
        path = next((p for p in files if all(t in fold_name(p.name) for t in spec["match"])), None)
        if path is None:
            continue
        pages = pdf_page_count(path)
        rel = path.relative_to(repo).as_posix()
        books.append(
            {
                "book_id": spec["book_id"],
                "source": "sach_ly_thuyet",
                "volume_id": None,
                "collection_id": None,
                "title_han": spec["title_han"],
                "title_vn": spec["title_vn"],
                "clan_key": "—",
                "kind": "ly_thuyet",
                "loai": [],
                "layout_tags": [],
                "language": "vi",
                "script_hint": "printed",
                "catalog_code": path.stem[:40],
                "page_count": pages,
                "page_count_catalog": pages,
                "jpg_source": 0,
                "jpg_review": 0,
                "page_count_source": "pdf_pages" if pages is not None else "unknown",
                "flags": ["not_corpus", "da_doc"],
                "read_status": "da_doc",
                "paths": {
                    "root": "data/04_external/sach",
                    "pages": None,
                    "review": None,
                    "url": "",
                    "pdf": rel,
                },
                "ocr": {
                    "lab": False,
                    "paddle": False,
                    "dich": False,
                    "lab_pages": 0,
                    "paddle_pages": 0,
                    "dich_pages": 0,
                },
                "notes": spec["notes"],
                "bytes": path.stat().st_size,
            }
        )
    return books


def build_catalog(repo: Path | None = None) -> dict[str, Any]:
    repo = repo or repo_root()
    extra = [b for b in (nguyen_phuc_book(repo), phan_gia_book(repo)) if b]
    books = (
        nom_books(repo)
        + [gpc_book(repo)]
        + pdf_books(repo)
        + huong_books(repo)
        + extra
        + docx_books(repo)
        + theory_books(repo)
    )
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "schema": "hannom-books-catalog.v1",
        "n_books": len(books),
        "books": books,
    }


def write_catalog(repo: Path | None = None) -> Path:
    repo = repo or repo_root()
    catalog = build_catalog(repo)
    out = repo / "data/00_raw/hannom/books_catalog.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> int:
    out = write_catalog()
    data = json.loads(out.read_text(encoding="utf-8"))
    print(f"Wrote {out}  ({data['n_books']} cuốn)")
    for book in data["books"]:
        flags = ",".join(book.get("flags") or []) or "—"
        print(
            f"  {book['book_id']:<16} {str(book.get('page_count')):>4}  "
            f"{book['kind']:<14} {flags:<18} {book['title_vn']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
