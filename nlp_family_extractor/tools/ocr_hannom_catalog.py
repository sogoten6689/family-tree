#!/usr/bin/env python3
"""OCR every Hán-Nôm book in books_catalog.json with PP-OCRv6.

From repo root (paddle venv):

  .venv-paddleocr/bin/python nlp_family_extractor/tools/ocr_hannom_catalog.py --book nom-1255
  .venv-paddleocr/bin/python nlp_family_extractor/tools/ocr_hannom_catalog.py --all --skip-existing
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

from ocr_paddleocr import (  # noqa: E402
    _lines_from_mapping,
    build_page_record,
    list_page_images,
    load_ocr,
    ocr_one,
    write_outputs,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_catalog(repo: Path) -> list[dict[str, Any]]:
    path = repo / "data/hannom/books_catalog.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("books") or [])


def render_pdf(pdf_path: Path, pages_dir: Path) -> list[Path]:
    import pypdfium2 as pdfium

    pages_dir.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(pdf_path))
    written: list[Path] = []
    try:
        for index in range(len(doc)):
            dest = pages_dir / f"{index + 1:03d}.jpg"
            if dest.exists():
                written.append(dest)
                continue
            page = doc[index]
            bitmap = page.render(scale=2)
            bitmap.to_pil().convert("RGB").save(dest, quality=88)
            written.append(dest)
    finally:
        doc.close()
    return written


def book_work_root(book: dict[str, Any], repo: Path) -> Path:
    """Per-book folder for paddleocr/ and dich/. PDFs must not share 13_8_2026/."""
    if book.get("source") == "tong_pho_pdf":
        return repo / "data/du_lieu_han_nom_moi/13_8_2026" / book["book_id"]
    rel = (book.get("paths") or {}).get("root") or (book.get("paths") or {}).get("pages")
    if not rel:
        raise ValueError(f"No root for {book.get('book_id')}")
    path = repo / rel
    return path.parent if path.is_file() else path


def page_dir_for(book: dict[str, Any], repo: Path) -> Path | None:
    paths = book.get("paths") or {}
    if book.get("source") == "tong_pho_pdf":
        pdf_rel = paths.get("pdf") or paths.get("pages")
        if not pdf_rel:
            return None
        pdf_path = repo / pdf_rel
        if not pdf_path.is_file():
            return None
        out = repo / "data/du_lieu_han_nom_moi/13_8_2026" / book["book_id"] / "pages"
        print(f"  render PDF → {out.relative_to(repo)}", flush=True)
        render_pdf(pdf_path, out)
        return out
    rel = paths.get("pages") or paths.get("root")
    if not rel:
        return None
    path = repo / rel
    return path if path.exists() else None


def ocr_book(book: dict[str, Any], *, repo: Path, ocr: Any, engine: str, skip_existing: bool, no_preview: bool) -> tuple[int, int]:
    pages_dir = page_dir_for(book, repo)
    if pages_dir is None:
        print(f"— skip {book['book_id']} (không có ảnh/PDF)")
        return 0, 0
    images = list_page_images(pages_dir, None)
    if not images:
        print(f"— skip {book['book_id']} (0 JPG số)")
        return 0, 0
    root = book_work_root(book, repo)
    output_dir = root / "paddleocr"
    print(f"\n=== {book['book_id']}  {book.get('title_vn')}  ({len(images)} trang) → {output_dir.relative_to(repo)}", flush=True)
    done = skipped = 0
    for image in images:
        json_path = output_dir / f"{image.stem}-paddleocr.json"
        if skip_existing and json_path.exists():
            skipped += 1
            continue
        print(f"→ {book['book_id']} {image.name}", flush=True)
        mapping, elapsed, paddle_result = ocr_one(ocr, image)
        lines = _lines_from_mapping(mapping)
        record = build_page_record(
            source=image,
            model=f"PP-OCRv6_medium+{engine}",
            elapsed_s=elapsed,
            mapping=mapping,
            lines=lines,
        )
        record["book_id"] = book["book_id"]
        write_outputs(
            output_dir=output_dir,
            image=image,
            record=record,
            paddle_result=paddle_result,
            save_preview=not no_preview,
        )
        print(f"  {record['line_count']} dòng, mean={record['mean_score']}, {elapsed:.1f}s", flush=True)
        done += 1
    print(f"  xong {book['book_id']}: {done} OCR, {skipped} skip")
    return done, skipped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OCR catalog Hán-Nôm bằng PP-OCRv6.")
    parser.add_argument("--book", action="append", dest="books", help="book_id; lặp được. Mặc định --all.")
    parser.add_argument("--all", action="store_true", help="Mọi cuốn có ảnh hoặc PDF.")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--no-preview", action="store_true")
    parser.add_argument("--engine", default="onnxruntime")
    parser.add_argument("--model", default="medium", choices=("tiny", "small", "medium"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = repo_root()
    catalog = load_catalog(repo)
    wanted = set(args.books or [])
    if not wanted and not args.all:
        raise SystemExit("Chọn --all hoặc --book nom-1255")
    books = [b for b in catalog if args.all or b["book_id"] in wanted]
    if wanted:
        missing = wanted - {b["book_id"] for b in books}
        if missing:
            raise SystemExit(f"Không có book_id: {sorted(missing)}")
    print(f"Load PP-OCRv6 ({args.engine}) cho {len(books)} cuốn…")
    ocr, engine = load_ocr(args.model, args.engine)
    print(f"Engine: {engine}")
    total_done = total_skip = 0
    for book in books:
        done, skipped = ocr_book(
            book,
            repo=repo,
            ocr=ocr,
            engine=engine,
            skip_existing=args.skip_existing,
            no_preview=args.no_preview,
        )
        total_done += done
        total_skip += skipped
    print(f"\nTổng: {total_done} trang OCR, {total_skip} bỏ qua.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
