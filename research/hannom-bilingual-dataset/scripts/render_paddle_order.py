"""Vẽ thứ tự đọc MỚI của paddle_v6 lên ảnh trang để soát bằng mắt (giai đoạn D).

Mỗi khung chữ Paddle được viền + đánh số theo thứ tự `column_order` (1 = đọc
đầu tiên). Thứ tự đúng của chữ Hán dọc: số tăng dần từ cột PHẢI sang TRÁI,
trong cột từ trên xuống. Không gọi API, chỉ đọc ảnh + `{stem}-paddleocr.json`.

Nhóm mẫu (--sample):
  random  2 trang/bộ, ngẫu nhiên có seed (trang văn bản)
  notes   trang có chú thích chữ nhỏ song song (khung cùng khoảng y trong 1 cột)
  lowtau  trang văn bản có Kendall τ thấp nhất (eval_paddle_order)
  chart   trang phả đồ (世系圖)
  changed trang vote đổi NỘI DUNG khi sắp lại Paddle (revote_paddle_order)

Chạy: python3 scripts/render_paddle_order.py --out DIR [--sample random notes ...] [--seed 42]
Ảnh ra nằm ngoài repo (ảnh gốc thuộc data/, không commit).
"""

from __future__ import annotations

import argparse
import glob
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import DATA_REPO_ROOT, FAMILY_TREE  # noqa: E402
from ocr_adapters.base import first_existing_file, paddle_dir_candidates  # noqa: E402
from ocr_adapters.paddle_v6 import COLUMN_OVERLAP, SIDE_BY_SIDE_OVERLAP, boxes_from_json, column_order_indices  # noqa: E402
from vote_ocr import load_catalog  # noqa: E402

FONT_CANDIDATES = ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc")
MAX_SIDE = 1400


def iter_paddle_pages():
    catalog = load_catalog()
    for path in sorted(glob.glob(str(DATA_REPO_ROOT / "data" / "track[12]_*" / "*.json"))):
        record = json.loads(Path(path).read_text(encoding="utf-8"))
        book = catalog.get(record["doc_id"])
        for page in record.get("pages", []):
            engines = (page.get("l1_ocr") or {}).get("engines") or {}
            if "paddle_v6" not in engines or book is None or not page.get("l0_image"):
                continue
            stem = Path(page["l0_image"]).stem
            json_path = first_existing_file(paddle_dir_candidates(book, FAMILY_TREE), f"{stem}-paddleocr.json")
            if json_path is None:
                continue
            yield record, page, book, json_path


def has_side_by_side_notes(boxes: list) -> bool:
    """Có ít nhất 2 khung cùng cột và chồng nhau theo y (chú thích 2 hàng)."""
    items = []
    for poly, text, _ in boxes:
        if not (text or "").strip():
            continue
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        items.append((min(xs), max(xs), min(ys), max(ys)))
    for i, a in enumerate(items):
        for b in items[i + 1 :]:
            x_overlap = min(a[1], b[1]) - max(a[0], b[0])
            y_overlap = min(a[3], b[3]) - max(a[2], b[2])
            same_col = x_overlap > COLUMN_OVERLAP * min(a[1] - a[0], b[1] - b[0])
            # cùng "cột lớn" nhưng lệch x (2 hàng chú thích): chồng y mạnh, x chạm nhau
            side = y_overlap > SIDE_BY_SIDE_OVERLAP * min(a[3] - a[2], b[3] - b[2]) and x_overlap > -5
            if side and not same_col and (a[1] - a[0]) < 40 and (b[1] - b[0]) < 40:
                return True
    return False


def render(image_path: Path, boxes: list, out_path: Path, title: str) -> None:
    img = Image.open(image_path).convert("RGB")
    scale = min(1.0, MAX_SIDE / max(img.size))
    if scale < 1.0:
        img = img.resize((round(img.width * scale), round(img.height * scale)))
    draw = ImageDraw.Draw(img)
    font_path = next((f for f in FONT_CANDIDATES if Path(f).exists()), None)
    size = max(14, round(img.width / 45))
    font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()

    # Theo CHỈ SỐ khung, không theo chữ — 2 khung trùng chữ không bị gắn nhầm số.
    for n, index in enumerate(column_order_indices(boxes), start=1):
        poly = boxes[index][0]
        pts = [(p[0] * scale, p[1] * scale) for p in poly]
        draw.polygon(pts, outline=(220, 0, 0), width=2)
        x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
        box_w = max(p[0] for p in pts) - x0
        label = str(n)
        # Nhãn nằm TRONG khung, cỡ chữ vừa bề rộng khung → khung sát nhau không đè nhãn.
        fsize = max(9, min(size, int(box_w / (0.6 * len(label)))))
        lfont = ImageFont.truetype(font_path, fsize) if font_path else font
        w = draw.textlength(label, font=lfont)
        draw.rectangle([x0 + 1, y0 + 1, x0 + w + 3, y0 + fsize + 3], fill=(255, 255, 255))
        draw.text((x0 + 2, y0 + 1), label, fill=(0, 0, 200), font=lfont)
    draw.rectangle([0, 0, img.width, size + 8], fill=(255, 255, 220))
    draw.text((4, 2), title, fill=(0, 0, 0), font=font)
    img.save(out_path)


def select(samples: list[str], seed: int) -> dict[str, list[tuple]]:
    pages = list(iter_paddle_pages())
    rng = random.Random(seed)
    chosen: dict[str, list[tuple]] = {}

    def is_chart(page) -> bool:
        engines = page["l1_ocr"]["engines"]
        return any("世系圖" in (e.get("text") or "") for e in engines.values())

    text_pages = [p for p in pages if not is_chart(p[1])]
    if "random" in samples:
        by_doc: dict[str, list] = {}
        for p in text_pages:
            by_doc.setdefault(p[0]["doc_id"], []).append(p)
        chosen["random"] = [x for doc in sorted(by_doc) for x in rng.sample(by_doc[doc], min(2, len(by_doc[doc])))]
    if "notes" in samples:
        notes = [p for p in text_pages if has_side_by_side_notes(boxes_from_json(p[3]))]
        chosen["notes"] = rng.sample(notes, min(8, len(notes)))
    if "chart" in samples:
        charts = [p for p in pages if is_chart(p[1])]
        chosen["chart"] = rng.sample(charts, min(4, len(charts)))
    if "lowtau" in samples:
        from eval_paddle_order import evaluate

        rows = [r for r in evaluate()["pages"] if r["group"] == "text" and "adapter" in r]
        worst = {(r["doc_id"], r["page_id"]) for r in sorted(rows, key=lambda r: r["adapter"])[:10]}
        chosen["lowtau"] = [p for p in pages if (p[0]["doc_id"], p[1].get("page_id")) in worst]
    if "changed" in samples:
        from revote_paddle_order import nonempty_lines, revote_page

        changed = []
        for p in pages:
            outcome = revote_page(p[1], p[2])
            if outcome and Counter(nonempty_lines(outcome["old"].get("voted_text"))) != Counter(
                nonempty_lines(outcome["new"].get("voted_text"))
            ):
                changed.append(p)
        chosen["changed"] = changed
    return chosen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sample", nargs="+", default=["random", "notes", "lowtau", "chart", "changed"])
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    index: list[dict[str, Any]] = []
    for group, items in select(args.sample, args.seed).items():
        (args.out / group).mkdir(parents=True, exist_ok=True)
        for record, page, _book, json_path in items:
            doc_id, page_id = record["doc_id"], page.get("page_id")
            out_path = args.out / group / f"{doc_id}__{page_id}.png"
            render(FAMILY_TREE / page["l0_image"], boxes_from_json(json_path), out_path, f"{group} {doc_id} {page_id}")
            index.append({"group": group, "doc_id": doc_id, "page_id": page_id, "image": str(out_path)})
    (args.out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(Counter(r["group"] for r in index))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
