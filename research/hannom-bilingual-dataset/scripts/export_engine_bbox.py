"""Xuất khung chữ của MỘT engine OCR (mặc định Kim Hán Nôm Lab) theo trang để nạp lên web.

Đọc `volumes/<số volume>/pages/<stem>-boundingbox.json` (trường `result_bbox` — các
mục `[quad 4 điểm, [chữ, độ tin cậy]]`, đúng file ocr_lab_hannom_catalog.py đã ghi),
sắp theo thứ tự đọc dọc (cột phải → trái, trong cột trên → dưới) bằng cùng hàm
`ordered_boxes` với export_page_bbox.py, rồi ghi 1 file JSON:

  {"schema": 1, "engine": "kim_hannom_lab",
   "books": {doc_id: {page_number: {"image_size": [w, h] | null,
                                    "boxes": [{order, bbox_xyxy, han, confidence}]}}}}

Quy ước khớp (giống export_page_bbox.py): doc_id = "nom-<số volume>"; page_number
đánh 1.. theo thứ tự `pages` trong record corpus (KHÔNG phải số trong tên file —
record có thể xáo/lấy mẫu trang), stem lấy từ `l0_image` của trang.

Kiểm tra kích thước ảnh `volumes/<vol>/pages/<stem>.jpg`: khung vượt ảnh → BỎ trang
và in cảnh báo. Trang không có file khung / không có khung → bỏ im lặng (đếm riêng).

Chỉ ĐỌC file local, không gọi API, không sửa record. Nạp lên DB:
nlp_family_extractor/tools/load_engine_bbox.py.

  python3 scripts/export_engine_bbox.py --volumes-dir <.../nomfoundation/volumes> \\
      --records-dir <hannom-bilingual-dataset/data> --out /tmp/kim_bbox.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_page_bbox import fits_image, ordered_boxes  # noqa: E402

ENGINE_KIM = "kim_hannom_lab"
BBOX_SUFFIX = "-boundingbox.json"


def boxes_from_result_bbox(path: Path) -> list[tuple[Any, str, float | None]] | None:
    """Đọc `result_bbox` → [(quad, chữ, độ tin cậy)]; mục hỏng bị bỏ. None nếu file không đọc được."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    raw = data.get("result_bbox") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return None
    out: list[tuple[Any, str, float | None]] = []
    for entry in raw:
        try:
            poly, (text, score) = entry
            if not poly or not all(len(p) >= 2 for p in poly):
                continue
            out.append((poly, str(text), None if score is None else float(score)))
        except (TypeError, ValueError):
            continue
    return out


def _image_size(pages_dir: Path, stem: str) -> tuple[int, int] | None:
    try:
        from PIL import Image
    except ImportError:
        return None
    for ext in (".jpg", ".jpeg", ".png", ".JPG", ".PNG"):
        p = pages_dir / f"{stem}{ext}"
        if p.is_file():
            with Image.open(p) as img:
                return img.size
    return None


def export_book(record: dict[str, Any], pages_dir: Path) -> tuple[dict[str, Any], list[str], dict[str, int]]:
    """Trả về (pages, warnings, stats) cho 1 bộ."""
    pages: dict[str, Any] = {}
    warnings: list[str] = []
    stats = {"record_pages": 0, "no_file": 0, "no_boxes": 0, "outside_image": 0, "no_size": 0, "boxes": 0}
    for number, page in enumerate(record.get("pages") or [], start=1):
        stats["record_pages"] += 1
        stem = Path(page.get("l0_image") or "").stem
        if not stem:
            stats["no_file"] += 1
            continue
        path = pages_dir / f"{stem}{BBOX_SUFFIX}"
        raw = boxes_from_result_bbox(path) if path.is_file() else None
        if raw is None:
            stats["no_file"] += 1
            continue
        boxes = ordered_boxes(raw)
        if not boxes:
            stats["no_boxes"] += 1
            continue
        size = _image_size(pages_dir, stem)
        if size is None:
            stats["no_size"] += 1
            warnings.append(f"trang {number} ({stem}): không đọc được kích thước ảnh")
        elif not fits_image(boxes, size):
            stats["outside_image"] += 1
            warnings.append(f"trang {number} ({stem}): khung vượt ảnh {size} — BỎ")
            continue
        pages[str(number)] = {"image_size": list(size) if size else None, "boxes": boxes}
        stats["boxes"] += len(boxes)
    return pages, warnings, stats


def export_volumes(volumes_dir: Path, records_dir: Path, *, engine: str, docs: list[str] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"schema": 1, "engine": engine, "books": {}}
    for path in sorted(records_dir.glob("track*/*.json")):
        doc_id = path.stem
        if not doc_id.startswith("nom-") or (docs and doc_id not in docs):
            continue
        pages_dir = volumes_dir / doc_id[len("nom-") :] / "pages"
        if not pages_dir.is_dir():
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        pages, warnings, stats = export_book(record, pages_dir)
        for w in warnings:
            print(f"[{doc_id}] {w}", file=sys.stderr)
        if pages:
            out["books"][doc_id] = pages
        print(
            f"{doc_id}: {len(pages)}/{stats['record_pages']} trang có khung ({stats['boxes']} khung); "
            f"thiếu file {stats['no_file']}, rỗng {stats['no_boxes']}, ngoài ảnh {stats['outside_image']}, "
            f"không rõ cỡ ảnh {stats['no_size']}"
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--volumes-dir", type=Path, required=True, help=".../nomfoundation/volumes")
    ap.add_argument("--records-dir", type=Path, required=True, help="thư mục data/ của repo hannom-bilingual-dataset (chứa track*/<doc_id>.json)")
    ap.add_argument("--engine", default=ENGINE_KIM)
    ap.add_argument("--doc", action="append", default=[], help="chỉ các doc_id này (mặc định: tất cả nom-*)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    out = export_volumes(args.volumes_dir, args.records_dir, engine=args.engine, docs=args.doc or None)
    args.out.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    total_pages = sum(len(p) for p in out["books"].values())
    print(f"→ {args.out} ({len(out['books'])} bộ, {total_pages} trang)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
