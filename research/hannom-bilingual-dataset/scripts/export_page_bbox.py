"""Xuất khung chữ Paddle (toạ độ trên ảnh gốc) theo trang để nạp lên web.

Đọc `{stem}-paddleocr.json` (result_bbox) của từng trang trong record corpus,
sắp theo thứ tự đọc (paddle_v6.column_order_indices: cột phải → trái, trong cột
trên → dưới) và ghi 1 file JSON:

  {"schema": 1, "books": {doc_id: {page_number: {"image_size": [w, h] | null,
                                                  "boxes": [{order, bbox_xyxy, han, confidence}]}}}}

page_number đánh 1.. theo thứ tự `pages` trong record — trùng cách importer
(nlp_family_extractor/tools/import_hannom_bilingual_corpus.py) tạo GiaPhaPage.
Nạp lên DB: nlp_family_extractor/tools/load_page_bbox.py.

Kiểm tra kích thước ảnh: toạ độ Paddle tính trên ảnh lúc OCR; nếu khung vượt
ra ngoài ảnh hiện có (ảnh đã bị thu nhỏ/cắt) → trang bị bỏ và in cảnh báo.

Không gọi API, không sửa record. Chạy:
  python3 scripts/export_page_bbox.py --doc nom-147 [--doc ...] --out /tmp/bbox.json
  python3 scripts/export_page_bbox.py --all --out /tmp/bbox.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import DATA_REPO_ROOT, FAMILY_TREE  # noqa: E402
from ocr_adapters.base import first_existing_file, paddle_dir_candidates, pages_dir_candidates  # noqa: E402
from ocr_adapters.paddle_v6 import boxes_from_json, column_order_indices  # noqa: E402
from vote_ocr import load_catalog  # noqa: E402

# Khung được phép lệch ra ngoài ảnh vài pixel (Paddle làm tròn / nới khung).
EDGE_TOLERANCE = 8


def ordered_boxes(boxes: list[tuple[Any, str, float | None]]) -> list[dict[str, Any]]:
    """Khung theo thứ tự đọc, đánh số từ 1; bbox_xyxy = hình chữ nhật bao polygon."""
    out = []
    for order, i in enumerate(column_order_indices(boxes), start=1):
        poly, text, score = boxes[i]
        xs = [float(p[0]) for p in poly]
        ys = [float(p[1]) for p in poly]
        out.append(
            {
                "order": order,
                "bbox_xyxy": [int(min(xs)), int(min(ys)), int(round(max(xs))), int(round(max(ys)))],
                "han": text.strip(),
                "confidence": round(float(score), 4) if score is not None else None,
            }
        )
    return out


def fits_image(boxes: list[dict[str, Any]], size: tuple[int, int] | None) -> bool:
    if size is None:
        return True  # không đọc được ảnh → không kiểm được, vẫn xuất (in cảnh báo ở main)
    w, h = size
    return all(b["bbox_xyxy"][2] <= w + EDGE_TOLERANCE and b["bbox_xyxy"][3] <= h + EDGE_TOLERANCE for b in boxes)


def _image_size(book: dict[str, Any], stem: str) -> tuple[int, int] | None:
    try:
        from PIL import Image
    except ImportError:
        return None
    for ext in (".jpg", ".jpeg", ".png", ".JPG", ".PNG"):
        p = first_existing_file(pages_dir_candidates(book, FAMILY_TREE), f"{stem}{ext}")
        if p is not None:
            with Image.open(p) as img:
                return img.size
    return None


def export_book(record: dict[str, Any], book: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    pages: dict[str, Any] = {}
    warnings: list[str] = []
    for number, page in enumerate(record.get("pages") or [], start=1):
        stem = Path(page.get("l0_image") or "").stem
        if not stem:
            continue
        path = first_existing_file(paddle_dir_candidates(book, FAMILY_TREE), f"{stem}-paddleocr.json")
        raw = boxes_from_json(path) if path is not None else None
        if not raw:
            continue
        boxes = ordered_boxes(raw)
        if not boxes:
            continue
        size = _image_size(book, stem)
        if size is None:
            warnings.append(f"trang {number} ({stem}): không đọc được kích thước ảnh")
        elif not fits_image(boxes, size):
            warnings.append(f"trang {number} ({stem}): khung vượt ảnh {size} — BỎ")
            continue
        pages[str(number)] = {"image_size": list(size) if size else None, "boxes": boxes}
    return pages, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--doc", action="append", default=[])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    catalog = load_catalog()
    records = sorted((DATA_REPO_ROOT / "data").glob("track*/*.json"))
    out: dict[str, Any] = {"schema": 1, "books": {}}
    for path in records:
        doc_id = path.stem
        if not args.all and doc_id not in args.doc:
            continue
        book = catalog.get(doc_id)
        if book is None:
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        pages, warnings = export_book(record, book)
        for w in warnings:
            print(f"[{doc_id}] {w}", file=sys.stderr)
        if pages:
            out["books"][doc_id] = pages
        print(f"{doc_id}: {len(pages)}/{len(record.get('pages') or [])} trang có khung")
    args.out.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"→ {args.out} ({len(out['books'])} bộ)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
