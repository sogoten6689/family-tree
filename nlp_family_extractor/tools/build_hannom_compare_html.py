#!/usr/bin/env python3
"""Build an offline Hán-Nôm library: homepage = book list, each book = page analysis.

From repo root:

  python nlp_family_extractor/tools/build_hannom_compare_html.py

Writes:
  data/00_raw/hannom/index.html              — danh sách + thống kê Word
  data/00_raw/hannom/books/{book_id}.html    — phân tích từng cuốn
  data/00_raw/du_lieu_han_nom_moi/24_8_2026/{book_id}.md — phân tích Word
  data/00_raw/du_lieu_han_nom_moi/24_8_2026/thong_ke.md
  data/00_raw/hannom/hannom-viewer.css
  data/00_raw/du_lieu_han_nom_moi/thong_ke_han_nom.html — redirect sang index
"""

from __future__ import annotations

import html as html_lib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_TOOLS = Path(__file__).resolve().parent
import sys

if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
from build_hannom_catalog import read_docx_paras, write_catalog
from ocr_paddleocr import list_page_images
from write_docx_analysis import analysis_record, write_docx_analyses

PAGE_LAYOUT = {
    0: ("bìa", "Bìa — nhan đề 家譜誌"),
    1: ("tựa", "Lời tựa (1)"),
    2: ("tựa", "Kết tựa + niên đại Bảo Đại 1928"),
    3: ("thờ", "Thờ tứ thân"),
    4: ("thờ", "Hiển tổ / hiển khảo"),
    5: ("thờ", "Bá, thúc, cô, huynh"),
    6: ("phả ký", "Phả ký — nguồn gốc họ Đặng"),
    7: ("phả ký", "Phả ký — đời cha / chú"),
    8: ("phả ký", "Phả ký — hiển khảo húy Cửu"),
    9: ("phả ký", "Phả ký — đời sau"),
    10: ("phả ký", "Phả ký — kết"),
    11: ("đời sau", "Đời sau — Ất Mùi Lê→Đặng"),
    12: ("đời sau", "Đời sau — phả hệ"),
    13: ("đời sau", "Đổi họ Lê → Đặng"),
    14: ("văn tế", "Mẫu văn tế / văn khấn"),
    15: ("văn tế", "Văn tế Trung nguyên / nguyên đán"),
    16: ("văn tế", "Văn tế — kết"),
}

CLAN_LABEL = {
    "chu": "họ Chu",
    "le": "họ Lê",
    "doan": "họ Đoàn",
    "nguyen": "họ Nguyễn",
    "giang": "họ Giang",
    "dang": "họ Đặng",
    "mai": "họ Mai",
    "la": "họ La",
    "pham": "họ Phạm",
    "tran": "họ Trần",
    "thuy_ung": "họ Thuỵ Ứng",
    "unknown": "chưa gán họ",
    "—": "—",
}

KIND_LABEL = {
    "gia_pha": "Gia phả",
    "gia_pha_dich": "Gia phả (Word dịch)",
    "ly_thuyet": "Sách lý thuyết",
    "su_lieu": "Sử liệu",
    "tong_pho_pdf": "Tông phả (PDF Hán)",
    "ke_uoc": "Kế ước / văn khế",
    "the_pha_print": "Thế phả (Quốc ngữ in)",
    "gia_pha_photo": "Gia phả (ảnh Quốc ngữ)",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def rel_to(path: Path, html_dir: Path) -> str | None:
    if not path.exists():
        return None
    return os.path.relpath(path.resolve(), html_dir.resolve()).replace("\\", "/")


def file_info(path: Path, html_dir: Path, repo: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return {
        "name": path.name,
        "rel_html": rel_to(path, html_dir),
        "rel_repo": os.path.relpath(path.resolve(), repo.resolve()).replace("\\", "/"),
        "abs": str(path.resolve()),
        "bytes": path.stat().st_size,
    }


def bbox_scores(payload: dict[str, Any]) -> list[float]:
    scores: list[float] = []
    for item in payload.get("result_bbox") or []:
        if isinstance(item, list) and len(item) >= 2 and isinstance(item[1], (list, tuple)) and len(item[1]) >= 2:
            try:
                scores.append(float(item[1][1]))
            except (TypeError, ValueError):
                pass
    return scores


def mean(xs: list[float]) -> float | None:
    if not xs:
        return None
    return round(sum(xs) / len(xs), 4)


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def book_root(book: dict[str, Any], repo: Path) -> Path:
    rel = (book.get("paths") or {}).get("root") or ""
    return repo / rel


def images_for(book: dict[str, Any], repo: Path) -> list[Path]:
    if book.get("source") in ("local_docx", "sach_ly_thuyet"):
        return []
    if "skip_ocr" in (book.get("flags") or []) and not (book.get("paths") or {}).get("pages"):
        return []
    paths = book.get("paths") or {}
    candidates = []
    for key in ("pages", "root"):
        rel = paths.get(key)
        if not rel:
            continue
        path = repo / rel
        if path.is_dir():
            candidates.append(path)
        elif book.get("source") == "tong_pho_pdf":
            rendered = repo / "data/00_raw/du_lieu_han_nom_moi/13_8_2026" / book["book_id"] / "pages"
            if rendered.is_dir():
                candidates.append(rendered)
    seen: set[Path] = set()
    images: list[Path] = []
    for folder in candidates:
        for image in list_page_images(folder, None):
            resolved = image.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            images.append(image)
    images.sort(key=lambda p: int(p.stem))
    return images


def find_dich(root: Path, stem: str) -> Path:
    nested = root / "dich" / f"{stem}-dich.md"
    if nested.is_file():
        return nested
    return root / f"{stem}-dich.md"


def page_section(book_id: str, stem: str) -> tuple[str, str]:
    if book_id == "gpc-dang-1928" and stem.isdigit():
        return PAGE_LAYOUT.get(int(stem), ("trang", f"Trang {stem}"))
    return ("trang", f"Trang {stem}")


def is_lab_record(payload: dict[str, Any]) -> bool:
    engine = str(payload.get("engine") or "").lower()
    return engine.startswith("kim") or bool(payload.get("ocr_id") is not None and "paddle" not in engine)


def load_lab(parent: Path, root: Path, stem: str) -> dict[str, Any]:
    raw = load_json(parent / f"{stem}-ocr-raw.json") or load_json(root / f"{stem}-ocr-raw.json") or {}
    box = load_json(parent / f"{stem}-boundingbox.json") or load_json(root / f"{stem}-boundingbox.json") or {}
    if box and is_lab_record(box):
        return box
    if raw and is_lab_record(raw):
        return raw
    return {}


def collect_pages(book: dict[str, Any], html_dir: Path, repo: Path) -> list[dict[str, Any]]:
    root = book_root(book, repo)
    pages: list[dict[str, Any]] = []
    for image in images_for(book, repo):
        stem = image.stem
        section, label = page_section(book["book_id"], stem)
        parent = image.parent
        lab = load_lab(parent, root, stem)
        pad = load_json(root / "paddleocr" / f"{stem}-paddleocr.json") or {}
        lab_texts = [str(t) for t in lab.get("result_ocr_text") or []]
        pad_texts = [str(t) for t in pad.get("result_ocr_text") or []]
        lab_s = bbox_scores(lab)
        pad_s = bbox_scores(pad)
        dich_path = find_dich(root, stem)
        pages.append(
            {
                "n": int(stem),
                "stem": stem,
                "section": section,
                "label": label,
                "lab": {
                    "engine": lab.get("engine") or ("kimhannom" if lab_texts else ""),
                    "texts": lab_texts,
                    "n_lines": len(lab_texts),
                    "mean": mean(lab_s),
                    "ocr_id": lab.get("ocr_id"),
                    "lang_type": lab.get("lang_type"),
                },
                "paddle": {
                    "engine": pad.get("engine") or "paddleocr",
                    "model": pad.get("model"),
                    "texts": pad_texts,
                    "n_lines": len(pad_texts),
                    "mean": pad.get("mean_score") if pad.get("mean_score") is not None else mean(pad_s),
                    "elapsed_s": pad.get("elapsed_s"),
                },
                "dich": dich_path.read_text(encoding="utf-8") if dich_path.is_file() else "",
                "files": {
                    "image": file_info(image, html_dir, repo),
                    "lab_bbox_preview": (
                        file_info(parent / f"{stem}-boundingbox-preview.jpg", html_dir, repo)
                        or file_info(root / f"{stem}-boundingbox-preview.jpg", html_dir, repo)
                    )
                    if is_lab_record(lab)
                    else None,
                    "paddle_preview": file_info(
                        root / "paddleocr" / "preview" / f"{stem}_ocr_res_img.jpg", html_dir, repo
                    ),
                    "paddle_txt": file_info(root / "paddleocr" / f"{stem}-paddleocr.txt", html_dir, repo),
                    "dich": file_info(dich_path, html_dir, repo),
                },
            }
        )
    return pages


def detect_docx_sections(book_id: str, paras: list[str]) -> list[dict[str, Any]]:
    markers: list[tuple[str, str]] = []
    if book_id == "docx-pham-1876":
        markers = [
            ("tua", "Lời tựa"),
            ("dich_pha", "Gia phả — dịch nghĩa"),
            ("am_pha", "Gia phả — phiên âm"),
            ("dich_pho", "Phó ý — dịch nghĩa"),
            ("am_pho", "Phó ý — phiên âm"),
        ]
        keys = ["LỜI TỰA", "GIA PHẢ HỌ PHẠM", "PHẠM GIA PHẢ KÝ", "PHÓ Ý HỌ PHẠM", "PHẠM TỘC PHÓ Ý"]
    elif book_id == "docx-nguyen-van":
        markers = [
            ("dich", "I. Dịch nghĩa"),
            ("am", "II. Phiên âm"),
            ("han", "III. Chữ Hán"),
        ]
        keys = ["I. DỊCH NGHĨA", "II. PHIÊN ÂM", "III."]
    elif book_id == "docx-tran-200":
        markers = [
            ("dich", "I. Dịch nghĩa"),
            ("am", "II. Phiên âm"),
            ("nhan_xet", "IV. Nhận xét"),
        ]
        keys = ["INội dung dịch nghĩa", "IIPhiên âm", "IV"]
    else:
        return [{"id": "full", "title": "Toàn văn", "start": 0, "end": len(paras)}]

    def find_marker(key: str) -> int:
        hits = [
            i
            for i, p in enumerate(paras)
            if key.lower() in p.lower() and not p.lstrip().startswith("-")
        ]
        return hits[-1] if hits else -1

    starts: list[int] = [find_marker(key) for key in keys]
    sections: list[dict[str, Any]] = []
    for i, (sid, title) in enumerate(markers):
        start = starts[i]
        if start < 0:
            continue
        end = len(paras)
        for later in starts[i + 1 :]:
            if later > start:
                end = later
                break
        sections.append({"id": sid, "title": title, "start": start, "end": end})
    if not sections:
        sections = [{"id": "full", "title": "Toàn văn", "start": 0, "end": len(paras)}]
    if sections and sections[0]["start"] > 0:
        sections.insert(0, {"id": "bia", "title": "Bìa / mục lục", "start": 0, "end": sections[0]["start"]})
    return sections


def load_docx_text(book: dict[str, Any], repo: Path) -> dict[str, Any] | None:
    rel = (book.get("paths") or {}).get("docx")
    if not rel:
        return None
    path = repo / rel
    if not path.is_file():
        return None
    paras = read_docx_paras(path)
    sections = detect_docx_sections(book.get("book_id") or "", paras)
    for sec in sections:
        chunk = paras[sec["start"] : sec["end"]]
        sec["n_paras"] = len(chunk)
        sec["chars"] = sum(len(p) for p in chunk) + max(len(chunk) - 1, 0)
        sec["text"] = "\n\n".join(chunk)
    return {"paras": len(paras), "sections": sections}


def catalog_summary(books: list[dict[str, Any]]) -> dict[str, Any]:
    def image_pages(book: dict[str, Any]) -> int:
        if book.get("source") in ("local_docx", "sach_ly_thuyet"):
            return 0
        return int(book.get("jpg_source") or book.get("page_count") or 0)

    def word_pages(book: dict[str, Any]) -> int:
        if book.get("source") != "local_docx":
            return 0
        stats = book.get("text_stats") or {}
        return int(stats.get("word_pages") or book.get("page_count") or 0)

    gia = [b for b in books if b.get("kind") == "gia_pha"]
    return {
        "n_books": len(books),
        "n_gia_pha": len(gia),
        "n_docx": sum(1 for b in books if b.get("source") == "local_docx"),
        "n_ly_thuyet": sum(1 for b in books if b.get("kind") == "ly_thuyet"),
        "n_da_doc": sum(1 for b in books if b.get("read_status") == "da_doc" or "da_doc" in (b.get("flags") or [])),
        "n_nom": sum(1 for b in books if b.get("source") == "nomfoundation"),
        "n_scan": sum(1 for b in books if b.get("source") == "local_scan"),
        "n_pdf": sum(1 for b in books if b.get("source") == "tong_pho_pdf"),
        "n_quoc_ngu_print": sum(1 for b in books if b.get("source") == "quoc_ngu_print"),
        "pages_local": sum(image_pages(b) for b in books),
        "pages_word": sum(word_pages(b) for b in books),
        "missing_images": sum(1 for b in books if "missing_pages" in (b.get("flags") or [])),
        "ocr_lab": sum(1 for b in books if (b.get("ocr") or {}).get("lab")),
        "ocr_paddle": sum(1 for b in books if (b.get("ocr") or {}).get("paddle")),
        "ocr_dich": sum(1 for b in books if (b.get("ocr") or {}).get("dich")),
    }


def enrich_book(book: dict[str, Any], html_dir: Path, repo: Path) -> dict[str, Any]:
    images = images_for(book, repo)
    cover = file_info(images[0], html_dir, repo) if images else None
    clan = book.get("clan_key") or "—"
    return {
        **book,
        "clan_label": CLAN_LABEL.get(clan, clan),
        "kind_label": KIND_LABEL.get(book.get("kind") or "", book.get("kind") or ""),
        "href": f"books/{book['book_id']}.html",
        "cover": cover,
        "n_images": len(images),
        "analysis_href": rel_to(repo / (book.get("paths") or {}).get("analysis"), html_dir)
        if (book.get("paths") or {}).get("analysis")
        else None,
        "fulltext_href": rel_to(repo / (book.get("paths") or {}).get("fulltext"), html_dir)
        if (book.get("paths") or {}).get("fulltext")
        else None,
    }


def book_payload(book: dict[str, Any], pages: list[dict[str, Any]], html_dir: Path, repo: Path) -> dict[str, Any]:
    lab_means = [p["lab"]["mean"] for p in pages if p["lab"]["mean"] is not None]
    pad_means = [p["paddle"]["mean"] for p in pages if p["paddle"]["mean"] is not None]
    clan = book.get("clan_key") or "—"
    text_doc = load_docx_text(book, repo)
    analysis = None
    if text_doc:
        analysis = analysis_record(book, text_doc.get("sections") or [])
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "book": {
            **book,
            "clan_label": CLAN_LABEL.get(clan, clan),
            "kind_label": KIND_LABEL.get(book.get("kind") or "", book.get("kind") or ""),
        },
        "pages": pages,
        "n_pages": len(pages),
        "lab_mean": mean(lab_means),
        "paddle_mean": mean(pad_means),
        "has_lab": sum(1 for p in pages if p["lab"]["n_lines"]),
        "has_paddle": sum(1 for p in pages if p["paddle"]["n_lines"]),
        "has_dich": sum(1 for p in pages if p["dich"]),
        "text_doc": text_doc,
        "analysis": analysis,
        "paths": {
            "index": "../index.html",
            "root": (book.get("paths") or {}).get("root") or "",
            "pages": (book.get("paths") or {}).get("pages") or "",
            "url": (book.get("paths") or {}).get("url") or "",
            "pdf": (book.get("paths") or {}).get("pdf") or "",
            "docx": (book.get("paths") or {}).get("docx") or "",
            "analysis": (book.get("paths") or {}).get("analysis") or "",
            "fulltext": (book.get("paths") or {}).get("fulltext") or "",
        },
        "analysis_href": rel_to(repo / ((book.get("paths") or {}).get("analysis") or ""), html_dir)
        if (book.get("paths") or {}).get("analysis")
        else None,
        "fulltext_href": rel_to(repo / ((book.get("paths") or {}).get("fulltext") or ""), html_dir)
        if (book.get("paths") or {}).get("fulltext")
        else None,
        "pdf_href": rel_to(repo / ((book.get("paths") or {}).get("pdf") or ""), html_dir)
        if (book.get("paths") or {}).get("pdf")
        else None,
    }


CSS = """
:root {
  --bg: #f4efe6;
  --paper: #fffcf6;
  --ink: #241c14;
  --muted: #6b5e52;
  --line: #e2d5c4;
  --lab: #2f5d3a;
  --lab-soft: #e7f2ea;
  --paddle: #8a4b12;
  --paddle-soft: #f8ead8;
  --dich: #1f4e79;
  --dich-soft: #e4eef8;
}
* { box-sizing: border-box; }
body { margin: 0; font-family: "Source Sans 3", "Segoe UI", sans-serif; background: var(--bg); color: var(--ink); }
header { background: #2c241c; color: #f7f0e6; padding: 1.1rem 1.4rem 1.25rem; }
header a { color: #e8d5b5; }
header h1 { margin: 0 0 .25rem; font-size: 1.35rem; font-weight: 650; }
header .han { font-family: "Songti SC", "Noto Serif SC", "Source Han Serif SC", serif; font-size: 1.15rem; font-weight: 500; }
header p { margin: 0; color: #d9cbb8; font-size: .92rem; }
.back { display: inline-block; margin-bottom: .45rem; font-size: .88rem; color: #d9cbb8; text-decoration: none; }
.back:hover { color: #fff; }
main { padding: 1rem 1.4rem 3rem; max-width: 1400px; margin: 0 auto; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: .7rem; margin: .8rem 0 1.2rem; }
.card { background: var(--paper); border: 1px solid var(--line); border-radius: 10px; padding: .75rem .9rem; }
.card b { display: block; font-size: 1.35rem; }
.card span { color: var(--muted); font-size: .82rem; }
.filters { display: flex; gap: .5rem; flex-wrap: wrap; margin: 0 0 1rem; }
.filters label { background: var(--paper); border: 1px solid var(--line); padding: .25rem .55rem; border-radius: 999px; font-size: .85rem; }
.section-title { margin: 1.4rem 0 .7rem; font-size: 1.05rem; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 1rem; }
.book-card {
  display: flex; flex-direction: column; background: var(--paper);
  border: 1px solid var(--line); border-radius: 12px; overflow: hidden;
  text-decoration: none; color: inherit; min-height: 100%;
}
.book-card:hover { border-color: #c4b39a; box-shadow: 0 6px 18px rgba(44,36,28,.08); }
.book-card .thumb { height: 210px; background: #ddd2c3; overflow: hidden; }
.book-card .thumb img { width: 100%; height: 100%; object-fit: cover; object-position: top center; display: block; }
.book-card .thumb.empty { display: flex; align-items: center; justify-content: center; color: var(--muted); font-size: .9rem; padding: 1rem; text-align: center; }
.book-card .meta { padding: .75rem .85rem 1rem; flex: 1; }
.book-card .han { font-family: "Songti SC", "Noto Serif SC", serif; font-size: 1.12rem; margin: 0 0 .15rem; }
.book-card h2 { margin: 0 0 .35rem; font-size: .98rem; font-weight: 600; line-height: 1.3; }
.book-card .muted { color: var(--muted); font-size: .8rem; }
.pills { display: flex; flex-wrap: wrap; gap: .28rem; margin-top: .45rem; }
.tag { display: inline-block; padding: .08rem .45rem; border-radius: 999px; font-size: .72rem; background: #efe6d8; }
.tag.on { background: var(--lab-soft); color: var(--lab); }
.tag.warn { background: #f8e0e0; }
.tag.bia { background: #eee; } .tag.tua { background: #e7f2ea; } .tag.tho { background: #f8ead8; }
.tag.pha { background: #e4eef8; } .tag.doi { background: #fde7d8; } .tag.van { background: #f8e0e0; }
.note { font-size: .88rem; color: var(--muted); margin: .4rem 0 1rem; }
.path { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .78rem; color: #3d342b; word-break: break-all; }
table { width: 100%; border-collapse: collapse; background: var(--paper); border: 1px solid var(--line); font-size: .9rem; }
th, td { padding: .45rem .55rem; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
th { background: #efe6d8; font-weight: 600; }
tr.clickable { cursor: pointer; }
tr.clickable:hover { background: #f3e9da; }
.bar { height: 8px; background: #eadfce; border-radius: 99px; overflow: hidden; min-width: 72px; display: inline-block; vertical-align: middle; }
.bar > i { display: block; height: 100%; background: var(--lab); }
.bar.paddle > i { background: var(--paddle); }
.compare { display: grid; grid-template-columns: 220px 1fr; gap: 1rem; }
.plist { background: var(--paper); border: 1px solid var(--line); border-radius: 10px; max-height: 78vh; overflow: auto; }
.plist button { display: block; width: 100%; text-align: left; border: 0; border-bottom: 1px solid var(--line); background: transparent; padding: .55rem .7rem; cursor: pointer; font: inherit; }
.plist button.on { background: var(--lab-soft); }
.viewer h2 { margin: 0 0 .4rem; font-size: 1.05rem; }
.toggles { display: flex; gap: .5rem; flex-wrap: wrap; margin: .4rem 0 .8rem; }
.toggles label { background: var(--paper); border: 1px solid var(--line); padding: .25rem .55rem; border-radius: 999px; font-size: .85rem; }
.imgs, .texts { display: grid; grid-template-columns: repeat(3, 1fr); gap: .6rem; }
.texts { margin-top: .7rem; }
.pane { background: var(--paper); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; min-height: 120px; }
.pane h3 { margin: 0; padding: .45rem .6rem; font-size: .82rem; }
.pane.lab h3 { background: var(--lab-soft); color: var(--lab); }
.pane.paddle h3 { background: var(--paddle-soft); color: var(--paddle); }
.pane.dich h3 { background: var(--dich-soft); color: var(--dich); }
.pane img { width: 100%; display: block; background: #ddd2c3; }
.pane pre { margin: 0; padding: .65rem .7rem 1rem; white-space: pre-wrap; word-break: break-word; font-size: .86rem; line-height: 1.5; max-height: 420px; overflow: auto; font-family: "Noto Serif", "Songti SC", "Source Han Serif", serif; }
.files { margin-top: .8rem; background: var(--paper); border: 1px dashed var(--line); border-radius: 10px; padding: .7rem .8rem; }
.files li { margin: .2rem 0; }
.muted { color: var(--muted); }
.hidden { display: none !important; }
.empty-book { background: var(--paper); border: 1px dashed var(--line); border-radius: 12px; padding: 1.5rem; }
.analysis-md { background: var(--paper); border: 1px solid var(--line); border-radius: 12px; padding: 1rem 1.1rem 1.2rem; margin: 0 0 1.2rem; }
.analysis-md h2 { margin: 0 0 .6rem; font-size: 1.05rem; }
.analysis-md h3 { margin: 1rem 0 .35rem; font-size: .92rem; }
.analysis-md ul { margin: .2rem 0 .4rem; padding-left: 1.2rem; }
.analysis-md li { margin: .22rem 0; line-height: 1.45; }
#docx-stats { margin: 0 0 1.4rem; }
#docx-stats h2 { margin: 1.2rem 0 .5rem; font-size: 1.05rem; }
@media (max-width: 980px) {
  .compare, .imgs, .texts { grid-template-columns: 1fr; }
}
"""

INDEX_TEMPLATE = r"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Gia phả Hán-Nôm</title>
  <link rel="stylesheet" href="hannom-viewer.css" />
</head>
<body>
  <header>
    <h1>Gia phả Hán-Nôm</h1>
    <p>Danh sách các cuốn local. Bấm một cuốn để xem phân tích trang — ảnh, OCR, phiên âm / dịch — như Gia phả chí.</p>
  </header>
  <main>
    <section id="overview"></section>
    <section id="read-sources"></section>
    <section id="docx-stats"></section>
    <div class="filters" id="filters"></div>
    <section id="library"></section>
  </main>
  <script id="data" type="application/json">__DATA__</script>
  <script>
    const DATA = JSON.parse(document.getElementById("data").textContent);
    const esc = (s) => String(s ?? "").replace(/[&<>]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
    const $ = (id) => document.getElementById(id);

    const GROUPS = [
      { key: "gia_pha", title: "Gia phả" },
      { key: "gia_pha_dich", title: "Gia phả (bản dịch Word)" },
      { key: "ke_uoc", title: "Kế ước / văn khế" },
      { key: "gia_pha_photo", title: "Gia phả (ảnh Quốc ngữ)" },
      { key: "the_pha_print", title: "Thế phả Quốc ngữ in" },
      { key: "ly_thuyet", title: "Sách lý thuyết đã đọc" },
      { key: "tong_pho_pdf", title: "Tông phả (PDF Hán)" },
      { key: "su_lieu", title: "Sử liệu" },
    ];

    function pill(ok, label) {
      return `<span class="tag ${ok ? "on" : ""}">${label}${ok ? "" : " —"}</span>`;
    }

    function card(b) {
      const cover = b.cover && b.cover.rel_html
        ? `<div class="thumb"><img src="${esc(b.cover.rel_html)}" alt="" /></div>`
        : `<div class="thumb empty">${b.source === "local_docx" ? "Bản dịch Word<br/>chưa có ảnh scan" : b.kind === "ly_thuyet" ? "Sách lý thuyết" : "Chưa có ảnh"}</div>`;
      const flags = (b.flags || []).includes("missing_pages")
        ? `<span class="tag warn">thiếu ảnh</span>`
        : (b.flags || []).includes("no_scan") ? `<span class="tag">Word</span>` : "";
      const ocr = b.ocr || {};
      return `<a class="book-card" href="${esc(b.href)}" data-kind="${esc(b.kind)}" data-src="${esc(b.source)}">
        ${cover}
        <div class="meta">
          <div class="han">${esc(b.title_han || "")}</div>
          <h2>${esc(b.title_vn)}</h2>
          <div class="muted">${esc(b.clan_label)} · ${b.page_count == null ? "—" : b.page_count} ${b.source === "local_docx" ? "trang Word" : "trang"}</div>
          <div class="pills">
            <span class="tag">${esc(b.kind_label)}</span>
            ${pill(ocr.lab, "lab")}
            ${pill(ocr.paddle, "Paddle")}
            ${pill(ocr.dich, "dịch")}
            ${flags}
            ${(b.read_status === "da_doc" || (b.flags || []).includes("da_doc")) ? `<span class="tag on">đã đọc</span>` : ""}
          </div>
        </div>
      </a>`;
    }

    function render() {
      const s = DATA.catalog_summary || {};
      $("overview").innerHTML = `
        <p class="note">Sinh lúc ${esc(DATA.generated_at)}. Catalog: <span class="path">${esc(DATA.paths.books_catalog)}</span></p>
        <div class="cards">
          <div class="card"><b>${s.n_gia_pha || 0}</b><span>gia phả (ảnh)</span></div>
          <div class="card"><b>${s.n_docx || 0}</b><span>bản dịch Word</span></div>
          <div class="card"><b>${s.n_books || 0}</b><span>cuốn catalog</span></div>
          <div class="card"><b>${s.pages_local || 0}</b><span>trang ảnh</span></div>
          <div class="card"><b>${s.pages_word || 0}</b><span>trang Word</span></div>
          <div class="card"><b>${s.ocr_paddle || 0}/${s.n_books || 0}</b><span>đã OCR Paddle</span></div>
          <div class="card"><b>${s.ocr_dich || 0}/${s.n_books || 0}</b><span>đã phiên âm / dịch</span></div>
          <div class="card"><b>${s.n_ly_thuyet || 0}</b><span>sách lý thuyết</span></div>
          <div class="card"><b>${s.n_da_doc || 0}</b><span>đã đọc kỹ</span></div>
        </div>
      `;
      const web = DATA.web_sources || [];
      const theory = (DATA.books || []).filter((b) => b.kind === "ly_thuyet");
      const readBooks = (DATA.books || []).filter((b) => b.read_status === "da_doc" || (b.flags || []).includes("da_doc"));
      $("read-sources").innerHTML = `
        <h2 class="section-title">Nguồn sách / tư liệu đã đọc</h2>
        <p class="note">Lý thuyết (không OCR) + cuốn corpus đã đọc kỹ + nguồn web đã khảo sát (Firecrawl 08/2026).</p>
        <h3 class="section-title" style="margin-top:.4rem">Sách lý thuyết trong <span class="path">data/04_external/sach/</span></h3>
        <table>
          <thead><tr><th>Sách</th><th>Trang PDF</th><th>File</th><th>Ghi chú</th></tr></thead>
          <tbody>
            ${theory.map((b) => `<tr>
              <td><a href="${esc(b.href)}">${esc(b.title_vn)}</a></td>
              <td>${b.page_count == null ? "—" : b.page_count}</td>
              <td class="path">${esc((b.paths && b.paths.pdf) || "")}</td>
              <td>${esc(b.notes || "")}</td>
            </tr>`).join("") || `<tr><td colspan="4" class="muted">Chưa có PDF trong data/04_external/sach</td></tr>`}
          </tbody>
        </table>
        <h3 class="section-title">Corpus đã đọc kỹ</h3>
        <table>
          <thead><tr><th>Cuốn</th><th>Loại</th><th>Ghi chú</th></tr></thead>
          <tbody>
            ${readBooks.filter((b) => b.kind !== "ly_thuyet").map((b) => `<tr>
              <td><a href="${esc(b.href)}">${esc(b.title_vn)}</a> <span class="muted path">${esc(b.book_id)}</span></td>
              <td>${esc(b.kind_label)}</td>
              <td>${esc(b.notes || "")}</td>
            </tr>`).join("")}
          </tbody>
        </table>
        <h3 class="section-title">Nguồn web đã khảo sát</h3>
        <table>
          <thead><tr><th>Nguồn</th><th>Track</th><th>Quyết định</th><th>Điểm</th><th>URL</th></tr></thead>
          <tbody>
            ${web.map((w) => `<tr>
              <td>${esc(w.name || w.source_id)}</td>
              <td>${esc(w.track || "")}</td>
              <td>${esc(w.source_decision || w.status || "")}</td>
              <td>${w.feasibility_score == null ? "—" : w.feasibility_score}</td>
              <td>${w.base_url ? `<a href="${esc(w.base_url)}">${esc(w.base_url)}</a>` : "—"}</td>
            </tr>`).join("")}
          </tbody>
        </table>
      `;
      const analyses = DATA.docx_analyses || [];
      if (analyses.length) {
        const num = (x) => x == null ? "—" : Number(x).toLocaleString("vi");
        $("docx-stats").innerHTML = `
          <h2 class="section-title">Thống kê Word 24/08/2026 <span class="muted">(${analyses.length} cuốn)</span></h2>
          <p class="note">Bản dịch / phiên âm — không đếm vào trang ảnh, không OCR.
            Markdown: <span class="path">data/00_raw/du_lieu_han_nom_moi/24_8_2026/</span>
            ${DATA.paths.thong_ke_md ? `· <a href="${esc(DATA.paths.thong_ke_md)}">thong_ke.md</a>` : ""}</p>
          <table>
            <thead><tr>
              <th>Cuốn</th><th>Họ</th><th>Trang Word</th><th>Đoạn</th><th>Ký tự</th>
                  <th>Hán/Nôm</th><th>Năm gốc</th><th>Năm dịch</th><th>MD</th>
            </tr></thead>
            <tbody>
              ${analyses.map((a) => {
                const st = a.stats || {};
                const book = (DATA.books || []).find((x) => x.book_id === a.book_id) || {};
                const md = book.analysis_href || "";
                const full = book.fulltext_href || "";
                return `<tr>
                  <td><a href="${esc(book.href || "#")}">${esc(a.title_vn || a.book_id)}</a><div class="muted path">${esc(a.book_id)}</div></td>
                  <td>${esc(book.clan_label || a.clan_key || "")}</td>
                  <td>${num(st.word_pages)}</td>
                  <td>${num(st.paras)}</td>
                  <td>${num(st.chars)}</td>
                  <td>${num(st.cjk_chars)}</td>
                  <td>${esc(a.year_source || "—")}</td>
                  <td>${esc(a.year_translate || "—")}</td>
                  <td>${md ? `<a href="${esc(md)}">phân tích</a>` : "—"}${full ? ` · <a href="${esc(full)}">toàn văn</a>` : ""}</td>
                </tr>`;
              }).join("")}
            </tbody>
          </table>
        `;
      }
      $("filters").innerHTML = `
        <label><input type="checkbox" data-kind="gia_pha" checked /> Gia phả</label>
        <label><input type="checkbox" data-kind="gia_pha_dich" checked /> Word dịch</label>
        <label><input type="checkbox" data-kind="ly_thuyet" checked /> Lý thuyết</label>
        <label><input type="checkbox" data-kind="tong_pho_pdf" checked /> Tông phả PDF Hán</label>
        <label><input type="checkbox" data-kind="the_pha_print" checked /> Thế phả Quốc ngữ in</label>
        <label><input type="checkbox" data-kind="ke_uoc" checked /> Kế ước</label>
        <label><input type="checkbox" data-kind="gia_pha_photo" checked /> Ảnh Quốc ngữ</label>
        <label><input type="checkbox" data-kind="su_lieu" checked /> Sử liệu</label>
      `;
      const on = {};
      $("filters").querySelectorAll("input").forEach((inp) => {
        on[inp.dataset.kind] = inp.checked;
        inp.onchange = drawLibrary;
      });
      drawLibrary();
    }

    function drawLibrary() {
      const on = {};
      $("filters").querySelectorAll("input").forEach((inp) => { on[inp.dataset.kind] = inp.checked; });
      const books = DATA.books || [];
      $("library").innerHTML = GROUPS.map((g) => {
        if (!on[g.key]) return "";
        const rows = books.filter((b) => b.kind === g.key);
        if (!rows.length) return "";
        return `<h2 class="section-title">${g.title} <span class="muted">(${rows.length})</span></h2>
          <div class="grid">${rows.map(card).join("")}</div>`;
      }).join("");
    }

    render();
  </script>
</body>
</html>
"""

BOOK_TEMPLATE = r"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>__TITLE__</title>
  <link rel="stylesheet" href="../hannom-viewer.css" />
</head>
<body>
  <header>
    <a class="back" href="../index.html">← Tất cả gia phả</a>
    <div class="han">__HAN__</div>
    <h1>__VN__</h1>
    <p id="sub"></p>
  </header>
  <main>
    <section id="summary"></section>
    <section id="compare"></section>
  </main>
  <script id="data" type="application/json">__DATA__</script>
  <script>
    const DATA = JSON.parse(document.getElementById("data").textContent);
    const esc = (s) => String(s ?? "").replace(/[&<>]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
    const $ = (id) => document.getElementById(id);
    const pct = (x) => x == null ? "—" : Math.round(x * 100) + "%";
    const bar = (x, kind) => x == null ? "—" : `<div class="bar ${kind||""}"><i style="width:${Math.max(0,Math.min(100,x*100))}%"></i></div>`;
    const tagClass = { "bìa":"bia", "tựa":"tua", "thờ":"tho", "phả ký":"pha", "đời sau":"doi", "văn tế":"van" };
    const b = DATA.book || {};
    const pages = DATA.pages || [];
    const hasLab = DATA.has_lab > 0;
    let current = 0;
    let show = { image: true, lab: hasLab, paddle: true, dich: true };

    const textDoc = DATA.text_doc;
    const stats = b.text_stats || {};

    document.getElementById("sub").textContent =
      [b.clan_label, b.kind_label, DATA.n_pages ? DATA.n_pages + " trang ảnh" : (stats.word_pages ? stats.word_pages + " trang Word" : ""), b.catalog_code, b.notes].filter(Boolean).join(" · ");

    function img(file, alt) {
      return file && file.rel_html
        ? `<img src="${esc(file.rel_html)}" alt="${esc(alt)}" />`
        : `<p class="muted" style="padding:1rem">Không có file</p>`;
    }

    if (textDoc && textDoc.sections) {
      const secs = textDoc.sections;
      const a = DATA.analysis || {};
      const bullets = (items) => items && items.length ? `<ul>${items.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : "";
      const mdLink = DATA.analysis_href
        ? `<a href="${esc(DATA.analysis_href)}">${esc((DATA.paths.analysis || "").split("/").pop() || "phân tích.md")}</a>`
        : "";
      const fullLink = DATA.fulltext_href
        ? `<a href="${esc(DATA.fulltext_href)}">${esc((DATA.paths.fulltext || "").split("/").pop() || "toàn văn.md")}</a>`
        : "";
      $("summary").innerHTML = `
        <div class="cards">
          <div class="card"><b>${stats.word_pages || "—"}</b><span>trang Word</span></div>
          <div class="card"><b>${stats.paras || textDoc.paras || "—"}</b><span>đoạn</span></div>
          <div class="card"><b>${(stats.chars || 0).toLocaleString("vi")}</b><span>ký tự</span></div>
          <div class="card"><b>${(stats.cjk_chars || 0).toLocaleString("vi")}</b><span>chữ Hán/Nôm</span></div>
          <div class="card"><b>${stats.unique_cjk || 0}</b><span>Hán/Nôm khác nhau</span></div>
          <div class="card"><b>${secs.length}</b><span>phần trong file</span></div>
        </div>
        <div class="analysis-md">
          <h2>Phân tích</h2>
          <p class="note">${esc(a.loai_guess || b.notes || "")} ${mdLink ? "· Phân tích: " + mdLink : ""}${fullLink ? " · Toàn văn: " + fullLink : ""}</p>
          <h3>Nội dung phả hệ</h3>
          ${bullets(a.noi_dung)}
          <h3>Địa danh</h3>
          ${bullets(a.dia_danh)}
          <h3>Pipeline</h3>
          ${bullets(a.pipeline)}
          <h3>Hạn chế</h3>
          ${bullets(a.han_che)}
        </div>
        <p class="note">File Word: <span class="path">${esc(DATA.paths.docx || DATA.paths.root)}</span></p>
        <table>
          <thead><tr><th>Phần</th><th>Đoạn</th><th>Ký tự</th></tr></thead>
          <tbody>
            ${secs.map((s, i) => `<tr class="clickable" data-i="${i}">
              <td>${esc(s.title)}</td><td>${s.n_paras}</td><td>${(s.chars||0).toLocaleString("vi")}</td>
            </tr>`).join("")}
          </tbody>
        </table>
      `;
      $("compare").innerHTML = `
        <div class="compare">
          <div class="plist">
            ${secs.map((s, i) => `<button data-i="${i}">${esc(s.title)}
              <div class="muted">${s.n_paras} đoạn · ${(s.chars||0).toLocaleString("vi")} ký tự</div>
            </button>`).join("")}
          </div>
          <div id="page-view" class="viewer"></div>
        </div>
      `;
      const showSec = (i) => {
        const s = secs[i];
        if (!s) return;
        $("compare").querySelectorAll(".plist button").forEach((btn) => btn.classList.toggle("on", Number(btn.dataset.i) === i));
        $("page-view").innerHTML = `<h2>${esc(s.title)}</h2><div class="pane dich"><pre>${esc(s.text || "")}</pre></div>`;
      };
      $("summary").querySelectorAll("tr.clickable").forEach((tr) => {
        tr.onclick = () => { showSec(Number(tr.dataset.i)); $("compare").scrollIntoView({behavior:"smooth", block:"start"}); };
      });
      $("compare").querySelectorAll(".plist button").forEach((btn) => {
        btn.onclick = () => showSec(Number(btn.dataset.i));
      });
      showSec(0);
    } else if (!pages.length) {
      const pdfHref = DATA.pdf_href;
      $("summary").innerHTML = `<div class="empty-book">
        <p>${b.kind === "ly_thuyet" ? "Sách lý thuyết đã đọc — không phải corpus OCR." : "Cuốn này chưa có ảnh trang local (thiếu JPG)."}</p>
        <p>${esc(b.notes || "")}</p>
        <p class="path">${esc(DATA.paths.pdf || DATA.paths.pages || DATA.paths.root)}</p>
        ${pdfHref ? `<p><a href="${esc(pdfHref)}">Mở PDF</a></p>` : ""}
        ${DATA.paths.url ? `<p><a href="${esc(DATA.paths.url)}">${esc(DATA.paths.url)}</a></p>` : ""}
      </div>`;
    } else {
      $("summary").innerHTML = `
        <div class="cards">
          <div class="card"><b>${DATA.n_pages}</b><span>trang</span></div>
          <div class="card"><b>${DATA.has_lab}</b><span>OCR lab</span></div>
          <div class="card"><b>${DATA.has_paddle}</b><span>OCR Paddle</span></div>
          <div class="card"><b>${DATA.has_dich}</b><span>phiên âm / dịch</span></div>
          <div class="card"><b>${pct(DATA.lab_mean)}</b><span>lab μ (nếu có)</span></div>
          <div class="card"><b>${pct(DATA.paddle_mean)}</b><span>Paddle μ</span></div>
        </div>
        <p class="note">Bấm một trang để xem ảnh + chữ OCR + bản dịch, cùng kiểu với Gia phả chí.
          ${DATA.paths.url ? `Nguồn: <a href="${esc(DATA.paths.url)}">${esc(DATA.paths.url)}</a>.` : ""}
          Path: <span class="path">${esc(DATA.paths.root)}</span></p>
        <table>
          <thead><tr>
            <th>Trang</th><th>Bố cục</th><th>Lab</th><th>Lab μ</th>
            <th>Paddle</th><th>Paddle μ</th><th>Dịch</th>
          </tr></thead>
          <tbody>
            ${pages.map((p, i) => `
              <tr class="clickable" data-i="${i}">
                <td>${esc(p.stem)}</td>
                <td><span class="tag ${tagClass[p.section]||""}">${esc(p.section)}</span> ${esc(p.label)}</td>
                <td>${p.lab.n_lines || "—"}</td>
                <td>${bar(p.lab.mean)} ${pct(p.lab.mean)}</td>
                <td>${p.paddle.n_lines || "—"}</td>
                <td>${bar(p.paddle.mean,"paddle")} ${pct(p.paddle.mean)}</td>
                <td>${p.dich ? "có" : "—"}</td>
              </tr>`).join("")}
          </tbody>
        </table>
      `;
      $("summary").querySelectorAll("tr.clickable").forEach((tr) => {
        tr.onclick = () => { showPage(Number(tr.dataset.i)); $("compare").scrollIntoView({behavior:"smooth", block:"start"}); };
      });

      $("compare").innerHTML = `
        <div class="toggles">
          <label><input type="checkbox" data-k="image" checked /> Ảnh gốc</label>
          <label><input type="checkbox" data-k="lab" ${hasLab?"checked":""} /> Bbox lab (Kim Hán Nôm)</label>
          <label><input type="checkbox" data-k="paddle" checked /> Bbox Paddle</label>
          <label><input type="checkbox" data-k="dich" checked /> Phiên âm / dịch</label>
        </div>
        <div class="compare">
          <div class="plist">
            ${pages.map((p, i) => `<button data-i="${i}">
              ${esc(p.stem)} · ${esc(p.section)}
              <div class="muted">lab ${pct(p.lab.mean)} · paddle ${pct(p.paddle.mean)}</div>
            </button>`).join("")}
          </div>
          <div id="page-view" class="viewer"></div>
        </div>
      `;
      $("compare").querySelectorAll(".plist button").forEach((btn) => {
        btn.onclick = () => showPage(Number(btn.dataset.i));
      });
      $("compare").querySelectorAll(".toggles input").forEach((inp) => {
        inp.onchange = () => { show[inp.dataset.k] = inp.checked; showPage(current); };
      });
      showPage(0);
    }

    function showPage(i) {
      current = i;
      const p = pages[i];
      if (!p) return;
      $("compare").querySelectorAll(".plist button").forEach((btn) => btn.classList.toggle("on", Number(btn.dataset.i) === i));
      const vis = ["image","lab","paddle","dich"].filter((k) => show[k]);
      const cols = Math.max(1, vis.filter((k) => k === "image" || k === "lab").length);
      const textCols = Math.max(1, vis.filter((k) => k !== "image").length);
      const labImg = p.files.lab_bbox_preview || p.files.image;
      const padImg = p.files.paddle_preview;
      $("page-view").innerHTML = `
        <h2>Trang ${esc(p.stem)} — ${esc(p.label)}</h2>
        <p class="note">${esc(b.title_vn)} · lab ${esc(p.lab.engine || "—")}
          · paddle ${esc(p.paddle.model || "—")} ${p.paddle.elapsed_s ? "· "+p.paddle.elapsed_s+"s" : ""}</p>
        <div class="imgs" style="grid-template-columns:repeat(${cols},1fr)">
          <div class="pane dich ${show.image?"":"hidden"}"><h3>Ảnh gốc</h3>${img(p.files.image, "gốc")}</div>
          <div class="pane lab ${show.lab?"":"hidden"}"><h3>Bbox lab (Kim Hán Nôm)</h3>${hasLab ? img(labImg, "lab") : `<p class="muted" style="padding:1rem">Cuốn này chưa OCR lab — chỉ Gia phả chí có bbox Kim Hán Nôm.</p>`}</div>
          <div class="pane paddle ${show.paddle?"":"hidden"}"><h3>Bbox Paddle</h3>${padImg ? img(padImg, "paddle") : `<p class="muted" style="padding:1rem">Chưa có overlay Paddle</p>`}</div>
        </div>
        <div class="texts" style="grid-template-columns:repeat(${textCols},1fr)">
          <div class="pane lab ${show.lab?"":"hidden"}"><h3>OCR lab (${p.lab.n_lines} dòng, μ ${pct(p.lab.mean)})</h3><pre>${esc((p.lab.texts||[]).join("\n")) || "(chưa có OCR lab)"}</pre></div>
          <div class="pane paddle ${show.paddle?"":"hidden"}"><h3>OCR Paddle (${p.paddle.n_lines} dòng, μ ${pct(p.paddle.mean)})</h3><pre>${esc((p.paddle.texts||[]).join("\n")) || "(chưa có Paddle)"}</pre></div>
          <div class="pane dich ${show.dich?"":"hidden"}"><h3>Phiên âm / dịch</h3><pre>${esc(p.dich || "(chưa có bản dịch)")}</pre></div>
        </div>
        <div class="files">
          <strong>File trang ${esc(p.stem)}</strong>
          <ul>
            ${Object.entries(p.files).filter(([,f]) => f).map(([k,f]) =>
              `<li><strong>${esc(k)}</strong> — <span class="path">${esc(f.rel_repo)}</span></li>`
            ).join("")}
          </ul>
        </div>
      `;
    }
  </script>
</body>
</html>
"""


def render_index(data: dict[str, Any]) -> str:
    return INDEX_TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def render_book(payload: dict[str, Any]) -> str:
    book = payload.get("book") or {}
    html = BOOK_TEMPLATE.replace("__DATA__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    title = book.get("title_vn") or book.get("book_id") or "Gia phả"
    html = html.replace("__TITLE__", html_lib.escape(title))
    html = html.replace("__HAN__", html_lib.escape(book.get("title_han") or ""))
    html = html.replace("__VN__", html_lib.escape(title))
    return html


def main() -> int:
    repo = repo_root()
    catalog_path = write_catalog(repo)
    catalog = load_json(catalog_path) or {"books": []}
    books = catalog.get("books") or []

    print("Word analysis MD:")
    docx_analyses = write_docx_analyses(repo, books, load_docx_text)
    catalog["books"] = books
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    hannom_dir = repo / "data/00_raw/hannom"
    books_dir = hannom_dir / "books"
    books_dir.mkdir(parents=True, exist_ok=True)
    (hannom_dir / "hannom-viewer.css").write_text(CSS.strip() + "\n", encoding="utf-8")

    index_books = [enrich_book(b, hannom_dir, repo) for b in books]
    index_books.sort(
        key=lambda b: (
            0 if b["book_id"] == "gpc-dang-1928"
            else 1 if b.get("kind") == "gia_pha"
            else 2 if b.get("kind") == "gia_pha_dich"
            else 3 if b.get("kind") == "ly_thuyet"
            else 4 if b.get("kind") == "tong_pho_pdf"
            else 5 if b.get("kind") == "ke_uoc"
            else 6 if b.get("kind") == "the_pha_print"
            else 7,
            int(b.get("volume_id") or 0),
            b["book_id"],
        )
    )
    index_data = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "books": index_books,
        "catalog_summary": catalog_summary(books),
        "docx_analyses": docx_analyses,
        "web_sources": (load_json(repo / "data/05_ops/sources_discovery/sources_registry.json") or {}).get("sources") or [],
        "paths": {
            "books_catalog": "data/00_raw/hannom/books_catalog.json",
            "repo_data": str(repo / "data"),
            "thong_ke_md": rel_to(repo / "data/00_raw/du_lieu_han_nom_moi/24_8_2026/thong_ke.md", hannom_dir),
        },
    }
    index_path = hannom_dir / "index.html"
    index_path.write_text(render_index(index_data), encoding="utf-8")
    print(f"Wrote {index_path}")

    for book in books:
        pages = collect_pages(book, books_dir, repo)
        payload = book_payload(book, pages, books_dir, repo)
        out = books_dir / f"{book['book_id']}.html"
        out.write_text(render_book(payload), encoding="utf-8")
        print(f"  {book['book_id']}: {len(pages)} trang → {out.relative_to(repo)}")

    old = repo / "data/00_raw/du_lieu_han_nom_moi/thong_ke_han_nom.html"
    old.write_text(
        "<!DOCTYPE html><meta charset='utf-8'>"
        "<meta http-equiv='refresh' content='0; url=../hannom/index.html'>"
        "<p><a href='../hannom/index.html'>Danh sách gia phả Hán-Nôm</a></p>\n",
        encoding="utf-8",
    )
    print(f"Wrote redirect {old}")
    print(f"Open: {index_path.resolve().as_uri()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
