#!/usr/bin/env python3
"""Draw OCR bounding-box overlays from existing Paddle JSON (no re-OCR).

From repo root:

  python3 nlp_family_extractor/tools/draw_hannom_bbox.py --all --skip-existing
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from ocr_hannom_catalog import book_work_root, load_catalog  # noqa: E402
from ocr_paddleocr import list_page_images  # noqa: E402

from PIL import Image, ImageDraw


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _as_points(poly: Any) -> list[tuple[int, int]]:
    if not isinstance(poly, (list, tuple)) or len(poly) < 3:
        return []
    points: list[tuple[int, int]] = []
    for item in poly:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            try:
                points.append((int(round(float(item[0]))), int(round(float(item[1])))))
            except (TypeError, ValueError):
                return []
    return points if len(points) >= 3 else []


def score_color(score: float | None) -> tuple[int, int, int]:
    if score is None:
        return (220, 70, 40)
    if score >= 0.85:
        return (46, 125, 50)
    if score >= 0.6:
        return (230, 140, 20)
    return (200, 40, 40)


def draw_overlay(image_path: Path, record: dict[str, Any], dest: Path) -> None:
    image = Image.open(image_path).convert("RGB")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width = max(2, min(image.size) // 280)
    for item in record.get("result_bbox") or []:
        if not isinstance(item, (list, tuple)) or len(item) < 1:
            continue
        points = _as_points(item[0])
        if not points:
            continue
        score = None
        if len(item) >= 2 and isinstance(item[1], (list, tuple)) and len(item[1]) >= 2:
            try:
                score = float(item[1][1])
            except (TypeError, ValueError):
                score = None
        color = score_color(score)
        draw.polygon(points, fill=color + (40,))
        draw.polygon(points, outline=color + (255,), width=width)
    composed = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    dest.parent.mkdir(parents=True, exist_ok=True)
    composed.save(dest, quality=88)


def pages_dir_for(book: dict[str, Any], repo: Path) -> Path | None:
    paths = book.get("paths") or {}
    for key in ("pages", "root"):
        rel = paths.get(key)
        if not rel:
            continue
        path = repo / rel
        if path.is_dir():
            return path
    if book.get("source") == "tong_pho_pdf":
        rendered = repo / "data/du_lieu_han_nom_moi/13_8_2026" / book["book_id"] / "pages"
        if rendered.is_dir():
            return rendered
    return None


def process_book(book: dict[str, Any], repo: Path, skip_existing: bool) -> tuple[int, int]:
    pages_dir = pages_dir_for(book, repo)
    if pages_dir is None:
        print(f"— skip {book['book_id']} (không có ảnh)")
        return 0, 0
    images = list_page_images(pages_dir, None)
    if not images:
        print(f"— skip {book['book_id']} (0 JPG)")
        return 0, 0
    root = book_work_root(book, repo)
    paddle_dir = root / "paddleocr"
    preview_dir = paddle_dir / "preview"
    done = skipped = 0
    print(f"\n=== bbox {book['book_id']} ({len(images)} trang)", flush=True)
    for image in images:
        record_path = paddle_dir / f"{image.stem}-paddleocr.json"
        preview = preview_dir / f"{image.stem}_ocr_res_img.jpg"
        sidecar_json = image.with_name(f"{image.stem}-boundingbox.json")
        sidecar_jpg = image.with_name(f"{image.stem}-boundingbox-preview.jpg")
        if skip_existing and preview.exists():
            skipped += 1
            continue
        if not record_path.is_file():
            print(f"  thiếu OCR {image.name}")
            continue
        record = json.loads(record_path.read_text(encoding="utf-8"))
        draw_overlay(image, record, preview)
        # Không ghi {stem}-boundingbox.* cạnh ảnh — đó là chỗ file lab Kim Hán Nôm.
        done += 1
        if done % 25 == 0:
            print(f"  … {done} trang", flush=True)
    print(f"  xong {book['book_id']}: {done} vẽ, {skipped} skip")
    return done, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description="Vẽ bounding box từ JSON Paddle có sẵn.")
    parser.add_argument("--book", action="append", dest="books")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()
    if not args.books and not args.all:
        raise SystemExit("Chọn --all hoặc --book nom-84")
    repo = repo_root()
    catalog = load_catalog(repo)
    wanted = set(args.books or [])
    books = [b for b in catalog if args.all or b["book_id"] in wanted]
    total_done = total_skip = 0
    for book in books:
        done, skipped = process_book(book, repo, args.skip_existing)
        total_done += done
        total_skip += skipped
    print(f"\nTổng: {total_done} overlay, {total_skip} bỏ qua.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
