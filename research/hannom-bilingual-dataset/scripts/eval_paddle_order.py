"""Đánh giá thứ tự dòng của paddle_v6 so với engine khác (offline, không gọi API).

Với mỗi trang có paddle_v6: sắp các khung chữ trong `{stem}-paddleocr.json` theo
từng PHƯƠNG ÁN, ghép mỗi dòng với dòng giống nhất của engine tham chiếu
(kim_hannom_lab, deepseek; độ giống ≥ MATCH_MIN trên chữ Hán) rồi tính Kendall τ
giữa thứ tự phương án và thứ tự của engine tham chiếu.

Lưu ý khoa học: τ đo ĐỘ KHỚP với thứ tự engine khác, không phải với thứ tự
đúng (engine tham chiếu cũng có thể sai, vd trang có chú thích nhỏ). Thứ tự
đúng phải đối chiếu ảnh (giai đoạn D của kế hoạch kiểm thử).

Chạy: python3 scripts/eval_paddle_order.py [--json out.json]
"""

from __future__ import annotations

import argparse
import glob
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from rapidfuzz.distance import Levenshtein

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import DATA_REPO_ROOT, FAMILY_TREE  # noqa: E402
from analyze_vote_alignment import han_only  # noqa: E402
from ocr_adapters.base import first_existing_file, paddle_dir_candidates  # noqa: E402
from ocr_adapters.paddle_v6 import boxes_from_json, column_order  # noqa: E402
from vote_ocr import load_catalog  # noqa: E402

MATCH_MIN = 0.5
REFERENCES = ("kim_hannom_lab", "deepseek")


def _box_x_center(poly) -> float:
    xs = [float(p[0]) for p in poly]
    return (min(xs) + max(xs)) / 2


VARIANTS: dict[str, Callable[[list], list[str]]] = {
    # Thứ tự PaddleOCR trả (theo mép trên) — trước khi sửa.
    "paddle_raw": lambda boxes: [t.strip() for _, t, _ in boxes if (t or "").strip()],
    # Chỉ theo tâm x phải → trái (không gom cột).
    "x_center": lambda boxes: [
        t.strip() for _, t, _ in sorted(boxes, key=lambda b: -_box_x_center(b[0])) if (t or "").strip()
    ],
    # Thuật toán trong adapter (ocr_adapters/paddle_v6.column_order).
    "adapter": lambda boxes: [t for t, _ in column_order(boxes)],
}


def kendall_tau(ranks: list[int]) -> float | None:
    """τ giữa thứ tự 0..n-1 và `ranks` (bỏ cặp hoà)."""
    concordant = discordant = 0
    for i in range(len(ranks)):
        for j in range(i + 1, len(ranks)):
            if ranks[i] < ranks[j]:
                concordant += 1
            elif ranks[i] > ranks[j]:
                discordant += 1
    total = concordant + discordant
    return (concordant - discordant) / total if total else None


def order_tau(lines: list[str], reference: list[str]) -> float | None:
    ref = [han_only(r) for r in reference]
    ranks = []
    for line in lines:
        h = han_only(line)
        if len(h) < 2:
            continue
        best_idx, best_sim = None, 0.0
        for idx, r in enumerate(ref):
            if not r:
                continue
            s = Levenshtein.normalized_similarity(h, r)
            if s > best_sim:
                best_idx, best_sim = idx, s
        if best_idx is not None and best_sim >= MATCH_MIN:
            ranks.append(best_idx)
    return kendall_tau(ranks) if len(ranks) >= 3 else None


def is_chart_page(engines: dict[str, Any]) -> bool:
    """Trang phả đồ (世系圖) — dạng ô lưới, không có 1 thứ tự đọc tuyến tính."""
    return any("世系圖" in (e.get("text") or "") or "世系图" in (e.get("text") or "") for e in engines.values())


def evaluate(variants: dict[str, Callable[[list], list[str]]] | None = None) -> dict[str, Any]:
    variants = variants or VARIANTS
    catalog = load_catalog()
    taus: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))  # group -> variant -> τ
    per_doc: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    pages: list[dict[str, Any]] = []
    for path in sorted(glob.glob(str(DATA_REPO_ROOT / "data" / "track[12]_*" / "*.json"))):
        record = json.loads(Path(path).read_text(encoding="utf-8"))
        book = catalog.get(record["doc_id"])
        for page in record.get("pages", []):
            engines = (page.get("l1_ocr") or {}).get("engines") or {}
            if "paddle_v6" not in engines or book is None or not page.get("l0_image"):
                continue
            json_path = first_existing_file(
                paddle_dir_candidates(book, FAMILY_TREE), f"{Path(page['l0_image']).stem}-paddleocr.json"
            )
            boxes = boxes_from_json(json_path) if json_path else None
            refs = [(engines[r].get("text") or "").splitlines() for r in REFERENCES if r in engines]
            if not boxes or not refs:
                continue
            group = "chart" if is_chart_page(engines) else "text"
            row = {"doc_id": record["doc_id"], "page_id": page.get("page_id"), "group": group}
            for name, fn in variants.items():
                values = [t for t in (order_tau(fn(boxes), ref) for ref in refs) if t is not None]
                if not values:
                    continue
                tau = st.mean(values)
                row[name] = round(tau, 3)
                taus[group][name].append(tau)
                if group == "text":
                    per_doc[record["doc_id"]][name].append(tau)
            pages.append(row)

    def summary(values: list[float]) -> dict[str, float]:
        return {
            "n": len(values),
            "median": round(st.median(values), 3),
            "mean": round(st.mean(values), 3),
            "share_ge_0_9": round(sum(v >= 0.9 for v in values) / len(values), 3),
        }

    return {
        "groups": {g: {v: summary(vals) for v, vals in by_variant.items() if vals} for g, by_variant in taus.items()},
        "per_doc_median": {
            doc: {v: round(st.median(vals), 3) for v, vals in by_variant.items() if vals}
            for doc, by_variant in sorted(per_doc.items())
        },
        "pages": pages,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    result = evaluate()
    for group, by_variant in result["groups"].items():
        print(f"== {group}")
        for name, s in by_variant.items():
            print(f"  {name:<12} n={s['n']:>5}  τ median={s['median']:+.3f}  mean={s['mean']:+.3f}  τ≥0.9: {s['share_ge_0_9']:.0%}")
    print("== text: τ trung vị theo bộ")
    names = list(VARIANTS)
    print("  " + " " * 16 + "".join(f"{n:>12}" for n in names))
    for doc, by_variant in result["per_doc_median"].items():
        print(f"  {doc:<16}" + "".join(f"{by_variant.get(n, float('nan')):>+12.3f}" for n in names))
    if args.json:
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
