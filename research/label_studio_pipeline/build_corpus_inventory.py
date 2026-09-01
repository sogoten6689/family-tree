#!/usr/bin/env python3
"""Quét corpus `data/` và ghi tổng quan sống (MD + JSON).

Không đi theo shortcut ở `data/` (vgp_corpus, hannom, …) — chỉ tầng 00_raw … 05_ops.

Từ root repo:

  PYTHONPATH=research python -m label_studio_pipeline.build_corpus_inventory
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from label_studio_pipeline.data_layout import (
    DATA_ROOT,
    DERIVED_GIA_PHA,
    DERIVED_LABELED_CORPUS,
    DERIVED_MANIFESTS,
    GOLD_LABELS,
    GOLD_STRATIFIED,
    HANNOM_CATALOG,
    INTERIM_GEMINI_LABELS,
    RAW_GIAPHATPHCM,
    RAW_VGP_CORPUS,
    REPO_ROOT,
)

TIERS = ("00_raw", "01_interim", "02_gold", "03_derived", "04_external", "05_ops")
SKIP_DIRS = {".git", "__pycache__", ".venv"}
IGNORE_FILES = {".DS_Store", ".gitattributes", ".gitignore", ".lfsconfig"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".gif", ".bmp"}
MEDIA_EXT = {
    "image": IMAGE_EXT,
    "pdf": {".pdf"},
    "docx": {".docx", ".doc"},
    "text": {".txt", ".md"},
    "json": {".json"},
    "html": {".html", ".htm"},
    "zip": {".zip"},
    "sqlite": {".sqlite3", ".db"},
}

INVENTORY_MD = DATA_ROOT / "DATA_INVENTORY.md"
INVENTORY_JSON = DERIVED_MANIFESTS / "corpus_inventory.json"

PAGE_STEM_RE = re.compile(r"^(\d{1,4})$")
PAREN1_RE = re.compile(r"\(\s*1\s*\)", re.I)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def fmt_mb(n: int) -> str:
    mb = n / 1024 / 1024
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb:.1f} MB"


def walk_files(root: Path) -> Iterable[Path]:
    if not root.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        pdir = Path(dirpath)
        if ".git" in pdir.parts:
            continue
        for fn in filenames:
            if fn in IGNORE_FILES:
                continue
            fp = pdir / fn
            if fp.is_file() and not fp.is_symlink():
                yield fp


def ext_of(path: Path) -> str:
    return path.suffix.lower() or "(none)"


def media_kind(ext: str) -> str:
    for kind, exts in MEDIA_EXT.items():
        if ext in exts:
            return kind
    return "other"


def is_ocr_sidecar_image(path: Path) -> bool:
    name = path.name.lower()
    parts = {p.lower() for p in path.parts}
    if "boundingbox" in name or "ocr_res" in name:
        return True
    if "paddleocr" in parts and "preview" in parts:
        return True
    return False


def is_source_page_image(path: Path) -> bool:
    if ext_of(path) not in IMAGE_EXT:
        return False
    if is_ocr_sidecar_image(path):
        return False
    return True


def is_paren1(path: Path) -> bool:
    return bool(PAREN1_RE.search(path.stem))


def load_json(path: Path) -> Any | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def rel(path: Path) -> str:
    try:
        return path.relative_to(DATA_ROOT).as_posix()
    except ValueError:
        return path.relative_to(REPO_ROOT).as_posix()


def scan_tier(tier: str) -> dict[str, Any]:
    root = DATA_ROOT / tier
    collections: list[dict[str, Any]] = []
    totals = Counter()
    bytes_total = 0
    files_total = 0
    if not root.is_dir():
        return {
            "tier": tier,
            "files": 0,
            "bytes": 0,
            "by_media": {},
            "collections": [],
        }
    kids = sorted(
        p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")
    )
    if not kids:
        kids = [root]
    for child in kids:
        by_media: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "bytes": 0})
        n_files = 0
        n_bytes = 0
        n_source_img = 0
        n_sidecar_img = 0
        for fp in walk_files(child):
            try:
                size = fp.stat().st_size
            except OSError:
                continue
            n_files += 1
            n_bytes += size
            kind = media_kind(ext_of(fp))
            by_media[kind]["count"] += 1
            by_media[kind]["bytes"] += size
            totals[kind] += 1
            if ext_of(fp) in IMAGE_EXT:
                if is_source_page_image(fp):
                    n_source_img += 1
                else:
                    n_sidecar_img += 1
        files_total += n_files
        bytes_total += n_bytes
        collections.append(
            {
                "name": child.name if child != root else "(root)",
                "path": rel(child),
                "files": n_files,
                "bytes": n_bytes,
                "source_images": n_source_img,
                "sidecar_images": n_sidecar_img,
                "by_media": dict(by_media),
            }
        )
    return {
        "tier": tier,
        "files": files_total,
        "bytes": bytes_total,
        "by_media": dict(totals),
        "collections": collections,
    }


def vgp_stats() -> dict[str, Any]:
    root = RAW_VGP_CORPUS
    tree_dirs = [p for p in root.iterdir() if p.is_dir() and p.name.isdigit()] if root.is_dir() else []
    n_valid = 0
    n_ky = n_he = 0
    for td in tree_dirs:
        ky = td / "pha_ky.txt"
        he = td / "pha_he.json"
        has_ky = ky.is_file()
        has_he = he.is_file()
        if has_ky:
            n_ky += 1
        if has_he:
            n_he += 1
        if not (has_ky and has_he):
            continue
        try:
            nchars = len(ky.read_text(encoding="utf-8", errors="replace").strip())
        except OSError:
            nchars = 0
        obj = load_json(he) or {}
        nodes = 0
        if isinstance(obj, dict):
            nodes = int(obj.get("node_count") or 0) or len(
                obj.get("nodes") or obj.get("members") or []
            )
        elif isinstance(obj, list):
            nodes = len(obj)
        if nchars >= 200 and nodes > 0:
            n_valid += 1
    gia = (
        [p for p in DERIVED_GIA_PHA.iterdir() if p.is_dir() and p.name.isdigit()]
        if DERIVED_GIA_PHA.is_dir()
        else []
    )
    return {
        "tree_dirs": len(tree_dirs),
        "pha_ky": n_ky,
        "pha_he": n_he,
        "valid_narrative_and_tree": n_valid,
        "gia_pha_export": len(gia),
        "unit": "cây (tree_id)",
        "valid_rule": "pha_ky.txt ≥ 200 ký tự AND pha_he.json node_count > 0",
    }


def gold_stats() -> dict[str, Any]:
    dirs = [
        p for p in GOLD_LABELS.iterdir() if p.is_dir() and p.name.isdigit()
    ] if GOLD_LABELS.is_dir() else []
    n_ent = sum(1 for d in dirs if (d / "gold.entities.json").is_file())
    stratified = load_json(GOLD_STRATIFIED) or {}
    counts = stratified.get("counts") if isinstance(stratified, dict) else {}
    train = load_json(DERIVED_LABELED_CORPUS / "v1" / "splits" / "train_ids.json") or {}
    test = load_json(DERIVED_LABELED_CORPUS / "v1" / "splits" / "test_ids.json") or {}
    gemini = [
        p for p in INTERIM_GEMINI_LABELS.iterdir() if p.is_dir() and p.name.isdigit()
    ] if INTERIM_GEMINI_LABELS.is_dir() else []
    labeled = load_json(DERIVED_MANIFESTS / "labeled_trees.json") or {}
    assess = load_json(DERIVED_MANIFESTS / "assessment_summary.json") or {}
    return {
        "gold_tree_dirs": len(dirs),
        "gold_with_entities": n_ent,
        "gemini_tree_dirs": len(gemini),
        "stratified_total": (counts or {}).get("total"),
        "stratified_counts": counts,
        "train_ids": train.get("doc_count"),
        "test_ids": test.get("doc_count"),
        "test_locked": test.get("locked"),
        "ls_imported_labeled_trees": labeled.get("selected_count"),
        "assessment_suitable": assess.get("suitable_count"),
        "assessment_assessed": assess.get("assessed_count"),
        "unit": "cây / document (1 Phả ký = 1 doc)",
    }


def hannom_catalog_stats() -> dict[str, Any]:
    cat = load_json(HANNOM_CATALOG) or {}
    books = cat.get("books") if isinstance(cat, dict) else []
    by_source = Counter(b.get("source") for b in books)
    by_kind = Counter(b.get("kind") for b in books)
    flags = Counter()
    for b in books:
        for f in b.get("flags") or []:
            flags[f] += 1
    n_pages_claimed = sum(int(b.get("page_count") or 0) for b in books if b.get("kind") != "ly_thuyet")
    return {
        "path": rel(HANNOM_CATALOG) if HANNOM_CATALOG.is_file() else None,
        "generated_at": cat.get("generated_at"),
        "n_books": cat.get("n_books") or len(books),
        "by_source": dict(by_source),
        "by_kind": dict(by_kind),
        "flags": dict(flags),
        "page_count_sum_non_theory": n_pages_claimed,
        "books": [
            {
                "book_id": b.get("book_id"),
                "kind": b.get("kind"),
                "source": b.get("source"),
                "title_vn": b.get("title_vn"),
                "page_count": b.get("page_count"),
                "flags": b.get("flags") or [],
                "ocr": b.get("ocr") or {},
            }
            for b in books
        ],
    }


def find_incoming_media() -> dict[str, Any]:
    """PDF / DOCX / image-lists trên đĩa, kể cả chưa có trong books_catalog."""
    pdfs: list[dict[str, Any]] = []
    docxs: list[dict[str, Any]] = []
    zips: list[dict[str, Any]] = []
    image_lists: list[dict[str, Any]] = []

    scan_roots = [
        DATA_ROOT / "00_raw",
        DATA_ROOT / "04_external",
    ]
    img_by_parent: dict[Path, list[Path]] = defaultdict(list)

    for root in scan_roots:
        for fp in walk_files(root):
            ext = ext_of(fp)
            size = fp.stat().st_size
            rec = {"path": rel(fp), "bytes": size, "name": fp.name}
            if ext == ".pdf":
                pdfs.append(rec)
            elif ext in {".docx", ".doc"}:
                docxs.append(rec)
            elif ext == ".zip":
                zips.append(rec)
            elif ext in IMAGE_EXT and is_source_page_image(fp) and not is_paren1(fp):
                img_by_parent[fp.parent].append(fp)

    for parent, files in sorted(img_by_parent.items(), key=lambda x: -len(x[1])):
        if len(files) < 3:
            continue
        if "paddleocr" in {p.lower() for p in parent.parts}:
            continue
        image_lists.append(
            {
                "path": rel(parent),
                "n_source_images": len(files),
                "bytes": sum(p.stat().st_size for p in files),
                "kind": "image_list",
            }
        )

    giapha = []
    if RAW_GIAPHATPHCM.is_dir():
        for child in sorted(RAW_GIAPHATPHCM.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                giapha.append(rel(child))

    return {
        "pdf": pdfs,
        "docx": docxs,
        "zip": zips,
        "image_lists": image_lists,
        "giaphatphcm_items": giapha,
    }


def nom_unique_pages() -> dict[str, Any]:
    """Đếm JPG nguồn (không gồm boundingbox-preview) theo volume Nom."""
    volumes = DATA_ROOT / "00_raw" / "hannom" / "nomfoundation" / "volumes"
    rows = []
    if not volumes.is_dir():
        return {"volumes": [], "source_pages_total": 0}
    for vol in sorted(volumes.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 10**9):
        if not vol.is_dir() or not vol.name.isdigit():
            continue
        pages = vol / "pages"
        folder = pages if pages.is_dir() else vol
        src = [
            p
            for p in folder.iterdir()
            if p.is_file() and is_source_page_image(p) and PAGE_STEM_RE.match(p.stem)
        ]
        all_img = [p for p in folder.iterdir() if p.is_file() and ext_of(p) in IMAGE_EXT]
        rows.append(
            {
                "volume_id": int(vol.name),
                "source_pages": len(src),
                "all_jpg_in_pages": len(all_img),
            }
        )
    return {
        "volumes": rows,
        "source_pages_total": sum(r["source_pages"] for r in rows),
        "note": "source_pages = stem số + .jpg, loại boundingbox-preview (catalog cũ từng đếm nhầm 2×)",
    }


def build_payload() -> dict[str, Any]:
    layers = [scan_tier(t) for t in TIERS]
    files = sum(t["files"] for t in layers)
    bytes_ = sum(t["bytes"] for t in layers)
    media_all: Counter[str] = Counter()
    for t in layers:
        media_all.update(t["by_media"])
    return {
        "generated_at": now_iso(),
        "schema": "corpus-inventory.v1",
        "data_root": "data/",
        "totals": {
            "files": files,
            "bytes": bytes_,
            "by_media": dict(media_all),
        },
        "layers": layers,
        "vgp": vgp_stats(),
        "gold": gold_stats(),
        "hannom_catalog": hannom_catalog_stats(),
        "nom_unique_pages": nom_unique_pages(),
        "incoming": find_incoming_media(),
    }


def md_escape(s: str) -> str:
    return (s or "").replace("|", "\\|")


def render_md(p: dict[str, Any]) -> str:
    t = p["totals"]
    v = p["vgp"]
    g = p["gold"]
    h = p["hannom_catalog"]
    nom = p["nom_unique_pages"]
    inc = p["incoming"]
    lines: list[str] = []
    a = lines.append

    a("# Corpus inventory — tổng quan dữ liệu nghiên cứu")
    a("")
    a(f"> **Sinh lúc:** `{p['generated_at']}` · schema `{p['schema']}`  ")
    a("> **File máy:** [`03_derived/manifests/corpus_inventory.json`](03_derived/manifests/corpus_inventory.json)  ")
    a("> **Không sửa tay số liệu** — chạy lại generator. Phân tích / protocol ở dưới được giữ trong script.")
    a("")
    a("```bash")
    a("PYTHONPATH=research python -m label_studio_pipeline.build_corpus_inventory")
    a("```")
    a("")
    a("Repo dữ liệu: `family-tree-data` (thư mục `data/` của `family-tree`).")
    a("")

    a("## 1. Cách đọc — đơn vị phân tích (bắt buộc)")
    a("")
    a("Không cộng file JPG với cây VGP thành một «n». Mỗi track một đơn vị:")
    a("")
    a("| Track | Đơn vị | Ví dụ | Metric luận văn |")
    a("|-------|--------|-------|-----------------|")
    a("| **A — Quốc ngữ NLP** | 1 cây = 1 `tree_id` = 1 Phả ký | `00_raw/vgp_corpus/122/` | gold NER/RE, split 80/20 |")
    a("| **B — Hán-Nôm OCR** | 1 cuốn (`book_id`) | `nom-1255`, `gpc-dang-1928` | trang scan, OCR lab/Paddle/dịch |")
    a("| **C — Lý thuyết** | 1 PDF sách | `04_external/sach/` | glossary loại/bố cục — **không** corpus gán nhãn |")
    a("| **D — Dịch Word** | 1 DOCX | `24_8_2026/*.docx` | extract cây từ Quốc ngữ; **không** OCR nếu không có scan |")
    a("| **E — Ảnh rời / list** | 1 thư mục ảnh = 1 cuốn incoming | `25_8_2026/Hương/…` | đếm JPG nguồn, loại `(1)` và preview OCR |")
    a("")
    a("**Tầng (00–05)** = giai đoạn xử lý, không phải loại file. Cùng một cuốn có thể có scan ở 00, OCR ở cạnh scan, copy review ở 03.")
    a("")
    a("| Tầng | Ý nghĩa | Được phép |")
    a("|------|---------|----------|")
    a("| 00 raw | Tư liệu gốc | Chỉ thêm, không sửa nội dung |")
    a("| 01 interim | Máy sinh (Gemini, synthetic, OCR nháp) | Xóa rồi chạy lại |")
    a("| 02 gold | Người duyệt | Số liệu chính bài |")
    a("| 03 derived | Export, split, review pack | Tính lại được |")
    a("| 04 external | Sách tham khảo | Không gán nhãn NER |")
    a("| 05 ops | Label Studio, discovery | Không trích dẫn như kết quả |")
    a("")

    a("## 2. Dashboard (quét đĩa, không follow symlink root)")
    a("")
    a("| Chỉ số | Giá trị |")
    a("|---------|---------|")
    a(f"| File (tầng 00–05) | **{fmt_int(t['files'])}** |")
    a(f"| Dung lượng | **{fmt_mb(t['bytes'])}** |")
    a(f"| Cây VGP raw | **{fmt_int(v['tree_dirs'])}** |")
    a(f"| Cây hợp lệ (Phả ký + phả hệ) | **{fmt_int(v['valid_narrative_and_tree'])}** |")
    a(f"| Export `gia_pha/` | **{fmt_int(v['gia_pha_export'])}** |")
    a(f"| Gold (thư mục `tree_id`) | **{fmt_int(g['gold_tree_dirs'])}** |")
    a(f"| Stratified MVP | **{g['stratified_total']}** doc (train {g['train_ids']} / test {g['test_ids']}, test locked={g['test_locked']}) |")
    a(f"| Catalog Hán-Nôm | **{h['n_books']}** cuốn (sinh `{h.get('generated_at') or '—'}`, **chưa gồm lô 25/08**) |")
    a(f"| Trang Nom nguồn (stem số, không preview) | **{fmt_int(nom['source_pages_total'])}** |")
    a(f"| PDF trên đĩa | **{len(inc['pdf'])}** |")
    a(f"| DOCX trên đĩa | **{len(inc['docx'])}** (có bản trùng MD5) |")
    a(f"| ZIP | **{len(inc['zip'])}** |")
    a(f"| Thư mục ảnh ≥3 file nguồn | **{len(inc['image_lists'])}** |")
    a("")
    a("### 2.1. File theo media")
    a("")
    a("| Media | Số file | Ghi chú |")
    a("|-------|--------:|---------|")
    notes = {
        "json": "cây, nhãn, OCR sidecar, catalog",
        "text": "pha_ky.txt + OCR txt + markdown phân tích",
        "image": "gồm cả preview bbox / Paddle — xem §6",
        "pdf": "tông phả + sách lý thuyết",
        "docx": "bản dịch / phiên âm",
        "html": "viewer catalog",
        "zip": "gói incoming (thường đã giải nén — đếm 1 lần)",
        "sqlite": "Label Studio ops",
        "other": "",
    }
    for kind, n in sorted(t["by_media"].items(), key=lambda x: -x[1]):
        a(f"| `{kind}` | {fmt_int(n)} | {notes.get(kind, '')} |")
    a("")

    a("## 3. Theo tầng")
    a("")
    for layer in p["layers"]:
        a(f"### {layer['tier']} — {fmt_int(layer['files'])} file · {fmt_mb(layer['bytes'])}")
        a("")
        a("| Collection | File | Dung lượng | Ảnh nguồn | Ảnh sidecar OCR |")
        a("|------------|-----:|-----------:|----------:|----------------:|")
        for c in layer["collections"]:
            a(
                f"| `{md_escape(c['path'])}` | {fmt_int(c['files'])} | {fmt_mb(c['bytes'])} "
                f"| {fmt_int(c['source_images'])} | {fmt_int(c['sidecar_images'])} |"
            )
        a("")

    a("## 4. Track A — Quốc ngữ (VGP) funnel")
    a("")
    a("```text")
    a(f"{fmt_int(v['tree_dirs'])} cây crawl")
    a(f"  → {fmt_int(v['valid_narrative_and_tree'])} hợp lệ = export gia_pha/")
    a("       ├─ máy: Gemini {g}  →  LS import {ls}  →  assessed suitable {suit}".format(
        g=fmt_int(g["gemini_tree_dirs"]),
        ls=g.get("ls_imported_labeled_trees") or "—",
        suit=g.get("assessment_suitable") or "—",
    ))
    a("       └─ người: {gold} thư mục gold trên đĩa (không phải tập con của LS import)".format(
        gold=fmt_int(g["gold_tree_dirs"]),
    ))
    a(f"            → {g['stratified_total']} stratified MVP  →  train {g['train_ids']} / test {g['test_ids']} (locked={g['test_locked']})")
    a("```")
    a("")
    a(f"- Quy tắc hợp lệ: `{v['valid_rule']}`.")
    a("- `pha_he.json` = **benchmark cấu trúc**, không phải gold NER.")
    a("- `01_interim/gemini_labels/` **không** trộn vào bảng số liệu chính.")
    a(f"- **{fmt_int(g['gold_tree_dirs'])} gold dirs ≠ 38 LS import.** Gold trên đĩa rộng hơn (curated / training dump). Số liệu bài: **{g['stratified_total']} stratified** (train {g['train_ids']} / test {g['test_ids']}).")
    a("- Manifest `research/label_studio_pipeline/THONG_KE.md` (2026-08-02: 1.263 cây / 189 hợp lệ) **lỗi thời** so với đĩa hiện tại.")
    a("")
    sc = g.get("stratified_counts") or {}
    if sc:
        a("| Stratum | n | Vai trò |")
        a("|---------|--:|---------|")
        a(f"| S1 relation-rich | {sc.get('S1', '—')} | train (+ test overlap IAA) |")
        a(f"| S2 medium | {sc.get('S2', '—')} | train |")
        a(f"| S3 hard | {sc.get('S3', '—')} | train |")
        a(f"| S4 held-out | {sc.get('S4', '—')} | **chỉ test**, khóa |")
        a(f"| Double annotation | {sc.get('double_annotation', '—')} | κ |")
        a("")

    a("## 5. Track B — Hán-Nôm / đa phương tiện")
    a("")
    a("### 5.1. Catalog cuốn (`books_catalog.json`)")
    a("")
    a(f"SSOT cuốn: `{h.get('path')}` · {h['n_books']} cuốn · sinh `{h.get('generated_at') or '—'}`.")
    a("")
    a("| Nguồn | Số cuốn |")
    a("|-------|--------:|")
    for src, n in sorted((h.get("by_source") or {}).items(), key=lambda x: -x[1]):
        a(f"| `{src}` | {n} |")
    a("")
    a("| book_id | Loại | Trang (catalog) | OCR lab/Paddle/dịch | Flags |")
    a("|---------|------|----------------:|---------------------|-------|")
    for b in h.get("books") or []:
        ocr = b.get("ocr") or {}
        flags = ",".join(b.get("flags") or []) or "—"
        a(
            f"| `{b.get('book_id')}` | {b.get('kind')} | {b.get('page_count') if b.get('page_count') is not None else '—'} "
            f"| {str(ocr.get('lab'))[0]}/{str(ocr.get('paddle'))[0]}/{str(ocr.get('dich'))[0]} "
            f"| {flags} |"
        )
    a("")
    a("Cột OCR: lab / Paddle / dich (`T`/`F`). Viewer: `data/00_raw/hannom/index.html`.")
    a("")
    a("### 5.2. Trang Nom — đếm đúng (không nhân đôi preview)")
    a("")
    a(nom.get("note") or "")
    a("")
    a("| volume | Trang nguồn | Mọi JPG trong `pages/` |")
    a("|-------:|------------:|-----------------------:|")
    for row in nom.get("volumes") or []:
        a(f"| {row['volume_id']} | {row['source_pages']} | {row['all_jpg_in_pages']} |")
    a(f"| **Tổng** | **{nom['source_pages_total']}** | |")
    a("")
    a("Nhiều `flags: mismatch` trong catalog là vì `count_images()` đếm cả `*-boundingbox-preview.jpg`. Số **trang nguồn** ở bảng này mới dùng khi viết bài.")
    a("")

    a("### 5.3. PDF trên đĩa")
    a("")
    a("| File | Dung lượng |")
    a("|------|-----------:|")
    for rec in inc["pdf"]:
        a(f"| `{md_escape(rec['path'])}` | {fmt_mb(rec['bytes'])} |")
    a("")

    a("### 5.4. DOCX trên đĩa")
    a("")
    a("| File | Dung lượng |")
    a("|------|-----------:|")
    for rec in inc["docx"]:
        a(f"| `{md_escape(rec['path'])}` | {fmt_mb(rec['bytes'])} |")
    a("")
    a("Lô `24_8_2026`: đã có `book_id` + `thong_ke.md`. Lô `25_8_2026/Hương`: có `inventory.md` **cục bộ**, **chưa** vào `books_catalog.json`.")
    a("")

    a("### 5.5. List ảnh (thư mục ≥ 3 JPG nguồn, loại preview Paddle)")
    a("")
    a("| Thư mục | Ảnh nguồn | Dung lượng |")
    a("|--------|----------:|-----------:|")
    for rec in inc["image_lists"]:
        a(f"| `{md_escape(rec['path'])}` | {rec['n_source_images']} | {fmt_mb(rec['bytes'])} |")
    a("")

    if inc.get("zip"):
        a("### 5.6. ZIP (gói incoming — đã giải nén thì không đếm nội dung zip thêm lần 2)")
        a("")
        for rec in inc["zip"]:
            a(f"- `{rec['path']}` · {fmt_mb(rec['bytes'])}")
        a("")

    if inc.get("giaphatphcm_items"):
        a("### 5.7. giaphatphcm.com (Quốc ngữ dựng lại — không trộn gold VGP, không OCR)")
        a("")
        for item in inc["giaphatphcm_items"]:
            a(f"- `{item}`")
        a("")

    a("## 6. Rủi ro đếm trùng & chất lượng")
    a("")
    a("| Hiện tượng | Hệ quả nếu đếm thô | Cách đếm đúng |")
    a("|------------|---------------------|---------------|")
    a("| Shortcut `data/vgp_corpus` → `00_raw/vgp_corpus` | Nhân đôi mọi số | Chỉ walk `00_raw`…`05_ops` |")
    a("| `review_corpus/hannom/{id}/pages` copy từ Nom | Nhân đôi trang | SSOT ảnh = `volumes/{id}/pages` |")
    a("| `*-boundingbox-preview.jpg` cạnh `001.jpg` | Catalog `page_count` ≈ 2× | Chỉ stem số |")
    a("| `paddleocr/preview/` | Nhân trang lần 3 | Sidecar, không phải trang sách |")
    a("| `IMG_9648(1).JPG` | iOS duplicate | Loại `(1)` như inventory Hương |")
    a("| `Hương.zip` + thư mục đã giải nén | Nhân file | Inventory ghi zip là *container* |")
    a("| DOCX bằng khoán copy 2 chỗ | 2 file, 1 văn bản | MD5 trong `25_8_2026/.../inventory.json` |")
    a("| `test_temp`, `test_temp2` | Rác lab trong raw | Không đưa catalog; cân nhắc `05_ops` |")
    a("")
    a("**Lô chưa catalog (2026-08-27):** `nguyen-ke-han-nom` (15 trang Paddle, lab 0/15), `nguyen-ke-gia-pha` (ảnh Quốc ngữ, không OCR). Thêm vào `build_hannom_catalog.py` khi chốt `book_id`.")
    a("")

    a("## 7. Protocol — mỗi lần nhận dữ liệu mới")
    a("")
    a("1. **Không** thả file rời ở root `data/`. Đặt vào tầng đúng (`00_raw/…` nếu gốc; `04_external/sach` nếu lý thuyết).")
    a("2. Chọn **đơn vị:** cuốn / cây / thư mục ảnh. Đặt tên `book_id` hoặc `tree_id`.")
    a("3. Ghi **inventory cục bộ** (`inventory.md` + `inventory.json`) trong thư mục lô — như `25_8_2026/Hương/`.")
    a("4. Khai **media:** `pdf` · `docx` · `image_list` · `txt` · `json_tree` · `zip`. List ảnh: đếm nguồn, loại preview/`(1)`.")
    a("5. Nếu là cuốn Hán-Nôm hoặc bản dịch: thêm vào `build_hannom_catalog.py` rồi `python nlp_family_extractor/tools/build_hannom_catalog.py`.")
    a("6. **Luôn** chạy generator này → cập nhật `DATA_INVENTORY.md` + JSON.")
    a("7. Số liệu đóng băng trong bài: copy từ file này và ghi ngày `generated_at`.")
    a("")
    a("## 8. Lệnh liên quan")
    a("")
    a("```bash")
    a("# Tổng quan corpus (file này)")
    a("PYTHONPATH=research python -m label_studio_pipeline.build_corpus_inventory")
    a("")
    a("# Catalog cuốn Hán-Nôm + Word 24/08 + PDF tông phả")
    a("python nlp_family_extractor/tools/build_hannom_catalog.py")
    a("python nlp_family_extractor/tools/build_hannom_compare_html.py")
    a("")
    a("# Phân tích Word 24/08")
    a("python nlp_family_extractor/tools/write_docx_analysis.py")
    a("```")
    a("")
    a("Đọc tầng: [`README.md`](README.md) · Nguồn/bản quyền: `docs/thesis/RESEARCH_SOURCES.md` (repo code).")
    a("")
    return "\n".join(lines)


def write_inventory(payload: dict[str, Any]) -> tuple[Path, Path]:
    INVENTORY_JSON.parent.mkdir(parents=True, exist_ok=True)
    slim = dict(payload)
    # JSON giữ đủ số; books chỉ id + flags để file gọn
    INVENTORY_JSON.write_text(
        json.dumps(slim, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    INVENTORY_MD.write_text(render_md(payload), encoding="utf-8")
    return INVENTORY_MD, INVENTORY_JSON


def main() -> int:
    payload = build_payload()
    md_path, json_path = write_inventory(payload)
    t = payload["totals"]
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(
        f"  files={t['files']}  {fmt_mb(t['bytes'])}  "
        f"vgp={payload['vgp']['tree_dirs']}  valid={payload['vgp']['valid_narrative_and_tree']}  "
        f"gold={payload['gold']['gold_tree_dirs']}  books={payload['hannom_catalog']['n_books']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
