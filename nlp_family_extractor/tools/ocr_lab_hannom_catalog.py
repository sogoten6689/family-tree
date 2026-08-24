#!/usr/bin/env python3
"""OCR lab Kim Hán Nôm — lấy bounding box thật từ API, không vẽ từ Paddle.

Ghi cạnh ảnh trang (cùng kiểu Gia phả chí):
  {stem}-ocr-raw.json           — payload API nguyên
  {stem}-boundingbox.json       — wrapper + result_bbox API
  {stem}-boundingbox-preview.jpg — overlay chỉ khi API trả tọa độ

Không ghi đè file lab đã có (Gia phả chí). Nếu API không trả result_bbox:
ghi JSON với mảng rỗng, không bịa tọa độ, không copy overlay Paddle.

Từ repo root:

  nlp_family_extractor/.venv/bin/python nlp_family_extractor/tools/ocr_lab_hannom_catalog.py --book nom-1255
  nlp_family_extractor/.venv/bin/python nlp_family_extractor/tools/ocr_lab_hannom_catalog.py --all --skip-existing
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_TOOLS = Path(__file__).resolve().parent
REPO = _TOOLS.parents[1]
EXTRACTOR = REPO / "nlp_family_extractor"
load_dotenv(EXTRACTOR / ".env")
load_dotenv()
if str(EXTRACTOR) not in sys.path:
    sys.path.insert(0, str(EXTRACTOR))
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from ocr_hannom_catalog import book_work_root, load_catalog  # noqa: E402
from ocr_paddleocr import list_page_images  # noqa: E402
from draw_hannom_bbox import draw_overlay, pages_dir_for  # noqa: E402


def login() -> None:
    from app.hannom.auth import fetch_hannom_token
    from app.hannom.client import apply_runtime_token

    email = os.getenv("HANNOM_EMAIL") or os.getenv("HANNOM_USERNAME")
    password = os.getenv("HANNOM_PASSWORD")
    if not email or not password:
        raise SystemExit("Thiếu HANNOM_EMAIL / HANNOM_PASSWORD trong nlp_family_extractor/.env")
    info = fetch_hannom_token(username=email, password=password)
    token = info.get("token") or info.get("access_token")
    if not token:
        raise SystemExit("Đăng nhập lab xong nhưng không có token.")
    apply_runtime_token(str(token))
    print("Đã đăng nhập Kim Hán Nôm (lab).", flush=True)


def has_lab_file(image: Path) -> bool:
    raw = image.with_name(f"{image.stem}-ocr-raw.json")
    box = image.with_name(f"{image.stem}-boundingbox.json")
    for path in (raw, box):
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        engine = str(payload.get("engine") or "").lower()
        if engine.startswith("kim") or payload.get("result_file_name") or payload.get("ocr_id") is not None:
            return True
    return False


def boxes_from_api(result_bbox: Any) -> list[dict[str, Any]]:
    """Reshape API quads — không suy tọa độ mới."""
    boxes: list[dict[str, Any]] = []
    if not isinstance(result_bbox, list):
        return boxes
    for index, item in enumerate(result_bbox):
        if not isinstance(item, (list, tuple)) or len(item) < 1:
            continue
        quad = item[0]
        if not isinstance(quad, list) or len(quad) < 3:
            continue
        text = ""
        conf = None
        if len(item) >= 2 and isinstance(item[1], (list, tuple)):
            if item[1]:
                text = str(item[1][0])
            if len(item[1]) >= 2:
                try:
                    conf = float(item[1][1])
                except (TypeError, ValueError):
                    conf = None
        xs, ys = [], []
        for point in quad:
            if isinstance(point, (list, tuple)) and len(point) >= 2:
                xs.append(float(point[0]))
                ys.append(float(point[1]))
        if not xs:
            continue
        boxes.append(
            {
                "han": text,
                "confidence": conf,
                "quad": quad,
                "bbox_xyxy": [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))],
                "id": index + 1,
            }
        )
    return boxes


def count_api_boxes(result_bbox: Any) -> int:
    if not isinstance(result_bbox, list):
        return 0
    n = 0
    for item in result_bbox:
        if isinstance(item, (list, tuple)) and item and isinstance(item[0], list) and len(item[0]) >= 3:
            n += 1
    return n


def ocr_page(client: Any, image: Path, *, ocr_id: int, lang_type: int) -> dict[str, Any]:
    from app.hannom.client import run_image_ocr_payload, upload_image

    file_bytes = image.read_bytes()
    temp_name = upload_image(client, file_bytes, image.name)
    payload = run_image_ocr_payload(
        client,
        temp_file_name=temp_name,
        ocr_id=ocr_id,
        lang_type=lang_type,
    )
    return payload


def write_lab_files(
    image: Path,
    api_payload: dict[str, Any],
    *,
    ocr_id: int,
    lang_type: int,
) -> dict[str, Any]:
    stem = image.stem
    raw_path = image.with_name(f"{stem}-ocr-raw.json")
    box_path = image.with_name(f"{stem}-boundingbox.json")
    preview_path = image.with_name(f"{stem}-boundingbox-preview.jpg")

    raw_path.write_text(json.dumps(api_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result_bbox = api_payload.get("result_bbox") or []
    n_boxes = count_api_boxes(result_bbox)
    texts = api_payload.get("result_ocr_text") or []
    note = None
    if not n_boxes:
        note = (
            "API lab không trả tọa độ (result_bbox rỗng). "
            "Không bịa box, không copy overlay Paddle."
        )

    wrapper = {
        "engine": "kimhannom",
        "endpoint": "POST /api/web/clc-sinonom/image-ocr",
        "source": image.name,
        "ocr_id": ocr_id,
        "lang_type": lang_type,
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "result_file_name": api_payload.get("result_file_name"),
        "result_ocr_text": texts,
        "result_bbox": result_bbox,
        "boxes": boxes_from_api(result_bbox),
        "coord_note": (
            "quad = 4 điểm API; bbox_xyxy = min/max của quad (không suy thêm điểm). "
            if n_boxes
            else note
        ),
        "n_api_boxes": n_boxes,
        "n_ocr_lines": len(texts) if isinstance(texts, list) else 0,
    }
    if note:
        wrapper["note"] = note
    box_path.write_text(json.dumps(wrapper, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if n_boxes:
        draw_overlay(image, {"result_bbox": result_bbox}, preview_path)
    elif preview_path.exists():
        # Không giữ overlay Paddle giả nếu lần này API không có box.
        preview_path.unlink()

    return wrapper


def process_book(
    book: dict[str, Any],
    *,
    client: Any,
    ocr_id: int,
    lang_type: int,
    skip_existing: bool,
    limit: int | None,
) -> tuple[int, int, int]:
    if book["book_id"] == "gpc-dang-1928":
        print(f"— skip {book['book_id']} (giữ bbox lab Gia phả chí)", flush=True)
        return 0, 0, 0
    pages_dir = pages_dir_for(book, REPO)
    if pages_dir is None:
        print(f"— skip {book['book_id']} (không có ảnh)", flush=True)
        return 0, 0, 0
    images = list_page_images(pages_dir, None)
    if not images:
        print(f"— skip {book['book_id']} (0 JPG)", flush=True)
        return 0, 0, 0
    done = skipped = empty_bbox = denied = 0
    print(f"\n=== lab OCR {book['book_id']}  {book.get('title_vn')}  ({len(images)} trang)", flush=True)
    for image in images:
        if limit is not None and done >= limit:
            break
        if skip_existing and has_lab_file(image):
            skipped += 1
            continue
        print(f"→ {book['book_id']} {image.name}", flush=True)
        try:
            payload = ocr_page(client, image, ocr_id=ocr_id, lang_type=lang_type)
            wrapper = write_lab_files(image, payload, ocr_id=ocr_id, lang_type=lang_type)
        except Exception as exc:
            print(f"  LỖI API: {exc}", flush=True)
            denied += 1
            if denied >= 3:
                raise SystemExit(
                    "Lab Kim Hán Nôm từ chối truy cập liên tiếp (quota/token). "
                    "Dừng để không spam API. Chạy lại --skip-existing khi hết hạn quota."
                )
            continue
        denied = 0
        n_box = wrapper.get("n_api_boxes") or 0
        n_txt = wrapper.get("n_ocr_lines") or 0
        if n_box == 0:
            empty_bbox += 1
            print(f"  chữ={n_txt}  bbox=0 (API không trả tọa độ)", flush=True)
        else:
            print(f"  chữ={n_txt}  bbox={n_box}", flush=True)
        done += 1
    print(f"  xong {book['book_id']}: {done} OCR lab, {skipped} skip, {empty_bbox} không có bbox", flush=True)
    return done, skipped, empty_bbox


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR lab Kim Hán Nôm — bounding box thật từ API.")
    parser.add_argument("--book", action="append", dest="books")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument(
        "--ocr-id",
        type=int,
        default=1,
        help="1 = dọc (trả bbox trên Gia phả chí thân bài). 3 = có lúc ra chữ nhưng bbox rỗng. Không lấy từ .env (HANNOM_OCR_ID=3 sẽ làm mất tọa độ).",
    )
    parser.add_argument("--lang-type", type=int, default=1, help="1 = Hán.")
    parser.add_argument("--limit", type=int, default=None, help="Tối đa số trang OCR trong lần chạy (thử).")
    args = parser.parse_args()
    if not args.books and not args.all:
        raise SystemExit("Chọn --all hoặc --book nom-1255")

    login()
    import httpx
    from app.hannom.client import get_auth_headers

    catalog = load_catalog(REPO)
    wanted = set(args.books or [])
    books = [b for b in catalog if args.all or b["book_id"] in wanted]
    print(f"ocr_id={args.ocr_id} lang_type={args.lang_type}  (1=Hán dọc, như Gia phả chí thân bài)", flush=True)

    remaining = args.limit
    total_done = total_skip = total_empty = 0
    with httpx.Client(headers=get_auth_headers(), timeout=120.0) as client:
        for book in books:
            done, skipped, empty = process_book(
                book,
                client=client,
                ocr_id=args.ocr_id,
                lang_type=args.lang_type,
                skip_existing=args.skip_existing,
                limit=remaining,
            )
            total_done += done
            total_skip += skipped
            total_empty += empty
            if remaining is not None:
                remaining -= done
                if remaining <= 0:
                    break
    print(
        f"\nTổng lab: {total_done} trang, {total_skip} bỏ qua, {total_empty} không có bbox API.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
