#!/usr/bin/env python3
"""Dịch nghĩa Hán → Việt bằng Qwen (OpenAI-compatible API).

Không xin key thầy: tự tạo DASHSCOPE_API_KEY (Alibaba Cloud Model Studio).
Máy Intel 32GB không chạy được Qwen3.6-27B local tuần này.

  # 1. Lấy key: https://modelstudio.console.alibabacloud.com  (region Singapore / intl)
  # 2. Thêm vào nlp_family_extractor/.env:
  #      DASHSCOPE_API_KEY=sk-...
  #      QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
  #      QWEN_MODEL=qwen3.6-27b
  # 3. Chạy (venv có httpx + python-dotenv):

  python nlp_family_extractor/tools/dich_qwen.py --book nguyen-ke-han-nom --pages 9

  # L3 pipeline mix_translate: input = L1* (mix) + L2 (phiên âm lab), ghi 01_interim/.../l3/
  # (không phải dich/ của sách) — xem docs/planning/mix_translate_family_tree_plan.md
  python nlp_family_extractor/tools/dich_qwen.py --book nguyen-ke-han-nom --pages 0,2 \
      --in-dir data/01_interim/huong_nguyen_ke/mix \
      --l2-dir data/01_interim/huong_nguyen_ke/l2 \
      --out data/01_interim/huong_nguyen_ke/l3
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

_TOOLS = Path(__file__).resolve().parent
REPO = _TOOLS.parents[1]
load_dotenv(REPO / "nlp_family_extractor/.env")
load_dotenv()

PROMPT = """Bạn là người dịch văn bản Hán hành chính Việt Nam (khế ước, kế ước, gia phả).
Dịch nghĩa tiếng Việt hiện đại. Giữ nguyên húy, địa danh, niên hiệu, số đo điền thổ.
Không bịa nhân vật hoặc quan hệ không có trong chữ.
Nếu OCR lệch, ghi trong mục Ghi chú; phần không chắc thì đánh dấu [không chắc].

Nhan đề: {title_han} — {title_vn}
Trang OCR: {page}

Chữ Hán (Paddle OCR, có thể sai):
{ocr_text}
{transcription_block}
Trả về markdown:
## Dịch nghĩa
...
## Ghi chú
...
"""

TRANSCRIPTION_BLOCK = """
Phiên âm Hán-Việt (lab Kim Hán Nôm — dùng để đối chiếu, không phải nguồn chính):
{transcription_text}
"""


def load_catalog() -> list[dict]:
    path = REPO / "data/00_raw/hannom/books_catalog.json"
    return list(json.loads(path.read_text(encoding="utf-8")).get("books") or [])


def book_root(book: dict) -> Path:
    if book.get("source") == "tong_pho_pdf":
        return REPO / "data/00_raw/du_lieu_han_nom_moi/13_8_2026" / book["book_id"]
    rel = (book.get("paths") or {}).get("root") or ""
    path = REPO / rel
    return path.parent if path.is_file() else path


def qwen_chat(
    ocr_text: str, *, title_han: str, title_vn: str, page: str, transcription_text: str = ""
) -> str:
    api_key = (os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY") or "").strip()
    if not api_key:
        raise SystemExit(
            "Thiếu DASHSCOPE_API_KEY (hoặc QWEN_API_KEY) trong nlp_family_extractor/.env.\n"
            "Tự tạo: Alibaba Cloud Model Studio → API Key.\n"
            "VN/quốc tế: QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1\n"
            "Model mặc định: qwen3.6-27b (bản T đã thử dịch nghĩa — không phải 37B; series 3.6 không có 37B)."
        )
    base = (
        os.getenv("QWEN_BASE_URL")
        or os.getenv("DASHSCOPE_BASE_URL")
        or "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    ).rstrip("/")
    model = os.getenv("QWEN_MODEL") or os.getenv("DASHSCOPE_MODEL") or "qwen3.6-27b"
    url = f"{base}/chat/completions"
    transcription_block = (
        TRANSCRIPTION_BLOCK.format(transcription_text=transcription_text[:6000]) if transcription_text else ""
    )
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": PROMPT.format(
                    title_han=title_han,
                    title_vn=title_vn,
                    page=page,
                    ocr_text=ocr_text[:12000],
                    transcription_block=transcription_block,
                ),
            }
        ],
        "temperature": 0.2,
        "extra_body": {"enable_thinking": False},
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=180.0) as client:
        response = client.post(url, headers=headers, json=body)
    if response.status_code >= 400:
        raise SystemExit(f"Qwen HTTP {response.status_code}: {response.text[:800]}")
    data = response.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise SystemExit(f"Response không có choices[0].message.content: {repr(data)[:500]}") from exc
    if not (text or "").strip():
        raise SystemExit("Qwen trả nội dung rỗng.")
    return str(text).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Dịch nghĩa 1+ trang Paddle bằng Qwen API.")
    parser.add_argument("--book", required=True)
    parser.add_argument("--pages", default="9", help="Số trang, cách nhau bởi dấu phẩy. Mặc định 9.")
    parser.add_argument(
        "--in-dir",
        type=Path,
        default=None,
        help="Đọc {stem}.han.txt từ đây (vd: mix/) thay vì <book>/paddleocr/{stem}-paddleocr.txt.",
    )
    parser.add_argument(
        "--l2-dir",
        type=Path,
        default=None,
        help="Đọc {stem}.transcription.txt từ đây (vd: l2/) để đưa phiên âm lab vào prompt (L1*+L2). Tuỳ chọn.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Ghi {stem}.modern_vn.md vào đây (vd: 01_interim/.../l3/) thay vì <book>/dich/{stem}-qwen.md.",
    )
    args = parser.parse_args()
    catalog = {b["book_id"]: b for b in load_catalog()}
    book = catalog.get(args.book)
    if book is None:
        raise SystemExit(f"Không có book_id {args.book}")
    root = book_root(book)
    src_dir = (args.in_dir if args.in_dir.is_absolute() else REPO / args.in_dir) if args.in_dir else root / "paddleocr"
    l2_dir = (args.l2_dir if args.l2_dir.is_absolute() else REPO / args.l2_dir) if args.l2_dir else None
    out_dir = (args.out if args.out.is_absolute() else REPO / args.out) if args.out else root / "dich"
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = [p.strip() for p in args.pages.split(",") if p.strip()]
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    model = os.getenv("QWEN_MODEL") or os.getenv("DASHSCOPE_MODEL") or "qwen3.6-27b"
    for stem in pages:
        src = src_dir / (f"{stem}.han.txt" if args.in_dir else f"{stem}-paddleocr.txt")
        if not src.is_file():
            print(f"— thiếu {src}")
            continue
        ocr = src.read_text(encoding="utf-8").strip()
        transcription = ""
        if l2_dir is not None:
            l2_src = l2_dir / f"{stem}.transcription.txt"
            if l2_src.is_file():
                transcription = l2_src.read_text(encoding="utf-8").strip()
            else:
                print(f"  (không thấy {l2_src} — dịch không kèm phiên âm lab)")
        print(f"→ Qwen {args.book} p.{stem} ({len(ocr)} ký tự Hán" + (f", {len(transcription)} ký tự phiên âm)" if transcription else ")"))
        body = qwen_chat(
            ocr,
            title_han=str(book.get("title_han") or ""),
            title_vn=str(book.get("title_vn") or ""),
            page=stem,
            transcription_text=transcription,
        )
        dest = out_dir / (f"{stem}.modern_vn.md" if args.out else f"{stem}-qwen.md")
        dest.write_text(
            f"# {args.book} — trang {stem} — Qwen dịch nghĩa\n\n"
            f"- model: `{model}`\n"
            f"- nguồn Hán: `{src}`\n"
            + (f"- nguồn phiên âm (L2): `{l2_dir / f'{stem}.transcription.txt'}`\n" if transcription else "")
            + f"- lúc: `{now}`\n"
            f"- không phải Gemini; không phải lab phiên âm\n\n"
            f"{body}\n",
            encoding="utf-8",
        )
        print(f"  wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
