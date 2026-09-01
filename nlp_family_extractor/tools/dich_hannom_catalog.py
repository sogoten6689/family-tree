#!/usr/bin/env python3
"""Phiên âm Hán-Việt từ OCR (API lab). Mặc định không gọi Gemini.

  python nlp_family_extractor/tools/dich_hannom_catalog.py --book nom-1255
  python nlp_family_extractor/tools/dich_hannom_catalog.py --all --skip-existing
  python nlp_family_extractor/tools/dich_hannom_catalog.py --book nom-1255 --gemini  # opt-in

  # L2 pipeline mix_translate: đọc mix/*.han.txt, ghi 01_interim/.../l2/ (không phải dich/ của sách),
  # luôn dùng lab phiên âm (bỏ qua --gemini) — xem docs/planning/mix_translate_family_tree_plan.md
  python nlp_family_extractor/tools/dich_hannom_catalog.py --book nguyen-ke-han-nom \
      --in-dir data/01_interim/huong_nguyen_ke/mix \
      --out data/01_interim/huong_nguyen_ke/l2
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
    path = REPO / "data/00_raw/hannom/books_catalog.json"
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
    """Phiên âm Hán-Việt qua API lab."""
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


def dich_page(
    client: Any, model: str | None, book: dict[str, Any], ocr_txt: Path, dest: Path, *, plain: bool = False
) -> None:
    ocr_text = ocr_txt.read_text(encoding="utf-8").strip()
    if not ocr_text:
        if plain:
            dest.write_text("", encoding="utf-8")
        else:
            dest.write_text("# OCR trống\n\nKhông có chữ Paddle để dịch.\n", encoding="utf-8")
        return
    if plain:
        # L2 mix_translate: chỉ lab phiên âm, không Gemini, không markdown — khớp
        # data/01_interim/.../l2/{n}.transcription.txt trong mix_translate_family_tree_plan.md
        phien = lab_transliterate(ocr_text)
        dest.write_text((phien or "").strip() + "\n", encoding="utf-8")
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
    body = ["Engine: phiên âm lab Kim Hán Nôm (không dùng Gemini).\n"]
    body.append("## Phiên âm\n")
    body.append(phien or "(lab không phiên âm được)")
    body.append("\n## Dịch nghĩa\n")
    body.append("Bỏ qua — chỉ phiên âm lab.\n")
    dest.write_text(header + "\n".join(body), encoding="utf-8")


def book_work_root(book: dict[str, Any]) -> Path:
    if book.get("source") == "tong_pho_pdf":
        return REPO / "data/00_raw/du_lieu_han_nom_moi/13_8_2026" / book["book_id"]
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
    parser.add_argument(
        "--gemini",
        action="store_true",
        help="Opt-in dịch nghĩa Gemini. Mặc định chỉ phiên âm lab.",
    )
    parser.add_argument("--sleep", type=float, default=0.4, help="Nghỉ giữa trang (giây).")
    parser.add_argument(
        "--in-dir",
        type=Path,
        default=None,
        help="Đọc *.han.txt từ đây (vd: mix/) thay vì <book>/paddleocr/*-paddleocr.txt.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "Ghi *.transcription.txt vào đây (vd: 01_interim/.../l2/) thay vì <book>/dich/*-dich.md. "
            "Khi dùng --out, luôn phiên âm lab (bỏ qua --gemini) — dùng cho pipeline mix_translate."
        ),
    )
    args = parser.parse_args()
    if not args.books and not args.all:
        raise SystemExit("Chọn --all hoặc --book nom-1255")

    catalog = load_catalog()
    wanted = set(args.books or [])
    books = [b for b in catalog if args.all or b["book_id"] in wanted]
    client, model = (None, None)
    if args.out:
        print("Dest tuỳ chỉnh (--out) — chỉ phiên âm lab, bỏ qua --gemini nếu có.")
    elif args.gemini:
        client, model = gemini_client()
        if client is None:
            print("Đã xin --gemini nhưng không có GOOGLE_API_KEY — phiên âm lab.")
        else:
            print(f"Gemini model: {model}")
    else:
        print("Bỏ qua Gemini — chỉ phiên âm lab Kim Hán Nôm.")
    done = skipped = 0
    for book in books:
        if args.in_dir:
            src_dir = args.in_dir if args.in_dir.is_absolute() else REPO / args.in_dir
            if not src_dir.is_dir():
                print(f"— skip {book['book_id']} ({src_dir} không tồn tại)")
                continue
            pattern = "*.han.txt"
        else:
            src_dir = paddle_outputs(book)
            if src_dir is None:
                print(f"— skip {book['book_id']} (chưa có paddleocr/)")
                continue
            pattern = "*-paddleocr.txt"

        if args.out:
            dich_dir = args.out if args.out.is_absolute() else REPO / args.out
        else:
            dich_dir = book_work_root(book) / "dich"
            # Không đè bản dịch tay Gia phả chí (nằm cạnh ảnh, không trong dich/).
            if book["book_id"] == "gpc-dang-1928":
                print(f"— skip {book['book_id']} (giữ *-dich.md tay)")
                continue

        files = sorted(src_dir.glob(pattern), key=lambda p: p.stem)
        print(f"\n=== dịch {book['book_id']} ({len(files)} trang) → {dich_dir}")
        dich_dir.mkdir(parents=True, exist_ok=True)
        for txt in files:
            stem = txt.name.split(".")[0] if args.in_dir else txt.stem.replace("-paddleocr", "")
            suffix = ".transcription.txt" if args.out else "-dich.md"
            dest = dich_dir / f"{stem}{suffix}"
            if args.skip_existing and dest.exists():
                skipped += 1
                continue
            print(f"→ {book['book_id']} {stem}")
            try:
                dich_page(client, model, book, txt, dest, plain=bool(args.out))
                done += 1
            except Exception as exc:
                print(f"  LỖI: {exc}")
            time.sleep(max(0.0, args.sleep))
    print(f"\nTổng: {done} trang dịch, {skipped} bỏ qua.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
