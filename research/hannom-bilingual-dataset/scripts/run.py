#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1 LỆNH DUY NHẤT để chạy OCR-vote cho 1 tài liệu và xem kết quả cuối.

Thay thế việc phải nhớ 2 lệnh riêng (vote_ocr.py rồi build_record.py) với 2 bộ
tên flag khác nhau (--book vs --doc-id, --out vs --votes-dir). Giờ chỉ cần:

  python3 scripts/run.py <doc_id>                 # 3 trang đầu (mặc định, an toàn quota)
  python3 scripts/run.py <doc_id> --pages 0,1,6    # đúng các trang này
  python3 scripts/run.py <doc_id> --all            # TOÀN BỘ trang — tốn quota thật, cân nhắc

3 nơi cần nhớ, không hơn:
  data/00_raw/hannom_inbox/<doc_id>/   (bên family-tree) — ảnh gốc, nơi BỎ VÀO
  runs/<doc_id>/                       — kết quả OCR+vote thô từng trang (cache tạm,
                                          gitignored, có thể xoá/chạy lại bất cứ lúc nào)
  data/track*/<doc_id>.json            — KẾT QUẢ CUỐI, đã gộp, đây là file thật của dataset
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import vote_ocr  # noqa: E402
import build_record  # noqa: E402
from _repo_paths import DATA_REPO_ROOT  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("doc_id")
    ap.add_argument("--pages", default=None, help="vd: 0,1,2 — mặc định 3 trang đầu")
    ap.add_argument("--all", action="store_true", help="chạy TOÀN BỘ trang — tốn quota thật (deepseek/google_vision/gemini)")
    ap.add_argument("--from-record", action="store_true",
                    help="Vote lại từ engines{} đã lưu trong record (không gọi API, không cần family-tree)")
    args = ap.parse_args()

    record_path = build_record.find_record_path(args.doc_id)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    all_page_ids = [p["page_id"] for p in record.get("pages", [])]
    if not all_page_ids:
        raise SystemExit(f"{record_path} chưa có trang nào trong 'pages' — kiểm tra lại record.")

    if args.pages:
        stems = [p.strip() for p in args.pages.split(",") if p.strip()]
    elif args.all:
        stems = all_page_ids
    else:
        stems = all_page_ids[:3]
        if len(all_page_ids) > 3:
            print(f"(Mặc định chỉ chạy 3/{len(all_page_ids)} trang đầu để tiết kiệm quota — "
                  f"thêm --all để chạy hết {len(all_page_ids)} trang, hoặc --pages để chọn trang cụ thể)\n")

    out_dir = DATA_REPO_ROOT / "runs" / args.doc_id
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.from_record:
        print(f"Đang vote lại {len(stems)} trang cho '{args.doc_id}' từ engines{{}} trong record (không gọi API)...")
        pages_by_id = {p["page_id"]: p for p in record.get("pages", [])}
        rates = []
        for stem in stems:
            page = pages_by_id.get(stem) or {}
            engines = (page.get("l1_ocr") or {}).get("engines") or {}
            results = vote_ocr.results_from_engines(engines)
            result = vote_ocr.vote_from_results(results, vote_ocr.DEFAULT_PRIORITY)
            used = list(result["engines"].keys())
            rate = result.get("uncertain_rate")
            if rate is not None:
                rates.append(rate)
            rate_txt = f", uncertain_rate {rate * 100:.1f}%" if rate is not None else ""
            print(f"  trang {stem}: {len(used)} engine ({', '.join(used) or '(không engine nào có dữ liệu)'}){rate_txt}")
            (out_dir / f"{stem}.vote.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        print(f"\n(Kết quả thô từng trang lưu ở {out_dir}/ — cache tạm, xoá/chạy lại được bất cứ lúc nào)")
        build_record.merge_votes(args.doc_id, out_dir)
        avg_rate = sum(rates) / len(rates) if rates else None
        print("\n=== KẾT QUẢ CUỐI ===")
        print(f"File: {record_path}")
        if avg_rate is not None:
            print(f"uncertain_rate trung bình {len(rates)} trang: {avg_rate * 100:.1f}%")
        print("Mở file trên để xem voted_text + uncertain_spans của từng trang.")
        return 0

    catalog = vote_ocr.load_catalog()
    book = catalog.get(args.doc_id)
    if book is None:
        raise SystemExit(
            f"Không có book_id={args.doc_id} trong books_catalog.json.\n"
            f"Nếu đây là tài liệu MỚI: chạy scripts/add_new_source.py trước."
        )

    out_dir = DATA_REPO_ROOT / "runs" / args.doc_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # XÁC NHẬN 2026-09-12: đã THỬ chạy song song nhiều TRANG cùng lúc (4 trang/lần,
    # 299s/8 trang) và song song nhiều ENGINE trong 1 trang (429s/8 trang) — CẢ
    # HAI đều CHẬM HƠN bản tuần tự hoàn toàn (92.7s/8 trang). Rate limit áp
    # dụng ở mức server cho bất kỳ kiểu gọi đồng thời nào tới cùng API key.
    # ĐÃ REVERT CẢ HAI — toàn bộ pipeline giờ tuần tự 100% (từng trang, từng
    # engine). Không tự ý bật lại song song ở bất kỳ mức nào khi chưa đo lại
    # cẩn thận, cô lập khỏi các tiến trình khác dùng chung API key.
    print(f"Đang vote {len(stems)} trang cho '{args.doc_id}'...")
    rates = []
    for stem in stems:
        result = vote_ocr.vote_page(book, stem, vote_ocr.DEFAULT_PRIORITY)
        used = list(result["engines"].keys())
        rate = result.get("uncertain_rate")
        if rate is not None:
            rates.append(rate)
        rate_txt = f", uncertain_rate {rate * 100:.1f}%" if rate is not None else ""
        print(f"  trang {stem}: {len(used)} engine ({', '.join(used) or '(không engine nào có dữ liệu)'}){rate_txt}")
        (out_dir / f"{stem}.vote.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"\n(Kết quả thô từng trang lưu ở {out_dir}/ — cache tạm, xoá/chạy lại được bất cứ lúc nào)")

    build_record.merge_votes(args.doc_id, out_dir)

    avg_rate = sum(rates) / len(rates) if rates else None
    print("\n=== KẾT QUẢ CUỐI ===")
    print(f"File: {record_path}")
    if avg_rate is not None:
        print(f"uncertain_rate trung bình {len(rates)} trang: {avg_rate * 100:.1f}%")
    print("Mở file trên để xem voted_text + uncertain_spans của từng trang.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
