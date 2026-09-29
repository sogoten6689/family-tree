#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phiên âm Hán-Việt (L2) cho các trang đã có `voted_text` (sau vote 5-engine).

Dùng lại hàm `lab_transliterate()` có sẵn bên family-tree
(`nlp_family_extractor/tools/dich_hannom_catalog.py`, gọi API Kim Hán Nôm Lab,
credential `HANNOM_EMAIL`/`HANNOM_PASSWORD` đã có trong
`family-tree/nlp_family_extractor/.env` — MIỄN PHÍ, không phải Gemini/DeepSeek)
— nhưng đưa vào TEXT ĐÃ VOTE (chất lượng cao hơn Paddle thô mà tool gốc bên
family-tree tự đọc), thay vì để tool đó tự tìm file Paddle của riêng nó.

Chỉ đọc hàm có sẵn bên family-tree qua importlib — KHÔNG sửa gì bên đó.

Dùng:
  python3 scripts/phien_am.py <doc_id>                # tất cả trang có voted_text, chưa có l2
  python3 scripts/phien_am.py <doc_id> --pages 001,002
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from _repo_paths import DATA_REPO_ROOT, FAMILY_TREE

ROOT = Path(__file__).resolve().parents[1]


def load_lab_transliterate():
    tool_path = FAMILY_TREE / "nlp_family_extractor/tools/dich_hannom_catalog.py"
    spec = importlib.util.spec_from_file_location("dich_hannom_catalog", tool_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.lab_transliterate


def find_record_path(doc_id: str) -> Path:
    for track_dir in ("track1_hannom_only", "track2_bilingual", "track3_viet_only"):
        p = DATA_REPO_ROOT / "data" / track_dir / f"{doc_id}.json"
        if p.is_file():
            return p
    raise SystemExit(f"Không tìm thấy record cho doc_id={doc_id}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("doc_id")
    ap.add_argument("--pages", default=None, help="vd 001,002 — mặc định tất cả trang có voted_text")
    args = ap.parse_args()

    lab_transliterate = load_lab_transliterate()

    record_path = find_record_path(args.doc_id)
    record = json.loads(record_path.read_text(encoding="utf-8"))

    # XÁC NHẬN 2026-09-12: đã THỬ song song nhiều trang cho vote_ocr.py (run.py)
    # — CHẬM HƠN 3 lần vì nhiều trang cùng gọi CHUNG 1 nhà cung cấp bị chính
    # server giới hạn tốc độ. API lab ở đây cũng là 1 nhà cung cấp duy nhất cho
    # mọi trang — không song song hoá theo trang, tránh lặp lại bài học đó.
    wanted = set(p.strip() for p in args.pages.split(",")) if args.pages else None
    updated = 0
    for page in record.get("pages", []):
        if wanted and page["page_id"] not in wanted:
            continue
        voted_text = (page.get("l1_ocr") or {}).get("voted_text")
        if not voted_text:
            continue
        if page.get("l2_phien_am"):
            continue
        print(f"  trang {page['page_id']}: đang phiên âm qua API lab...")
        phien = lab_transliterate(voted_text)
        if phien:
            page["l2_phien_am"] = phien
            updated += 1
            if record.get("status") == "l1_done":
                record["status"] = "l2_done"
            record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            preview = phien.replace("\n", " ")[:70]
            print(f"    -> {preview}...")
        else:
            print("    -> LAB KHÔNG PHIÊN ÂM ĐƯỢC (thiếu HANNOM_EMAIL/PASSWORD hoặc lỗi đăng nhập)")

    if updated:
        print(f"\nĐã cập nhật {updated} trang, lưu vào {record_path} (status={record['status']})")
    else:
        print("\nKhông có trang nào được cập nhật.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
