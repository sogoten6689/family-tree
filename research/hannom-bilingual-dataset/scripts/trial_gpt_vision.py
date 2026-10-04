"""Chạy thử engine gpt_vision trên N trang của 1 bộ và so với các engine đã có — TỐN TIỀN (OpenAI).

Chỉ gọi GPT (engine khác lấy từ `l1_ocr.engines` đã lưu trong record — không gọi
lại). Kết quả thô lưu ở runs/<doc>/gpt_vision/<stem>.txt; trang đã có file thì
KHÔNG gọi lại (chạy lại script không tốn thêm). Không sửa record.

Đo mỗi trang:
  - gpt_chars, overlap_<engine>: tỉ lệ chữ chung (multiset) của GPT với từng engine
  - so vote theo từng chữ KHÔNG có GPT và CÓ GPT: tự sửa, đề xuất, tỉ lệ cần soát

Chạy: python3 scripts/trial_gpt_vision.py --doc nom-147 --pages 15 [--seed 7] [--json OUT]
"""

from __future__ import annotations

import argparse
import json
import random
import statistics as st
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import DATA_REPO_ROOT, FAMILY_TREE  # noqa: E402
from ocr_adapters import gpt_vision, paddle_v6  # noqa: E402
from vote_char_majority import han_only, vote_page  # noqa: E402
from vote_ocr import DEFAULT_PRIORITY, load_catalog, results_from_engines  # noqa: E402


def overlap(a: str, b: str) -> float:
    return sum((Counter(a) & Counter(b)).values()) / max(len(a), len(b)) if a and b else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--doc", required=True)
    ap.add_argument("--pages", type=int, default=15, help="số trang lấy ngẫu nhiên (trang có ≥2 engine)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    if not gpt_vision._api_key():
        raise SystemExit("Chưa có OPENAI_API_KEY (family-tree/nlp_family_extractor/.env) — dừng, không gọi gì.")
    record = json.loads(next((DATA_REPO_ROOT / "data").glob(f"track*/{args.doc}.json")).read_text(encoding="utf-8"))
    book = load_catalog()[args.doc]
    pages = [p for p in record["pages"] if len((p.get("l1_ocr") or {}).get("engines") or {}) >= 2]
    sample = random.Random(args.seed).sample(pages, min(args.pages, len(pages)))
    cache = DATA_REPO_ROOT / "runs" / args.doc / "gpt_vision"
    cache.mkdir(parents=True, exist_ok=True)

    rows = []
    for page in sorted(sample, key=lambda p: p["page_id"]):
        stem = Path(page["l0_image"]).stem
        f = cache / f"{stem}.txt"
        if f.is_file():
            lines = [ln for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip()]
            status = "cache"
        else:
            r = gpt_vision.load(book, stem, FAMILY_TREE)
            lines = r.lines if r else []
            f.write_text("\n".join(lines), encoding="utf-8")
            status = "called"
        results = results_from_engines(page["l1_ocr"]["engines"])
        if "paddle_v6" in results:
            fresh = paddle_v6.load(book, stem, FAMILY_TREE)
            if fresh is not None:
                results["paddle_v6"] = fresh
        base_lines = {n: r.lines for n, r in results.items() if han_only("".join(r.lines))}
        gpt_text = han_only("".join(lines))
        row = {"page": page["page_id"], "status": status, "gpt_chars": len(gpt_text)}
        for name, ls in base_lines.items():
            row[f"overlap_{name}"] = round(overlap(gpt_text, han_only("".join(ls))), 3)
        before = vote_page(base_lines, DEFAULT_PRIORITY)
        with_gpt = vote_page({**base_lines, **({"gpt_vision": lines} if gpt_text else {})}, DEFAULT_PRIORITY)
        for tag, v in (("before", before), ("with_gpt", with_gpt)):
            c = v.counts()
            row[f"{tag}_auto"] = c.get("auto_fixed", 0)
            row[f"{tag}_suggest"] = c.get("suggested", 0)
            row[f"{tag}_review"] = round(v.review_rate(), 3)
        row["gpt_voted"] = "gpt_vision" in with_gpt.engines
        row["gpt_excluded"] = with_gpt.excluded.get("gpt_vision")
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False))

    engines = sorted({k[8:] for r in rows for k in r if k.startswith("overlap_")})
    print("\nTÓM TẮT", args.doc, f"{len(rows)} trang (gọi mới {sum(r['status'] == 'called' for r in rows)})")
    for e in engines:
        vals = [r[f"overlap_{e}"] for r in rows if f"overlap_{e}" in r and r["gpt_chars"]]
        if vals:
            print(f"  GPT ~ {e:<15} chữ chung TB {st.mean(vals):.2f}")
    for tag in ("before", "with_gpt"):
        print(
            f"  vote {tag:<9} tự sửa {sum(r[f'{tag}_auto'] for r in rows):>4}  đề xuất {sum(r[f'{tag}_suggest'] for r in rows):>4}"
            f"  cần soát TB {st.mean(r[f'{tag}_review'] for r in rows):.1%}"
        )
    print(f"  GPT không có chữ Hán: {sum(1 for r in rows if not r['gpt_chars'])} trang; bị loại khỏi vote: "
          f"{sum(1 for r in rows if r['gpt_excluded'])}")
    if args.json:
        args.json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
