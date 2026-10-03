"""So vote cũ (theo dòng, record) với vote mới theo từng chữ (vote_char_majority) — offline.

Không ghi vào record. Paddle đọc lại theo thứ tự cột (adapter đã sửa); engine nền
chọn như cũ (`rank_by_similarity`, cả 4 engine). Ghi thống kê + mẫu tự sửa ra
--out (JSON) và cắt ảnh mẫu (--crops) để đối chiếu bằng mắt.

Chạy: python3 scripts/compare_char_vote.py --doc nom-147 --out OUT.json [--crops DIR --sample 20]
"""

from __future__ import annotations

import argparse
import json
import random
import statistics as st
import sys
from collections import Counter
from pathlib import Path

from rapidfuzz.distance import Levenshtein

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import DATA_REPO_ROOT, FAMILY_TREE  # noqa: E402
from ocr_adapters import paddle_v6  # noqa: E402
from ocr_adapters.base import first_existing_file, paddle_dir_candidates  # noqa: E402
from vote_char_majority import find_outliers, han_only, slot_to_dict, vote_page_chars  # noqa: E402
from vote_ocr import DEFAULT_PRIORITY, load_catalog, rank_by_similarity, results_from_engines  # noqa: E402


def find_record(doc_id: str) -> Path:
    hits = list((DATA_REPO_ROOT / "data").glob(f"track*/{doc_id}.json"))
    if not hits:
        raise SystemExit(f"Không thấy record {doc_id}")
    return hits[0]


def old_char_review(l1: dict) -> int:
    """Ước lượng số chữ 'chưa chắc' của vote cũ: edit distance tới engine lệch gần nhất."""
    total = 0
    for span in l1.get("uncertain_spans") or []:
        voted = han_only(span.get("voted_line") or "")
        dists = [Levenshtein.distance(voted, han_only(d.get("text") or "")) for d in span.get("disagreeing") or []]
        if dists:
            total += min(min(dists), len(voted))
    return total


def crop_auto_fix(page: dict, book: dict, backbone_line: int, char_index_in_line: int, line_len: int, out: Path, title: str) -> bool:
    from PIL import Image, ImageDraw

    stem = Path(page["l0_image"]).stem
    json_path = first_existing_file(paddle_dir_candidates(book, FAMILY_TREE), f"{stem}-paddleocr.json")
    if json_path is None:
        return False
    boxes = paddle_v6.boxes_from_json(json_path)
    ordered = [boxes[i] for i in paddle_v6.column_order_indices(boxes) if han_only(boxes[i][1] or "")]
    if backbone_line >= len(ordered):
        return False
    poly = ordered[backbone_line][0]
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    img = Image.open(FAMILY_TREE / page["l0_image"]).convert("RGB")
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    # vị trí ước lượng của chữ trong khung dọc
    cy0 = y0 + (y1 - y0) * char_index_in_line / max(1, line_len)
    cy1 = y0 + (y1 - y0) * (char_index_in_line + 1) / max(1, line_len)
    crop = img.crop((max(0, x0 - 40), max(0, y0 - 20), min(img.width, x1 + 40), min(img.height, y1 + 20)))
    draw = ImageDraw.Draw(crop)
    ox, oy = max(0, x0 - 40), max(0, y0 - 20)
    draw.rectangle([x0 - ox - 4, cy0 - oy - 2, x1 - ox + 4, cy1 - oy + 2], outline=(220, 0, 0), width=3)
    draw.text((2, 2), title, fill=(0, 0, 200))
    crop.save(out)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--doc", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--crops", type=Path)
    parser.add_argument("--sample", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    record = json.loads(find_record(args.doc).read_text(encoding="utf-8"))
    book = load_catalog().get(args.doc)
    status_total: Counter = Counter()
    page_status_total: Counter = Counter()
    excluded_total: Counter = Counter()
    insert_total: Counter = Counter()
    pages_out = []
    auto_fixes = []
    sims_old, sims_new = [], []
    old_review = old_chars = 0

    for page in record["pages"]:
        l1 = page.get("l1_ocr") or {}
        results = results_from_engines(l1.get("engines") or {})
        if len(results) < 2:
            continue
        if "paddle_v6" in results and book is not None and page.get("l0_image"):
            fresh = paddle_v6.load(book, Path(page["l0_image"]).stem, FAMILY_TREE)
            if fresh is not None:
                results["paddle_v6"] = fresh
        # Bỏ engine lạc đề TRƯỚC khi chọn nền (vote_page_chars sàng lại + lệch thứ tự).
        outliers = find_outliers({n: han_only("".join(r.lines)) for n, r in results.items()})
        ranked = {n: r for n, r in results.items() if n not in outliers} or results
        backbone = rank_by_similarity(ranked, DEFAULT_PRIORITY)[0][0]
        vote = vote_page_chars({name: r.lines for name, r in results.items()}, backbone)
        page_status_total[vote.page_status] += 1
        for name, reason in vote.excluded.items():
            excluded_total[(name, reason.split(":")[0])] += 1

        counts = vote.counts()
        status_total.update(counts)
        insert_total.update(s.status for s in vote.slots if s.kind == "insert")
        old_review += old_char_review(l1)
        old_chars += len(han_only(l1.get("voted_text") or ""))

        final = "".join(vote.lines)
        bb_text = han_only("".join(results[backbone].lines))
        engine_texts = {n: han_only("".join(r.lines)) for n, r in results.items()}
        others = [t for n, t in engine_texts.items() if n != backbone]
        # Độ giống trung bình với các engine KHÁC nền: kết quả mới vs văn bản nền (≈ vote cũ)
        sims_old.append(st.mean(Levenshtein.normalized_similarity(bb_text, t) for t in others))
        sims_new.append(st.mean(Levenshtein.normalized_similarity(final, t) for t in others))

        line_starts = []
        pos = 0
        for line in vote.lines:
            line_starts.append(pos)
            pos += len(line)
        for s in vote.slots:
            if s.kind == "char" and s.status == "auto_fixed":
                auto_fixes.append(
                    {
                        "page_id": page.get("page_id"),
                        "backbone": backbone,
                        "line": s.line,
                        "char_in_line": s.index - line_starts[s.line],
                        "line_len": len(vote.lines[s.line]),
                        "from": s.backbone,
                        "to": s.final,
                        "votes": s.votes,
                        "context": vote.lines[s.line],
                    }
                )
        pages_out.append(
            {
                "page_id": page.get("page_id"),
                "backbone": backbone,
                "chars": sum(counts.values()),
                "status": dict(counts),
                "review_rate": round(vote.review_rate(), 4),
                "page_status": vote.page_status,
                "excluded": vote.excluded,
                "old_line_uncertain_rate": l1.get("uncertain_rate"),
                "lines": vote.lines,
                "slots": [slot_to_dict(s) for s in vote.slots if s.status != "unanimous"],
            }
        )

    chars = sum(v for k, v in status_total.items())
    need = status_total["suggested"] + status_total["tie"] + status_total["kept_weak"] + status_total["unaligned"]
    summary = {
        "doc_id": args.doc,
        "pages": len(pages_out),
        "chars": chars,
        "char_status": dict(status_total),
        "insert_status": dict(insert_total),
        "page_status": dict(page_status_total),
        "excluded": {f"{n} ({why})": c for (n, why), c in excluded_total.most_common()},
        "review_rate_new": round(need / chars, 4) if chars else None,
        "review_rate_old_char_estimate": round(old_review / old_chars, 4) if old_chars else None,
        "old_line_uncertain_rate_median": st.median(float(p["old_line_uncertain_rate"] or 0) for p in pages_out),
        "similarity_to_other_engines": {"backbone_text": round(st.mean(sims_old), 4), "new_vote": round(st.mean(sims_new), 4)},
        "auto_fix_pairs_top": Counter(f"{a['from']}→{a['to']}" for a in auto_fixes).most_common(15),
    }
    args.out.write_text(json.dumps({"summary": summary, "pages": pages_out, "auto_fixes": auto_fixes}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.crops:
        args.crops.mkdir(parents=True, exist_ok=True)
        rng = random.Random(args.seed)
        candidates = [a for a in auto_fixes if a["backbone"] == "paddle_v6"]
        chosen = rng.sample(candidates, min(args.sample, len(candidates)))
        page_by_id = {p.get("page_id"): p for p in record["pages"]}
        for n, a in enumerate(chosen, 1):
            crop_auto_fix(
                page_by_id[a["page_id"]], book, a["line"], a["char_in_line"], a["line_len"],
                args.crops / f"{n:02d}_p{a['page_id']}.png", f"{n}",
            )
            print(f"{n:02d} p{a['page_id']} dòng {a['line'] + 1}: {a['from']} → {a['to']}  phiếu {a['votes']}  | {a['context']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
