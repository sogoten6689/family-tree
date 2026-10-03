"""Phân tích vì sao vote OCR có uncertain_rate cao (offline, không gọi API).

Giả thuyết cần kiểm tra: phần lớn "dòng chưa chắc chắn" là do các engine CHIA
DÒNG khác nhau (cùng chữ nhưng ngắt dòng khác), không phải do đọc sai chữ.

Hai phép đo, chỉ trên chữ Hán (bỏ khoảng trắng, dấu câu, Latin, số):

1. Theo cặp engine (A, B) trên mỗi trang:
   - line_sim: trung bình độ giống của mỗi dòng A với dòng khớp nhất của B
     (giống cách vote_line/best_match ghép dòng), lấy đối xứng A↔B.
   - page_sim: độ giống Levenshtein chuẩn hoá của TOÀN TRANG A với toàn trang B
     (ghép mọi dòng theo thứ tự) — không phụ thuộc chỗ ngắt dòng nhưng PHỤ THUỘC
     thứ tự dòng (paddle_v6 đọc cột ngược chiều các engine khác → page_sim thấp).
   - char_bag: tỉ lệ chữ chung (multiset) — không phụ thuộc cả ngắt lẫn thứ tự.

2. Với mỗi engine "lệch" trong uncertain_spans: so dòng đã vote với
   (a) dòng engine đó được ghép (similarity đã lưu) và
   (b) đoạn khớp nhất trong toàn trang của engine đó (cửa sổ Levenshtein).
   (b) ≥ SIM_MATCH trong khi (a) < SIM_MATCH → lệch do chia dòng, không phải
   đọc khác chữ.

3. Số chữ khác giữa dòng đã vote và dòng của engine lệch (edit distance), và tỉ
   lệ chưa chắc chắn THEO CHỮ (tổng edit distance tới engine lệch gần nhất /
   số chữ Hán của trang) — so với uncertain_rate đang tính THEO DÒNG.

Không có bộ chữ Hán chuẩn (gold) nên các số này đo ĐỘ ĐỒNG THUẬN giữa engine,
không đo độ CHÍNH XÁC.

Chạy: python3 scripts/analyze_vote_alignment.py [--json out.json]
"""

from __future__ import annotations

import argparse
import glob
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import DATA_REPO_ROOT  # noqa: E402

SIM_MATCH = 0.92  # cùng ngưỡng gom cụm của vote_ocr.vote_line
MIN_LINE_CHARS = 4  # dòng quá ngắn → khớp cửa sổ dễ ngẫu nhiên, bỏ qua


def is_han(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x3400 <= cp <= 0x4DBF
        or 0x4E00 <= cp <= 0x9FFF
        or 0xF900 <= cp <= 0xFAFF
        or 0x20000 <= cp <= 0x323AF
        or 0x2F800 <= cp <= 0x2FA1F
    )


def han_only(text: str) -> str:
    return "".join(ch for ch in text if is_han(ch))


def han_lines(text: str) -> list[str]:
    return [line for line in (han_only(raw) for raw in text.splitlines()) if line]


def sim(a: str, b: str) -> float:
    return Levenshtein.normalized_similarity(a, b)


def best_line_sim(lines_a: list[str], lines_b: list[str]) -> float:
    if not lines_a or not lines_b:
        return 0.0
    return st.mean(max(sim(a, b) for b in lines_b) for a in lines_a)


def best_window_sim(needle: str, haystack: str) -> float:
    """Độ giống của needle với đoạn con khớp nhất trong haystack.

    Dùng fuzz.partial_ratio (rapidfuzz, C) — thước đo Indel chứ không phải
    Levenshtein như vote; quét cửa sổ Levenshtein bằng Python quá chậm cho
    ~20k dòng. Indel phạt thay chữ (replace) nặng hơn Levenshtein, nên phép
    đo này THIÊN VỀ báo "khác chữ" → số "split_only" là cận dưới."""
    if not needle or not haystack:
        return 0.0
    return fuzz.partial_ratio(needle, haystack) / 100


def iter_pages(data_root: Path):
    for path in sorted(glob.glob(str(data_root / "data" / "track[12]_*" / "*.json"))):
        record = json.loads(Path(path).read_text(encoding="utf-8"))
        for page in record.get("pages", []):
            l1 = page.get("l1_ocr") or {}
            if l1.get("engines"):
                yield record["doc_id"], page.get("page_id"), l1


def analyze(data_root: Path) -> dict[str, Any]:
    pair_line: dict[tuple[str, str], list[float]] = defaultdict(list)
    pair_page: dict[tuple[str, str], list[float]] = defaultdict(list)
    pair_bag: dict[tuple[str, str], list[float]] = defaultdict(list)
    edit_hist: Counter = Counter()
    char_rates: list[float] = []
    near_lines = 0
    span_total = 0
    page_gap: list[float] = []
    span_counts = defaultdict(int)  # kind -> count
    span_by_engine: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    doc_rates: dict[str, list[float]] = defaultdict(list)
    pages = 0

    for doc_id, _page_id, l1 in iter_pages(data_root):
        pages += 1
        doc_rates[doc_id].append(float(l1.get("uncertain_rate") or 0))
        texts = {name: e.get("text") or "" for name, e in l1["engines"].items()}
        lines = {name: han_lines(t) for name, t in texts.items()}
        flat = {name: han_only(t) for name, t in texts.items()}

        gaps = []
        for a, b in combinations(sorted(texts), 2):
            if not flat[a] or not flat[b]:
                continue
            ls = (best_line_sim(lines[a], lines[b]) + best_line_sim(lines[b], lines[a])) / 2
            ps = sim(flat[a], flat[b])
            pair_line[(a, b)].append(ls)
            pair_page[(a, b)].append(ps)
            ca, cb = Counter(flat[a]), Counter(flat[b])
            pair_bag[(a, b)].append(sum((ca & cb).values()) / max(len(flat[a]), len(flat[b])))
            gaps.append(ps - ls)
        if gaps:
            page_gap.append(st.mean(gaps))

        uncertain_chars = 0
        for span in l1.get("uncertain_spans") or []:
            voted = han_only(span.get("voted_line") or "")
            span_total += 1
            dists = [Levenshtein.distance(voted, han_only(d.get("text") or "")) for d in span.get("disagreeing") or []]
            for dist in dists:
                edit_hist[min(dist, 6)] += 1
            if dists:
                uncertain_chars += min(min(dists), len(voted))
                near_lines += min(dists) <= 1
            for d in span.get("disagreeing") or []:
                engine = d.get("engine")
                if len(voted) < MIN_LINE_CHARS or engine not in flat:
                    kind = "short_or_missing"
                else:
                    line_s = sim(voted, han_only(d.get("text") or ""))
                    window_s = best_window_sim(voted, flat[engine])
                    if line_s >= SIM_MATCH:
                        kind = "line_already_close"
                    elif window_s >= SIM_MATCH:
                        kind = "split_only"  # chữ có trong trang engine kia, chỉ khác chỗ ngắt dòng
                    elif window_s - line_s >= 0.2:
                        kind = "split_and_reading"  # chia dòng làm tệ thêm, nhưng vẫn khác chữ
                    else:
                        kind = "reading_differs"  # khác chữ thật
                span_counts[kind] += 1
                span_by_engine[engine or "?"][kind] += 1
        voted_page = han_only(l1.get("voted_text") or "")
        if voted_page:
            char_rates.append(uncertain_chars / len(voted_page))

    pairs = []
    for key in sorted(pair_line):
        pairs.append(
            {
                "pair": f"{key[0]} ~ {key[1]}",
                "pages": len(pair_line[key]),
                "line_sim": round(st.mean(pair_line[key]), 3),
                "page_sim": round(st.mean(pair_page[key]), 3),
                "char_bag": round(st.mean(pair_bag[key]), 3),
            }
        )
    return {
        "pages": pages,
        "mean_page_minus_line": round(st.mean(page_gap), 3) if page_gap else None,
        "pairs": sorted(pairs, key=lambda p: -p["page_sim"]),
        "uncertain_rate_line_median": round(st.median(float(r) for rs in doc_rates.values() for r in rs), 3),
        "uncertain_rate_char_median": round(st.median(char_rates), 3) if char_rates else None,
        "edit_distance_hist": {(">=6" if k == 6 else str(k)): v for k, v in sorted(edit_hist.items())},
        "lines_closest_engine_within_1_char": [near_lines, span_total],
        "disagreements": dict(span_counts),
        "disagreements_by_engine": {k: dict(v) for k, v in span_by_engine.items()},
        "uncertain_rate_by_doc": {
            doc: {"pages": len(r), "mean": round(st.mean(r), 3)} for doc, r in sorted(doc_rates.items())
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-root", type=Path, default=DATA_REPO_ROOT)
    parser.add_argument("--json", type=Path, help="ghi kết quả đầy đủ ra file JSON")
    args = parser.parse_args()

    result = analyze(args.data_root)
    print(f"Trang có dữ liệu engine: {result['pages']}")
    print(f"page_sim - line_sim trung bình mỗi trang: {result['mean_page_minus_line']}")
    print("\nCặp engine (xếp theo page_sim):")
    for p in result["pairs"]:
        print(
            f"  {p['pair']:<34} trang={p['pages']:>5}  line_sim={p['line_sim']:.3f}"
            f"  page_sim={p['page_sim']:.3f}  char_bag={p['char_bag']:.3f}"
        )
    print(
        f"\nuncertain_rate trung vị: theo dòng={result['uncertain_rate_line_median']}"
        f"  theo chữ={result['uncertain_rate_char_median']}"
    )
    near, total_lines = result["lines_closest_engine_within_1_char"]
    print(f"Dòng chưa chắc chắn có engine lệch ≤1 chữ: {near}/{total_lines} ({near / max(1, total_lines):.0%})")
    hist_total = sum(result["edit_distance_hist"].values()) or 1
    print("Số chữ khác (dòng vote vs engine lệch): " + ", ".join(
        f"{k}: {v / hist_total:.0%}" for k, v in result["edit_distance_hist"].items()
    ))
    total = sum(result["disagreements"].values()) or 1
    print("\nPhân loại các lần engine 'lệch' trong uncertain_spans:")
    for kind, n in sorted(result["disagreements"].items(), key=lambda x: -x[1]):
        print(f"  {kind:<20} {n:>6}  ({n / total:.0%})")
    print("\nTheo engine:")
    for engine, kinds in sorted(result["disagreements_by_engine"].items()):
        sub = sum(kinds.values()) or 1
        parts = ", ".join(f"{k}={v} ({v / sub:.0%})" for k, v in sorted(kinds.items(), key=lambda x: -x[1]))
        print(f"  {engine:<16} {parts}")
    if args.json:
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nĐã ghi {args.json}")


if __name__ == "__main__":
    main()
