#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gộp kết quả vote_ocr.py (L1) + phiên âm/dịch nghĩa tay hoặc tool (L2/L3) vào
1 file JSON Track 1 đã có sẵn (data/track1_hannom_only/{doc_id}.json), CẬP NHẬT
tại chỗ — không tạo record mới, không đụng track2/track3.

Chỉ merge; không tự OCR/dịch gì trong script này (đó là việc của vote_ocr.py và
family-tree/nlp_family_extractor/tools/{dich_hannom_catalog,dich_qwen}.py).

Dùng:
  # 1. Chạy vote_ocr.py, lưu ra thư mục tạm
  python scripts/vote_ocr.py --book gpc-dang-1928 --pages 0,1,2 --out /tmp/votes/gpc-dang-1928

  # 2. Gộp vào record (chỉ cập nhật page đã có trong --pages, không xoá page khác)
  python scripts/build_record.py --doc-id gpc-dang-1928 --votes-dir /tmp/votes/gpc-dang-1928
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import vote_ocr  # noqa: E402
from ocr_adapters.base import pages_dir_candidates, first_existing_file  # noqa: E402
from _repo_paths import DATA_REPO_ROOT  # noqa: E402

IMG_EXTS = (".jpg", ".jpeg", ".png")


def resolve_l0_image(doc_id: str, stem: str) -> str | None:
    """Tìm ảnh gốc thật cho 1 trang MỚI (chưa có trong record) — XÁC NHẬN 2026-09-14:
    trước đây merge_votes() luôn ghi l0_image=None cho trang mới, gây bug hàng loạt
    (đã vá tay 10 file Track 1 trước đó). Giờ tự dò bằng đúng logic ocr_adapters dùng
    để load ảnh, tránh lặp lại bug này mỗi khi thêm tài liệu mới."""
    catalog = vote_ocr.load_catalog()
    book = catalog.get(doc_id)
    if book is None:
        return None
    candidates = pages_dir_candidates(book, vote_ocr.FAMILY_TREE)
    for ext in IMG_EXTS:
        found = first_existing_file(candidates, f"{stem}{ext}")
        if found is not None:
            try:
                return str(found.relative_to(vote_ocr.FAMILY_TREE))
            except ValueError:
                return str(found)
    return None


def find_record_path(doc_id: str) -> Path:
    for track_dir in ("track1_hannom_only", "track2_bilingual", "track3_viet_only"):
        p = DATA_REPO_ROOT / "data" / track_dir / f"{doc_id}.json"
        if p.is_file():
            return p
    raise SystemExit(f"Không tìm thấy record cho doc_id={doc_id} trong data/track*/")


def merge_votes(doc_id: str, votes_dir: Path) -> Path:
    """Gộp {stem}.vote.json trong votes_dir vào record của doc_id. Trả về đường dẫn record."""
    record_path = find_record_path(doc_id)
    record = json.loads(record_path.read_text(encoding="utf-8"))

    vote_files = {f.stem.replace(".vote", ""): f for f in votes_dir.glob("*.vote.json")}
    if not vote_files:
        raise SystemExit(f"Không có file *.vote.json trong {votes_dir}")

    pages_by_id = {p["page_id"]: p for p in record.get("pages", [])}
    updated = 0
    for stem, vf in vote_files.items():
        vote = json.loads(vf.read_text(encoding="utf-8"))
        vote_l1 = {
            "voted_text": vote.get("voted_text"),
            "vote_method": vote.get("vote_method"),
            "engines": vote.get("engines", {}),
            "uncertain_spans": vote.get("uncertain_spans", []),
            "structural_diffs": vote.get("structural_diffs", []),
            "uncertain_rate": vote.get("uncertain_rate"),
        }
        page = pages_by_id.get(stem)
        if page is None:
            page = {"page_id": stem, "l0_image": resolve_l0_image(doc_id, stem), "l1_ocr": None,
                     "l2_phien_am": None, "l3_dich_nghia": None, "pairs": []}
            record.setdefault("pages", []).append(page)
            pages_by_id[stem] = page
        page["l1_ocr"] = vote_l1
        updated += 1

    if updated and record.get("status") == "draft":
        record["status"] = "l1_done"

    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Đã cập nhật {updated} trang trong {record_path} (status={record['status']})")
    return record_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--doc-id", required=True)
    ap.add_argument("--votes-dir", required=True, help="Thư mục chứa {stem}.vote.json từ vote_ocr.py --out")
    args = ap.parse_args()
    merge_votes(args.doc_id, Path(args.votes_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
