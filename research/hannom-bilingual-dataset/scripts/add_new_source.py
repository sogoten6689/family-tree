#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Đăng ký 1 tài liệu MỚI (ảnh scan chưa từng có trong family-tree) vào pipeline.

CÁCH DÙNG — 2 bước:

  1. Tạo thư mục và bỏ ảnh đã chụp/scan vào, đặt tên số thứ tự trang:
       family-tree/data/00_raw/hannom_inbox/<doc_id>/0.jpg
       family-tree/data/00_raw/hannom_inbox/<doc_id>/1.jpg
       ...
     (chấp nhận .jpg/.jpeg/.png, đánh số từ 0, không cần đệm số 0 phía trước)

  2. Chạy đúng 1 lệnh này:
       python3 scripts/add_new_source.py --doc-id <doc_id> \
         [--title-vn "Tên gọi tiếng Việt"] [--title-han "漢字"] [--ho "Họ"]

Script làm 4 việc (đều CỘNG THÊM, không sửa/xoá gì đã có sẵn):
  a. Thêm 1 entry mới vào family-tree/data/00_raw/hannom/books_catalog.json
     (đây là ghi duy nhất chạm vào repo family-tree — chỉ append, không sửa
     entry khác).
  b. Chạy lại build_manifest.py để manifest/classification.json thấy tài liệu mới.
  c. Tạo record JSON Track 1 (mặc định) tại data/track1_hannom_only/<doc_id>.json,
     mọi trường phân loại (quy_mo/hinh_thuc/dia_danh/nien_dai) để null + ghi_chu
     "Chưa phân loại" — KHÔNG bịa, đúng nguyên tắc no-fabrication.
  d. Validate record vừa tạo theo schema.

Sau khi chạy xong, xem kết quả OCR ngay bằng:
  python3 scripts/run.py <doc_id>
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

from _repo_paths import DATA_REPO_ROOT, FAMILY_TREE

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = FAMILY_TREE / "data/00_raw/hannom/books_catalog.json"
INBOX_ROOT = FAMILY_TREE / "data/00_raw/hannom_inbox"

IMG_EXTS = (".jpg", ".jpeg", ".png")


def _numeric_key(stem: str):
    return (0, int(stem)) if stem.isdigit() else (1, stem)


def find_pages(doc_id: str) -> list[tuple[str, str]]:
    """Trả [(stem, ext)], sort theo số nếu tên file là số."""
    folder = INBOX_ROOT / doc_id
    if not folder.is_dir():
        raise SystemExit(
            f"Không thấy thư mục {folder}\n"
            f"Tạo thư mục này trước, bỏ ảnh vào (0.jpg, 1.jpg, ...) rồi chạy lại."
        )
    pages: dict[str, str] = {}
    for p in folder.iterdir():
        if p.suffix.lower() in IMG_EXTS:
            pages[p.stem] = p.suffix.lower()
    if not pages:
        raise SystemExit(f"Thư mục {folder} không có ảnh nào (.jpg/.jpeg/.png).")
    return sorted(pages.items(), key=lambda kv: _numeric_key(kv[0]))


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def save_catalog(catalog: dict) -> None:
    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--doc-id", required=True, help="vd: nom-2000, phai chi co chu thuong/so/-")
    ap.add_argument("--title-vn", default=None)
    ap.add_argument("--title-han", default=None)
    ap.add_argument("--ho", default=None)
    args = ap.parse_args()

    doc_id = args.doc_id
    if not re.fullmatch(r"[a-z0-9][a-z0-9\-]*", doc_id):
        raise SystemExit("doc-id chỉ nên chứa chữ thường/số/dấu gạch ngang, vd: nom-2000")

    pages = find_pages(doc_id)
    print(f"Tìm thấy {len(pages)} trang trong {INBOX_ROOT / doc_id}: "
          f"{pages[0][0]}{pages[0][1]} .. {pages[-1][0]}{pages[-1][1]}")

    catalog = load_catalog()
    if any(b["book_id"] == doc_id for b in catalog["books"]):
        raise SystemExit(f"doc_id={doc_id} đã tồn tại trong books_catalog.json — dùng doc-id khác.")

    rel_root = f"data/00_raw/hannom_inbox/{doc_id}"
    new_book = {
        "book_id": doc_id,
        "source": "local_scan",
        "volume_id": None,
        "collection_id": None,
        "title_han": args.title_han,
        "title_vn": args.title_vn or doc_id,
        "clan_key": (args.ho or "").strip().lower() or None,
        "kind": "gia_pha",
        "loai": [],
        "layout_tags": [],
        "language": "han",
        "script_hint": "unknown",
        "catalog_code": "",
        "page_count": len(pages),
        "page_count_catalog": len(pages),
        "jpg_source": len(pages),
        "jpg_review": 0,
        "page_count_source": "jpg_count",
        "flags": [],
        "read_status": "chua_doc",
        "paths": {"root": rel_root, "pages": rel_root, "review": "", "paddleocr": "", "url": ""},
        "ocr": {"lab": False, "paddle": False, "dich": False, "lab_pages": 0, "paddle_pages": 0, "dich_pages": 0},
        "notes": "Thêm bởi scripts/add_new_source.py (hannom-bilingual-dataset) — chưa OCR/phân loại.",
    }
    catalog["books"].append(new_book)
    catalog["n_books"] = len(catalog["books"])
    save_catalog(catalog)
    print(f"✓ Đã thêm book_id={doc_id} vào {CATALOG_PATH}")

    sys.path.insert(0, str(ROOT / "scripts"))
    import build_manifest
    build_manifest.main()

    record = {
        "doc_id": doc_id,
        "ma_dinh_danh": None,  # F-code — chỉ tính được SAU khi đọc xong, xem scripts/ma_dinh_danh_tables.py
        "track": 1,
        "co_ban_han": True,
        "ten_goc_han": args.title_han,
        "ten_han_viet": args.title_vn or doc_id,
        "ho": args.ho,
        "quy_mo": None,
        "hinh_thuc": None,
        "dia_danh": None,
        "nien_dai": None,
        "nguon": {"duong_dan_goc": rel_root, "loai_tu_lieu": "anh_scan"},
        "pages": [
            {
                "page_id": stem,
                "l0_image": f"{rel_root}/{stem}{ext}",
                "l1_ocr": None,
                "l2_phien_am": None,
                "l3_dich_nghia": None,
                "ghi_chu_trang": None,
                "pairs": [],
            }
            for stem, ext in pages
        ],
        "status": "draft",
        "ghi_chu": (
            "Chưa phân loại — mới thêm qua add_new_source.py, cần đọc trực tiếp "
            "để xác nhận quy_mo/hinh_thuc/dia_danh/nien_dai (không suy đoán)."
        ),
        "provenance": {
            "created_at": datetime.date.today().isoformat(),
            "pipeline_version": "v0.1",
            "reviewed_by": None,
        },
    }
    record_path = DATA_REPO_ROOT / "data" / "track1_hannom_only" / f"{doc_id}.json"
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ Đã tạo record draft: {record_path}")

    import jsonschema
    schema = json.loads((ROOT / "schema" / "bilingual_record.schema.json").read_text(encoding="utf-8"))
    v = jsonschema.Draft7Validator(schema)
    errors = list(v.iter_errors(record))
    if errors:
        for e in errors:
            print("SCHEMA LỖI:", list(e.path), e.message)
        raise SystemExit(1)
    print("✓ Schema hợp lệ")

    print()
    print("Bước tiếp theo — xem kết quả OCR ngay:")
    print(f"  python3 scripts/run.py {doc_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
