#!/usr/bin/env python3
"""Scan local Hán-Nôm books and write data/hannom/books_catalog.json.

From repo root:

  python nlp_family_extractor/tools/build_hannom_catalog.py
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}

CLAN_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("chu", ("chu tộc", "朱族")),
    ("le", ("lê tộc", "黎族", "黎氏")),
    ("doan", ("đoàn", "段族", "段譜")),
    ("nguyen", ("nguyễn", "阮族", "阮堂", "阮文")),
    ("giang", ("giang", "江氏")),
    ("dang", ("đặng", "鄧")),
    ("mai", ("mai thị", "梅氏")),
    ("la", ("là thị", "罗氏", "羅氏")),
    ("tran", ("trần thị", "陈氏", "陳氏")),
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
    catalog = load_json(repo / "data/hannom/nomfoundation/catalog.json") or {}
    volumes_root = repo / "data/hannom/nomfoundation/volumes"
    review_root = repo / "data/review_corpus/hannom"
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
                    "root": f"data/hannom/nomfoundation/volumes/{vid}",
                    "pages": f"data/hannom/nomfoundation/volumes/{vid}/pages",
                    "review": f"data/review_corpus/hannom/{vid}",
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
    book_dir = repo / "data/du_lieu_han_nom_moi/gia_pha_chi"
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
        "paths": {
            "root": "data/du_lieu_han_nom_moi/gia_pha_chi",
            "pages": "data/du_lieu_han_nom_moi/gia_pha_chi",
            "review": "data/du_lieu_han_nom_moi/gia_pha_chi",
            "paddleocr": "data/du_lieu_han_nom_moi/gia_pha_chi/paddleocr",
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


def pdf_books(repo: Path) -> list[dict[str, Any]]:
    pdf_dir = repo / "data/du_lieu_han_nom_moi/13_8_2026"
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
        rendered = repo / "data/du_lieu_han_nom_moi/13_8_2026" / book_id / "pages"
        jpg_n = count_images(rendered)
        paddle_dir = repo / "data/du_lieu_han_nom_moi/13_8_2026" / book_id / "paddleocr"
        dich_dir = repo / "data/du_lieu_han_nom_moi/13_8_2026" / book_id / "dich"
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
                    "root": f"data/du_lieu_han_nom_moi/13_8_2026/{book_id}",
                    "pages": f"data/du_lieu_han_nom_moi/13_8_2026/{book_id}/pages",
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


def build_catalog(repo: Path | None = None) -> dict[str, Any]:
    repo = repo or repo_root()
    books = nom_books(repo) + [gpc_book(repo)] + pdf_books(repo)
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "schema": "hannom-books-catalog.v1",
        "n_books": len(books),
        "books": books,
    }


def write_catalog(repo: Path | None = None) -> Path:
    repo = repo or repo_root()
    catalog = build_catalog(repo)
    out = repo / "data/hannom/books_catalog.json"
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
