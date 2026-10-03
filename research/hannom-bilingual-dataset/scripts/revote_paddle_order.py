"""Vote lại OFFLINE các trang có paddle_v6 sau khi sửa thứ tự cột (2026-10-03).

Không gọi API nào: lấy text các engine đã lưu trong record (`l1_ocr.engines`),
chỉ thay text paddle_v6 bằng bản đọc lại từ `{stem}-paddleocr.json` qua adapter
(đã sắp theo cột), rồi chạy `vote_from_results` (hàm thuần).

Mặc định CHỈ ĐO (dry-run), không ghi gì. `--write` mới cập nhật record — trang
có voted_text đổi HOẶC text paddle_v6 đổi thứ tự — và chỉ các trường L1 của vote (voted_text, vote_method, engines, uncertain_spans,
structural_diffs, uncertain_rate) — KHÔNG đụng l2_phien_am / l3_dich_nghia / pairs.

Chạy: python3 scripts/revote_paddle_order.py [--doc DOC_ID ...] [--write] [--json out.json]
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import DATA_REPO_ROOT, FAMILY_TREE  # noqa: E402
from ocr_adapters import paddle_v6  # noqa: E402
from vote_ocr import DEFAULT_PRIORITY, load_catalog, results_from_engines, vote_from_results  # noqa: E402

L1_VOTE_FIELDS = ("voted_text", "vote_method", "engines", "uncertain_spans", "structural_diffs", "uncertain_rate")


def nonempty_lines(text: str | None) -> list[str]:
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def revote_page(page: dict[str, Any], book: dict[str, Any] | None) -> dict[str, Any] | None:
    """Trả {"old", "new", "reproduced", "paddle_reordered", "same_paddle_lines"} hoặc None nếu
    trang không có paddle_v6 / không đọc lại được."""
    l1 = page.get("l1_ocr") or {}
    engines = l1.get("engines") or {}
    if "paddle_v6" not in engines or book is None or not page.get("l0_image"):
        return None
    stem = Path(page["l0_image"]).stem
    fresh = paddle_v6.load(book, stem, FAMILY_TREE)
    if fresh is None:
        return None

    old_paddle = nonempty_lines(engines["paddle_v6"].get("text"))
    results = results_from_engines(engines)
    reproduced = vote_from_results(results, DEFAULT_PRIORITY)
    results["paddle_v6"] = fresh
    new = vote_from_results(results, DEFAULT_PRIORITY)
    return {
        "old": l1,
        "new": new,
        "reproduced": nonempty_lines(reproduced.get("voted_text")) == nonempty_lines(l1.get("voted_text")),
        "same_paddle_lines": Counter(old_paddle) == Counter(fresh.lines),
        "paddle_reordered": old_paddle != fresh.lines,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--doc", nargs="*", help="chỉ các doc_id này (mặc định: mọi record track 1/2)")
    parser.add_argument("--write", action="store_true", help="ghi kết quả vào record (mặc định chỉ đo)")
    parser.add_argument("--json", type=Path, help="ghi thống kê chi tiết ra file JSON")
    args = parser.parse_args()

    catalog = load_catalog()
    stats: Counter = Counter()
    per_doc: dict[str, Counter] = {}
    changed_pages: list[dict[str, Any]] = []

    for path in sorted(glob.glob(str(DATA_REPO_ROOT / "data" / "track[12]_*" / "*.json"))):
        original = Path(path).read_text(encoding="utf-8")
        record = json.loads(original)
        doc_id = record["doc_id"]
        if args.doc and doc_id not in args.doc:
            continue
        book = catalog.get(doc_id)
        doc_stats = per_doc.setdefault(doc_id, Counter())
        dirty = False
        for page in record.get("pages", []):
            outcome = revote_page(page, book)
            if outcome is None:
                continue
            old, new = outcome["old"], outcome["new"]
            old_lines, new_lines = nonempty_lines(old.get("voted_text")), nonempty_lines(new.get("voted_text"))
            stats["pages"] += 1
            doc_stats["pages"] += 1
            stats["reproduced_before_fix"] += outcome["reproduced"]
            stats["paddle_same_lines_as_stored"] += outcome["same_paddle_lines"]
            stats["paddle_reordered"] += outcome["paddle_reordered"]
            stats["voted_text_changed"] += old_lines != new_lines
            stats["voted_text_only_reordered"] += old_lines != new_lines and Counter(old_lines) == Counter(new_lines)
            stats["backbone_changed"] += (old.get("vote_method") or "").split("_backbone")[0] != (
                new.get("vote_method") or ""
            ).split("_backbone")[0]
            stats["uncertain_rate_sum_old"] += float(old.get("uncertain_rate") or 0)
            stats["uncertain_rate_sum_new"] += float(new.get("uncertain_rate") or 0)
            doc_stats["voted_text_changed"] += old_lines != new_lines
            if old_lines != new_lines:
                changed_pages.append({"doc_id": doc_id, "page_id": page.get("page_id")})
            # Ghi cả khi chỉ text paddle_v6 trong engines{} đổi thứ tự (paddle không làm
            # backbone → voted_text giữ nguyên nhưng bước "OCR theo engine" vẫn hiện sai).
            if args.write and (old_lines != new_lines or outcome["paddle_reordered"]):
                page["l1_ocr"] = {**old, **{k: new[k] for k in L1_VOTE_FIELDS if k in new}}
                dirty = True
        if args.write and dirty:
            # Giữ định dạng gốc (indent=2, Unicode thô; có/không xuống dòng cuối file tuỳ record).
            trailing = "\n" if original.endswith("\n") else ""
            Path(path).write_text(json.dumps(record, ensure_ascii=False, indent=2) + trailing, encoding="utf-8")
            stats["records_written"] += 1

    n = stats["pages"] or 1
    print(f"Trang có paddle_v6 đọc lại được: {stats['pages']}")
    print(f"  Vote lại với dữ liệu CŨ ra đúng voted_text đã lưu: {stats['reproduced_before_fix']}")
    print(f"  Paddle đọc lại có cùng tập dòng với bản đã lưu:    {stats['paddle_same_lines_as_stored']}")
    print(f"  Paddle bị đổi thứ tự dòng:                         {stats['paddle_reordered']}")
    print(f"  voted_text thay đổi:                               {stats['voted_text_changed']}")
    print(f"    trong đó chỉ đổi thứ tự (nội dung giữ nguyên):   {stats['voted_text_only_reordered']}")
    print(f"  Engine nền (backbone) thay đổi:                    {stats['backbone_changed']}")
    print(
        f"  uncertain_rate trung bình: cũ={stats['uncertain_rate_sum_old'] / n:.4f}"
        f"  mới={stats['uncertain_rate_sum_new'] / n:.4f}"
    )
    print("  " + ("ĐÃ GHI " + str(stats["records_written"]) + " record" if args.write else "Dry-run: không ghi gì."))
    if args.json:
        args.json.write_text(
            json.dumps({"stats": dict(stats), "per_doc": {k: dict(v) for k, v in per_doc.items()}, "changed": changed_pages},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
