#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bảng tổng quan tiến độ TOÀN BỘ tài liệu — không tốn quota (chỉ đọc lại
record JSON đã có, KHÔNG gọi API sống của deepseek/google_vision/gemini để
kiểm tra — nếu không mỗi lần xem tiến độ lại tốn tiền thật).

Dùng:
  python3 scripts/status.py            # toàn bộ 28 tài liệu
  python3 scripts/status.py --track 1  # chỉ Track 1
"""
from __future__ import annotations

import argparse
import glob
import json

from _repo_paths import DATA_REPO_ROOT

CLASSIFY_FIELDS = ["quy_mo", "hinh_thuc", "ho", "dia_danh", "nien_dai"]


def is_classified(value) -> bool:
    if not value:
        return False
    return "Chưa phân loại" not in str(value)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--track", type=int, choices=[1, 2, 3], default=None)
    args = ap.parse_args()

    rows = []
    for f in sorted(glob.glob(str(DATA_REPO_ROOT / "data" / "*" / "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        if args.track and d["track"] != args.track:
            continue
        pages = d.get("pages", [])
        total = len(pages)
        with_l1 = sum(1 for p in pages if (p.get("l1_ocr") or {}).get("voted_text"))
        engines_seen = set()
        rates = []
        for p in pages:
            l1 = p.get("l1_ocr") or {}
            engines_seen.update(l1.get("engines", {}).keys())
            if l1.get("uncertain_rate") is not None:
                rates.append(l1["uncertain_rate"])
        avg_rate = f"{sum(rates) / len(rates) * 100:.1f}%" if rates else "-"
        n_classified = sum(1 for k in CLASSIFY_FIELDS if is_classified(d.get(k)))
        rows.append({
            "doc_id": d["doc_id"],
            "track": d["track"],
            "l1": f"{with_l1}/{total}",
            "n_engines": len(engines_seen),
            "avg_rate": avg_rate,
            "classified": f"{n_classified}/5",
            "ma_dinh_danh": d.get("ma_dinh_danh") or "-",
        })

    w = {"doc_id": 24, "track": 5, "l1": 8, "n_engines": 8, "avg_rate": 9, "classified": 10, "ma_dinh_danh": 26}
    header = (f"{'doc_id':<{w['doc_id']}} {'track':<{w['track']}} {'L1 (trang)':<{w['l1']}} "
              f"{'#engine':<{w['n_engines']}} {'unc.rate':<{w['avg_rate']}} {'phân loại':<{w['classified']}} ma_dinh_danh")
    print(header)
    print("-" * len(header))
    for r in rows:
        print(f"{r['doc_id']:<{w['doc_id']}} {r['track']:<{w['track']}} {r['l1']:<{w['l1']}} "
              f"{r['n_engines']:<{w['n_engines']}} {r['avg_rate']:<{w['avg_rate']}} "
              f"{r['classified']:<{w['classified']}} {r['ma_dinh_danh']}")

    n_full_l1 = sum(1 for r in rows if r["l1"].split("/")[0] == r["l1"].split("/")[1] and r["l1"] != "0/0")
    n_with_code = sum(1 for r in rows if r["ma_dinh_danh"] != "-")
    print()
    print(f"Tổng {len(rows)} tài liệu | {n_full_l1} đã vote đủ trang | {n_with_code} đã có ma_dinh_danh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
