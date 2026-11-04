"""Tạo vị trí từng chữ cho thẻ Soát: <cuon>/khung/<trang>.json, từ ảnh trang và cap_cau.csv.

PaddleOCR (miễn phí, chạy trên máy) cho khung cột và chữ nhận dạng, đọc ở hai độ phân giải vì chữ to
chỉ bắt được khi thu nhỏ ảnh. Chữ Paddle có thể sai, nên chỉ dùng để định vị: cả trang bản máy được dóng
vào các khung theo thứ tự đọc. Trong mỗi khung, từng chữ được tách theo khoảng trắng giữa các nét mực;
không tách khớp số chữ thì chia đều và đánh dấu `u` (ước lượng). Chữ không có khung phù hợp thì bỏ khỏi
lớp phủ, số lượng ghi ở trường `thieu`.

    .venv-paddleocr/bin/python nlp_family_extractor/tools/tao_khung_doi_chieu.py <thu-muc-cuon> [--ban-tam 0.466,0.523]

Sau khi tạo, nên vẽ thử vài trang lên ảnh: độ phủ cao chưa chắc chữ đã nằm đúng chỗ. tq-347 dùng --ban-tam như trên.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

HAN_RE = re.compile(r"[㐀-䶿一-鿿豈-﫿\U00020000-\U0003ffff]")
MIN_COLUMN_OVERLAP = 0.5
MIN_EVEN_SHARE = 0.6
NOISE_RATIO = 0.4
INK_THRESHOLD = 128
COARSE_SIDE = 1600
MAX_BOX_OVERLAP = 0.3
MIN_GLYPH_RATIO = 0.5
MIN_PAGE_MATCH = 0.2


def han_only(text: str) -> str:
    return "".join(HAN_RE.findall(text))


def char_box(box: dict, index: int, count: int | None = None) -> list[int]:
    """Khung của ô thứ `index` khi chia khung Paddle thành `count` ô: cột đứng chia theo y, dòng ngang theo x."""
    x0, y0, x1, y1 = box["box"]
    n = count or max(len(box["text"]), 1)
    if y1 - y0 >= x1 - x0:
        step = (y1 - y0) / n
        return [x0, round(y0 + index * step), x1, round(y0 + (index + 1) * step)]
    step = (x1 - x0) / n
    return [round(x0 + index * step), y0, round(x0 + (index + 1) * step), y1]


def _columns(boxes: list[dict]) -> list[dict]:
    """Cột từ phải sang trái, trong cột từ trên xuống."""
    columns: list[list[dict]] = []
    span = (0, 0)
    for box in sorted(boxes, key=lambda b: -(b["box"][0] + b["box"][2])):
        x0, x1 = box["box"][0], box["box"][2]
        overlap = min(span[1], x1) - max(span[0], x0)
        if columns and overlap > MIN_COLUMN_OVERLAP * min(span[1] - span[0], x1 - x0):
            columns[-1].append(box)
            span = (min(span[0], x0), max(span[1], x1))
        else:
            columns.append([box])
            span = (x0, x1)
    return [b for col in columns for b in sorted(col, key=lambda b: b["box"][1])]


def _tiers(boxes: list[dict]) -> list[list[dict]]:
    """Bảng phả hệ chia thành các tầng ngang; tầng là dải y không khung nào vắt qua. Văn xuôi chỉ có một tầng."""
    tiers: list[list[dict]] = []
    bottom = None
    for box in sorted(boxes, key=lambda b: b["box"][1]):
        if bottom is None or box["box"][1] > bottom:
            tiers.append([])
            bottom = box["box"][3]
        tiers[-1].append(box)
        bottom = max(bottom, box["box"][3])
    return tiers


def _runs(mask) -> list[list[int]]:
    """Các đoạn liên tiếp có giá trị đúng, dạng [đầu, cuối)."""
    runs: list[list[int]] = []
    start = None
    for i, on in enumerate(mask):
        if on and start is None:
            start = i
        elif not on and start is not None:
            runs.append([start, i])
            start = None
    if start is not None:
        runs.append([start, len(mask)])
    return runs


def _split_along(crop, size: int) -> list[tuple[int, int]]:
    """Tách một cột mực thành các chữ theo chiều đọc. Nét rời của một chữ (như 二, 三) được gộp lại."""
    merged: list[list[int]] = []
    for run in _runs(crop.sum(axis=1) > max(1, 0.03 * crop.shape[1])):
        if merged and run[1] - merged[-1][0] < 1.15 * size and run[0] - merged[-1][1] < 0.5 * size:
            merged[-1][1] = run[1]
        else:
            merged.append(run)
    cells: list[tuple[int, int]] = []
    for a, b in merged:
        n = max(1, round((b - a) / size))
        cells += [(a + (b - a) * k // n, a + (b - a) * (k + 1) // n) for k in range(n)]
    return cells


def box_cells(box: dict, ink) -> list[list[int]]:
    """Khung sát nét của từng chữ trong một khung Paddle. `ink` là ma trận đúng/sai của cả ảnh, đúng là có mực."""
    height, width = ink.shape
    x0, y0 = max(box["box"][0], 0), max(box["box"][1], 0)
    x1, y1 = min(box["box"][2], width), min(box["box"][3], height)
    horizontal = x1 - x0 > y1 - y0
    crop = ink[y0:y1, x0:x1].T if horizontal else ink[y0:y1, x0:x1]
    if crop.size == 0:
        return []
    # Khung Paddle hay lấn sang cột kề, nên chỉ giữ dải mực rộng nhất. Chữ gần vuông nên bề ngang là cỡ chữ.
    across = _runs(crop.sum(axis=0) > max(1, 0.02 * crop.shape[0]))
    if not across:
        return []
    c0, c1 = max(across, key=lambda r: r[1] - r[0])
    column = crop[:, c0:c1]
    cells = []
    for a, b in _split_along(column, c1 - c0):
        part = column[a:b]
        rows, cols = _runs(part.any(axis=1)), _runs(part.any(axis=0))
        if not rows or not cols:
            continue
        top, bottom = a + rows[0][0], a + rows[-1][1]
        left, right = c0 + cols[0][0], c0 + cols[-1][1]
        cells.append(
            [x0 + top, y0 + left, x0 + bottom, y0 + right] if horizontal else [x0 + left, y0 + top, x0 + right, y0 + bottom]
        )
    return cells


def merge_boxes(fine: list[dict], coarse: list[dict], page_text: str) -> list[dict]:
    """Gộp hai lần đọc. Chỗ trùng nhau giữ lần đọc có nhiều chữ khớp bản máy hơn (hoa văn đọc ra toàn chữ lạ)."""
    known = set(page_text)

    def area(b: list[int]) -> int:
        return max(b[2] - b[0], 0) * max(b[3] - b[1], 0)

    def overlaps(a: list[int], b: list[int]) -> bool:
        common = [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]
        if common[2] <= common[0] or common[3] <= common[1]:
            return False
        return area(common) > MAX_BOX_OVERLAP * min(area(a), area(b))

    def score(boxes: list[dict]) -> int:
        return sum(ch in known for box in boxes for ch in box["text"])

    kept = list(fine)
    for box in coarse:
        clash = [f for f in kept if overlaps(box["box"], f["box"])]
        if not clash or score([box]) > score(clash):
            kept = [f for f in kept if f not in clash] + [box]
    return kept


def reading_order(boxes: list[dict], gutter: tuple[int, int] | None = None) -> list[dict]:
    """Thứ tự đọc sách chữ dọc: trang phải trước trang trái, từng tầng từ trên xuống, trong tầng theo cột.

    `gutter` là dải x của bản tâm (phần in sẵn giữa hai trang): khung nằm trong đó không phải nội dung.
    """
    if not boxes:
        return []
    sizes = sorted(min(b["box"][2] - b["box"][0], b["box"][3] - b["box"][1]) for b in boxes)
    # Lấy mốc ở một phần ba dưới, vì trang bìa chỉ có vài khung rất to.
    noise = NOISE_RATIO * sizes[len(sizes) // 3]
    body = [b for b in boxes if min(b["box"][2] - b["box"][0], b["box"][3] - b["box"][1]) >= noise]
    if gutter is None:
        halves = [body]
    else:
        center = lambda b: (b["box"][0] + b["box"][2]) / 2
        body = [b for b in body if not gutter[0] <= center(b) <= gutter[1]]
        halves = [[b for b in body if center(b) > gutter[1]], [b for b in body if center(b) < gutter[0]]]
    return [b for half in halves for tier in _tiers(half) for b in _columns(tier)]


def _common_subsequence(a: str, b: list[str]) -> list[tuple[int, int]]:
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            dp[i][j] = dp[i + 1][j + 1] + 1 if a[i] == b[j] else max(dp[i + 1][j], dp[i][j + 1])
    pairs = []
    i = j = 0
    while i < n and j < m:
        if a[i] == b[j] and dp[i][j] == dp[i + 1][j + 1] + 1:
            pairs.append((i, j))
            i, j = i + 1, j + 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


def _glyph_length(box: dict) -> float:
    x0, y0, x1, y1 = box["box"]
    return max(y1 - y0, x1 - x0) / max(len(box["text"]), 1)


def _fill_gap(gap: list[int], read: list[int], seq: list[tuple[int, int]], boxes: list[dict], left: int | None, right: int | None) -> dict[int, int]:
    """Chữ bản máy nằm giữa hai chữ đã khớp nhận ô đọc nào. Chữ không có ô đọc phù hợp thì bỏ, không đoán."""
    if left is not None and left == right:
        # Cùng một khung: Paddle có thể đọc thiếu chữ, ô đọc chỉ để biết chữ thuộc khung nào.
        anchor = read or [next(j for j, s in enumerate(seq) if s[0] == left)]
        return {t: anchor[k * len(anchor) // len(gap)] for k, t in enumerate(gap)}
    near_left = [j for j in read if seq[j][0] == left]
    near_right = [j for j in read if seq[j][0] == right]
    # Đầu và cuối trang không có chữ khớp chặn hai bên thì không có gì bảo đảm khung ở giữa là đúng dòng này.
    has_middle = left is not None and right is not None and len(near_left) + len(near_right) < len(read)
    if len(gap) > len(near_left) + len(near_right) and has_middle:
        # Có khung đọc sai cả cột: chia theo chiều dài thực của khung, vì số chữ đọc được không đáng tin.
        weights = [_glyph_length(boxes[seq[j][0]]) for j in read]
        total = sum(weights)
        out, seen, r = {}, weights[0], 0
        for k, t in enumerate(gap):
            target = (k + 0.5) / len(gap) * total
            while seen < target and r < len(read) - 1:
                r += 1
                seen += weights[r]
            out[t] = read[r]
        return out
    room = len(near_left) + len(near_right)
    take_left = min(len(near_left), round(len(gap) * len(near_left) / room)) if room else 0
    take_right = min(len(near_right), len(gap) - take_left)
    out = dict(zip(gap[:take_left], near_left))
    if take_right:
        out.update(zip(gap[-take_right:], near_right[-take_right:]))
    return out


def _positions(box: dict, read_at: list[int], cells: list[list[int]]) -> tuple[list[list[int]], bool]:
    """Vị trí các chữ được gán vào khung, và vị trí đó có phải tách từ nét mực không."""
    n, m, read = len(read_at), len(cells), len(box["text"])
    if m == n:
        return cells, True
    if m == read:
        return [cells[j] for j in read_at], True
    # Dấu ngoặc trên ảnh cũng chiếm một ô mực, tuy không phải chữ Hán.
    raw = box.get("raw", "")
    if raw and m == len(raw):
        slots = [i for i, ch in enumerate(raw) if HAN_RE.match(ch)]
        return [cells[slots[j]] for j in read_at], True
    if m > n:
        return [cells[k * m // n] for k in range(n)], False
    if n >= MIN_EVEN_SHARE * read:
        return [char_box(box, k, n) for k in range(n)], False
    return [char_box(box, j) for j in read_at], False


def locate_rows(rows: list[str], boxes: list[dict], gutter: tuple[int, int] | None = None, ink=None) -> tuple[list[dict], int]:
    """Dóng cả trang bản máy vào các khung theo thứ tự đọc. Trả về các chữ có vị trí và số chữ thiếu."""
    text = "".join(han_only(row) for row in rows)
    ordered = reading_order(boxes, gutter)
    seq = [(b, j) for b, box in enumerate(ordered) for j in range(len(box["text"]))]
    read = [ordered[b]["text"][j] for b, j in seq]
    pairs = _common_subsequence(text, read)
    # Gần như không khớp chữ nào thì khung là hoa văn hoặc nhiễu (như trang bìa), đặt chữ vào sẽ sai.
    if len(pairs) < MIN_PAGE_MATCH * len(text):
        return [], len(text)

    where = dict(pairs)
    prev_t, prev_r = -1, -1
    for t, r in [*pairs, (len(text), len(seq))]:
        gap = list(range(prev_t + 1, t))
        if gap:
            left = seq[prev_r][0] if prev_r >= 0 else None
            right = seq[r][0] if r < len(seq) else None
            where.update(_fill_gap(gap, list(range(prev_r + 1, r)), seq, ordered, left, right))
        prev_t, prev_r = t, r

    typical_glyph = sorted(_glyph_length(box) for box in ordered)[len(ordered) // 2]
    per_box: dict[int, list[int]] = {}
    for t in sorted(where):
        per_box.setdefault(seq[where[t]][0], []).append(t)
    chars = []
    for b, members in per_box.items():
        box = ordered[b]
        # Nhồi đến mức mỗi chữ nhỏ hơn hẳn cỡ chữ thường của trang thì vị trí không còn ý nghĩa.
        x0, y0, x1, y1 = box["box"]
        crowded = len(members) > len(box["text"])
        if crowded and max(y1 - y0, x1 - x0) / len(members) < MIN_GLYPH_RATIO * typical_glyph:
            continue
        cells = box_cells(box, ink) if ink is not None else []
        positions, exact = _positions(box, [seq[where[t]][1] for t in members], cells)
        for t, position in zip(members, positions):
            chars.append((t, {"c": text[t], "b": position} if exact else {"c": text[t], "b": position, "u": 1}))
    chars.sort(key=lambda c: c[0])
    return [c for _, c in chars], len(text) - len(chars)


def read_rows(book_dir: Path) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    with (book_dir / "cap_cau.csv").open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            rows.setdefault(r["trang"], []).append(r["han"])
    return rows


def detect(image: Path, ocr) -> list[dict]:
    result = ocr.predict(str(image))[0]
    boxes = []
    for poly, text in zip(result["dt_polys"], result["rec_texts"]):
        xs, ys = [int(p[0]) for p in poly], [int(p[1]) for p in poly]
        clean = han_only(text)
        if clean:
            boxes.append({"box": [min(xs), min(ys), max(xs), max(ys)], "text": clean, "raw": text})
    return boxes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book_dir", type=Path)
    parser.add_argument(
        "--ban-tam",
        type=lambda v: tuple(float(x) for x in v.split(",")),
        help="dải bản tâm theo tỉ lệ chiều rộng ảnh, ví dụ 0.445,0.53 (sách đóng hai trang một ảnh)",
    )
    args = parser.parse_args()

    import numpy as np
    from paddleocr import PaddleOCR
    from PIL import Image

    models = {
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "use_textline_orientation": False,
        "text_detection_model_name": "PP-OCRv5_mobile_det",
        "text_recognition_model_name": "PP-OCRv5_mobile_rec",
    }
    ocr = PaddleOCR(**models)
    ocr_coarse = PaddleOCR(**models, text_det_limit_side_len=COARSE_SIDE, text_det_limit_type="max")
    rows = read_rows(args.book_dir)
    out_dir = args.book_dir / "khung"
    out_dir.mkdir(exist_ok=True)
    total = placed = estimated = 0
    for page, page_rows in sorted(rows.items()):
        image = next(p for p in (args.book_dir / "anh" / f"{page}{e}" for e in (".jpg", ".jpeg", ".png")) if p.is_file())
        with Image.open(image) as img:
            width, height = img.size
            ink = np.array(img.convert("L")) < INK_THRESHOLD
        gutter = (args.ban_tam[0] * width, args.ban_tam[1] * width) if args.ban_tam else None
        boxes = merge_boxes(detect(image, ocr), detect(image, ocr_coarse), han_only("".join(page_rows)))
        chars, missing = locate_rows(page_rows, boxes, gutter, ink)
        payload = {"rong": width, "cao": height, "chu": chars, "thieu": missing}
        (out_dir / f"{page}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        total += len(chars) + missing
        placed += len(chars)
        rough = sum("u" in c for c in chars)
        estimated += rough
        print(f"{page}: định vị {len(chars)}/{len(chars) + missing} chữ, {rough} chữ ước lượng")
    print(f"Tổng: {placed}/{total} chữ ({placed / total:.1%}), {estimated} chữ ước lượng" if total else "Không có chữ nào.")


if __name__ == "__main__":
    main()
