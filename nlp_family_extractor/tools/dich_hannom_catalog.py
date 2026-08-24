#!/usr/bin/env python3
"""Dịch nghĩa + Hán-Việt từ OCR Paddle (Gemini). Không ghi đè bản dịch tay đã có.

  python nlp_family_extractor/tools/dich_hannom_catalog.py --book nom-1255
  python nlp_family_extractor/tools/dich_hannom_catalog.py --all --skip-existing
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_TOOLS = Path(__file__).resolve().parent
REPO = _TOOLS.parents[1]
load_dotenv(REPO / "nlp_family_extractor/.env")
load_dotenv()


PROMPT = """Bạn dịch một trang gia phả / văn bản Hán (OCR máy, có thể lệch chữ).

Nhan đề cuốn: {title_han} — {title_vn}
Trang: {page}

Chữ OCR (Paddle):
{ocr_text}

Yêu cầu:
1. Phiên âm Hán-Việt (theo dòng, giữ thứ tự).
2. Dịch nghĩa tiếng Việt hiện đại, giữ nguyên tên người / địa danh / húy nhật.
3. Không bịa thêm quan hệ hoặc nhân vật không có trong OCR.
4. Nếu OCR rác / không đọc được, ghi rõ «OCR yếu» và chỉ dịch phần chắc.

Output markdown:
## Phiên âm
...
## Dịch nghĩa
...
## Ghi chú
...
"""


def load_catalog() -> list[dict[str, Any]]:
    path = REPO / "data/hannom/books_catalog.json"
    return list(json.loads(path.read_text(encoding="utf-8")).get("books") or [])


def gemini_client():
    from google import genai

    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        return None, None
    model = os.getenv("GEMINI_MODEL_NAME", "models/gemini-2.5-flash")
    return genai.Client(api_key=key), model


_LAB_READY = False
_GEMINI_OK = True


def lab_transliterate(text: str) -> str | None:
    """Phiên âm Hán-Việt qua API lab (khi Gemini hỏng)."""
    global _LAB_READY
    extractor = REPO / "nlp_family_extractor"
    if str(extractor) not in sys.path:
        sys.path.insert(0, str(extractor))
    try:
        from app.hannom.auth import fetch_hannom_token
        from app.hannom.client import apply_runtime_token, get_auth_headers, run_transliteration
        import httpx
    except Exception:
        return None
    if not _LAB_READY:
        email = os.getenv("HANNOM_EMAIL") or os.getenv("HANNOM_USERNAME")
        password = os.getenv("HANNOM_PASSWORD")
        if not email or not password:
            return None
        token_info = fetch_hannom_token(username=email, password=password)
        token = token_info.get("token") or token_info.get("access_token")
        if not token:
            return None
        apply_runtime_token(str(token))
        _LAB_READY = True
    headers = get_auth_headers()
    with httpx.Client(headers=headers, timeout=120.0) as client:
        lines = run_transliteration(client, text=text)
    return "\n".join(lines)


def dich_page(client: Any, model: str | None, book: dict[str, Any], ocr_txt: Path, dest: Path) -> None:
    ocr_text = ocr_txt.read_text(encoding="utf-8").strip()
    if not ocr_text:
        dest.write_text("# OCR trống\n\nKhông có chữ Paddle để dịch.\n", encoding="utf-8")
        return
    page = ocr_txt.stem.replace("-paddleocr", "")
    header = (
        f"# {book['book_id']} — trang {page}\n\n"
        f"Nguồn OCR: `{ocr_txt.relative_to(REPO)}`\n"
    )
    global _GEMINI_OK
    if _GEMINI_OK and client and model:
        prompt = PROMPT.format(
            title_han=book.get("title_han") or "",
            title_vn=book.get("title_vn") or "",
            page=page,
            ocr_text=ocr_text[:8000],
        )
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            text = (response.text or "").strip()
            if text:
                dest.write_text(header + f"Model dịch: `{model}`\n\n" + text + "\n", encoding="utf-8")
                return
        except Exception as exc:
            _GEMINI_OK = False
            print(f"  Gemini lỗi ({exc.__class__.__name__}) — tắt Gemini, dùng lab phiên âm")
    phien = lab_transliterate(ocr_text)
    body = ["Không dùng Gemini (key lỗi/401). Phiên âm lab Kim Hán Nôm trên chữ Paddle.\n"]
    body.append("## Phiên âm\n")
    body.append(phien or "(lab không phiên âm được)")
    body.append("\n## Dịch nghĩa\n")
    body.append("Chưa có — cần Gemini hoặc dịch tay.\n")
    dest.write_text(header + "\n".join(body), encoding="utf-8")


def book_work_root(book: dict[str, Any]) -> Path:
    if book.get("source") == "tong_pho_pdf":
        return REPO / "data/du_lieu_han_nom_moi/13_8_2026" / book["book_id"]
    rel = (book.get("paths") or {}).get("root")
    if not rel:
        raise ValueError(f"No root for {book.get('book_id')}")
    path = REPO / rel
    return path.parent if path.is_file() else path


def paddle_outputs(book: dict[str, Any]) -> Path | None:
    folder = book_work_root(book) / "paddleocr"
    return folder if folder.is_dir() else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--book", action="append", dest="books")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.4, help="Nghỉ giữa trang (giây).")
    args = parser.parse_args()
    if not args.books and not args.all:
        raise SystemExit("Chọn --all hoặc --book nom-1255")

    catalog = load_catalog()
    wanted = set(args.books or [])
    books = [b for b in catalog if args.all or b["book_id"] in wanted]
    client, model = gemini_client()
    if client is None:
        print("Gemini không có key — sẽ phiên âm bằng API lab.")
    else:
        print(f"Gemini model: {model} (nếu 401 sẽ fallback lab phiên âm)")
    done = skipped = 0
    for book in books:
        paddle_dir = paddle_outputs(book)
        if paddle_dir is None:
            print(f"— skip {book['book_id']} (chưa có paddleocr/)")
            continue
        dich_dir = book_work_root(book) / "dich"
        # Không đè bản dịch tay Gia phả chí (nằm cạnh ảnh, không trong dich/).
        if book["book_id"] == "gpc-dang-1928":
            print(f"— skip {book['book_id']} (giữ *-dich.md tay)")
            continue
        files = sorted(paddle_dir.glob("*-paddleocr.txt"), key=lambda p: p.stem)
        print(f"\n=== dịch {book['book_id']} ({len(files)} trang) → {dich_dir.relative_to(REPO)}")
        dich_dir.mkdir(parents=True, exist_ok=True)
        for txt in files:
            stem = txt.stem.replace("-paddleocr", "")
            dest = dich_dir / f"{stem}-dich.md"
            if args.skip_existing and dest.exists():
                skipped += 1
                continue
            print(f"→ {book['book_id']} {stem}")
            try:
                dich_page(client, model, book, txt, dest)
                done += 1
            except Exception as exc:
                print(f"  LỖI: {exc}")
            time.sleep(max(0.0, args.sleep))
    print(f"\nTổng: {done} trang dịch, {skipped} bỏ qua.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
