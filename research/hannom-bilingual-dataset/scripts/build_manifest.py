#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sinh manifest/classification.json từ family-tree/data/00_raw/hannom/books_catalog.json.

Track gán theo phân tích đã đọc trực tiếp (phiên làm việc trước), KHÔNG suy đoán mới:
  1 = toàn Hán Nôm, chưa có dịch nghĩa thật
  2 = đã có sẵn Hán + Việt song ngữ
  3 = văn bản gia phả tiếng Việt thuần (không có/mất bản Hán)
  loại khỏi phạm vi = không phải bản thân 1 bộ phả (kế ước, sách lý thuyết)
"""
import json
from pathlib import Path

from _repo_paths import FAMILY_TREE

OUT = Path(__file__).resolve().parents[1] / "manifest" / "classification.json"

EXCLUDE = {
    "nguyen-ke-han-nom": "văn khế/kế ước đất, không phải bản thân 1 bộ phả",
    "sach-gia-pha-hoc-tinh-hoa": "sách lý thuyết, không phải bản thân 1 bộ phả",
    "sach-huong-dan-viet-gia-pha": "sách lý thuyết, không phải bản thân 1 bộ phả",
    "nom-130": "sử liệu chung, không gắn dòng họ nào",
}

TRACK2 = {"pdf-phan-gia-cong-pha", "gpc-dang-1928", "docx-nguyen-van"}
TRACK3 = {"pdf-nguyen-phuc-the-pha", "docx-pham-1876", "docx-tran-200", "nguyen-ke-gia-pha"}


def track_for(book_id: str) -> int:
    if book_id in TRACK2:
        return 2
    if book_id in TRACK3:
        return 3
    return 1


def main() -> None:
    catalog = json.loads((FAMILY_TREE / "data/00_raw/hannom/books_catalog.json").read_text(encoding="utf-8"))
    books = catalog["books"]

    entries = []
    excluded_entries = []
    for b in books:
        bid = b["book_id"]
        if bid in EXCLUDE:
            excluded_entries.append({"doc_id": bid, "title_vn": b.get("title_vn"), "ly_do": EXCLUDE[bid]})
            continue
        entries.append({
            "doc_id": bid,
            "track": track_for(bid),
            "title_han": b.get("title_han") or None,
            "title_vn": b.get("title_vn"),
            "duong_dan_goc": (b.get("paths") or {}).get("root"),
        })

    counts = {1: 0, 2: 0, 3: 0}
    for e in entries:
        counts[e["track"]] += 1

    manifest = {
        "sinh_tu": "family-tree/data/00_raw/hannom/books_catalog.json",
        "tong_so": len(entries) + len(excluded_entries),
        "so_luong_theo_track": counts,
        "entries": sorted(entries, key=lambda e: e["track"]),
        "loai_khoi_pham_vi": excluded_entries,
    }
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Đã ghi:", OUT)
    print("Track counts:", counts, "| loại khỏi phạm vi:", len(excluded_entries))


if __name__ == "__main__":
    main()
