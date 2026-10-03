"""Vote lại L1 của record theo TỪNG CHỮ (schema 2) — offline, không gọi API.

Mỗi trang có kết quả engine (`l1_ocr.engines`): đọc lại paddle_v6 theo thứ tự cột
(adapter đã sửa), vote bằng `vote_page` của backend (nlp_family_extractor/app/
hannom/vote_char.py — nguồn duy nhất), ghi l1_ocr mới:

    voted_text            văn bản kết quả (chỉ chữ Hán, theo dòng của engine nền)
    schema_version=2 ...  meta vote (backbone, page_status, thresholds, stats,
                          review_rate, uncertain_rate, engines, slots)
    downstream_stale      chữ Hán (nội dung hoặc thứ tự) khác bản vote trước →
                          l2_phien_am / l3_dich_nghia có thể lệch (KHÔNG tự chạy lại
                          phiên âm/dịch — tốn tiền, Lâm quyết sau)

Engine giữ `score` cũ (nếu có). Chỉ đổi `l1_ocr` của trang có engine; mọi trường
khác giữ nguyên, định dạng file giữ nguyên. Mặc định CHỈ ĐO; `--write` mới ghi.
Repo dữ liệu nên sạch (đã commit) trước khi --write để `git diff` chỉ có thay đổi này.

Chạy: python3 scripts/revote_char_records.py [--doc ID ...] [--write] [--json OUT]
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
from vote_char_majority import build_vote_meta, han_only, vote_page  # noqa: E402
from vote_ocr import DEFAULT_PRIORITY, load_catalog, results_from_engines  # noqa: E402


def revote_l1(page: dict[str, Any], book: dict[str, Any] | None) -> dict[str, Any] | None:
    """l1_ocr mới (schema 2) cho 1 trang, hoặc None nếu trang không có engine có chữ Hán."""
    l1 = page.get("l1_ocr") or {}
    old_engines = l1.get("engines") or {}
    results = results_from_engines(old_engines)
    if "paddle_v6" in results and book is not None and page.get("l0_image"):
        fresh = paddle_v6.load(book, Path(page["l0_image"]).stem, FAMILY_TREE)
        if fresh is not None:
            results["paddle_v6"] = fresh
    engine_lines = {name: r.lines for name, r in results.items() if han_only("".join(r.lines))}
    if not engine_lines:
        return None
    vote = vote_page(engine_lines, DEFAULT_PRIORITY)
    meta = build_vote_meta(vote, engine_lines)
    voted_text = "\n".join(meta.pop("lines"))
    for name, entry in meta["engines"].items():
        score = (old_engines.get(name) or {}).get("score")
        if score is not None:
            entry["score"] = score
    old_text = han_only(l1.get("voted_text") or "")
    # Cờ "dính": đã bật thì giữ (chạy lại lần 2 so với chính bản mới sẽ không còn
    # khác → nếu tính lại sẽ mất dấu). Chỉ xoá khi phiên âm/dịch thật sự làm lại.
    stale = bool(l1.get("downstream_stale")) or han_only(voted_text) != old_text
    return {"voted_text": voted_text, **meta, "downstream_stale": stale}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--doc", nargs="*", help="chỉ các doc_id này (mặc định: mọi record track 1/2)")
    parser.add_argument("--write", action="store_true", help="ghi vào record (mặc định chỉ đo)")
    parser.add_argument("--json", type=Path, help="ghi thống kê ra file JSON")
    args = parser.parse_args()

    catalog = load_catalog()
    stats: Counter = Counter()
    per_doc: dict[str, Counter] = {}
    for path in sorted(glob.glob(str(DATA_REPO_ROOT / "data" / "track[12]_*" / "*.json"))):
        original = Path(path).read_text(encoding="utf-8")
        record = json.loads(original)
        doc_id = record["doc_id"]
        if args.doc and doc_id not in args.doc:
            continue
        doc = per_doc.setdefault(doc_id, Counter())
        dirty = False
        for page in record.get("pages", []):
            new_l1 = revote_l1(page, catalog.get(doc_id))
            if new_l1 is None:
                continue
            doc["pages"] += 1
            doc["stale"] += new_l1["downstream_stale"]
            doc[f"status_{new_l1['page_status']}"] += 1
            for k, v in new_l1["stats"].items():
                if k != "chars":
                    doc[k] += v
            doc["chars"] += new_l1["stats"]["chars"]
            if page.get("l1_ocr") != new_l1:
                doc["l1_changed"] += 1
                page["l1_ocr"] = new_l1
                dirty = True
        if args.write and dirty:
            trailing = "\n" if original.endswith("\n") else ""
            Path(path).write_text(json.dumps(record, ensure_ascii=False, indent=2) + trailing, encoding="utf-8")
            doc["written"] = 1
        stats.update(doc)

    print(f"{'doc':<24}{'trang':>6}{'đổi L1':>8}{'stale':>7}{'tự sửa':>8}{'đề xuất':>9}  ok/partial/unaligned")
    for doc_id, c in per_doc.items():
        if c["pages"]:
            print(
                f"{doc_id:<24}{c['pages']:>6}{c['l1_changed']:>8}{c['stale']:>7}{c['auto_fixed']:>8}{c['suggested']:>9}"
                f"  {c['status_ok']}/{c['status_partial']}/{c['status_unaligned']}"
            )
    need = stats["suggested"] + stats["tie"] + stats["kept_weak"] + stats["unaligned"]
    print(
        f"TỔNG: {stats['pages']} trang, đổi L1 {stats['l1_changed']}, stale {stats['stale']}, "
        f"tự sửa {stats['auto_fixed']}, đề xuất {stats['suggested']}, cần soát {need / max(1, stats['chars']):.1%}"
    )
    print(f"ĐÃ GHI {sum(c['written'] for c in per_doc.values())} record" if args.write else "Dry-run: không ghi gì.")
    if args.json:
        args.json.write_text(
            json.dumps({"total": dict(stats), "per_doc": {k: dict(v) for k, v in per_doc.items()}}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
