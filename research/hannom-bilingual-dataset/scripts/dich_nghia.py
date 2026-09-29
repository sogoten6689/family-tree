#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dịch nghĩa (L3) TỪNG DÒNG cho các trang đã có `voted_text` + `l2_phien_am`.

Dùng Gemini (GOOGLE_API_KEY có sẵn trong family-tree/nlp_family_extractor/.env
— TỐN QUOTA THẬT mỗi trang, khác với phiên âm dùng API lab miễn phí).

QUAN TRỌNG — khác bản trước: dịch TỪNG DÒNG, giữ đúng số dòng như bản Hán gốc,
KHÔNG dịch gộp cả trang thành 1 đoạn văn liền mạch. Lý do: phiên âm (L2) vốn
đã khớp dòng-với-dòng 100% với chữ Hán (vì phiên âm không đảo trật tự chữ) —
XÁC NHẬN qua đối chiếu thật trên nom-1255 trang 1 (8/8 dòng khớp đúng thứ tự).
Nếu dịch nghĩa cũng giữ đúng cấu trúc dòng, `pairs[]` (ghép Hán↔Việt) được
tạo ra TỰ ĐỘNG, không cần UI ghép cặp thủ công nào cả.

Đánh đổi: câu dịch từng dòng đôi khi kém tự nhiên hơn dịch cả đoạn (1 câu Hán
cổ có thể tràn qua nhiều dòng/cột) — chấp nhận vì mục đích chính là có pairs
đúng cấu trúc cho dữ liệu training, không phải văn bản đọc mượt nhất.

Dùng:
  python3 scripts/dich_nghia.py <doc_id> [--pages 001,002] [--force]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ocr_adapters.base import call_with_timeout  # noqa: E402
from _repo_paths import DATA_REPO_ROOT, FAMILY_TREE  # noqa: E402

PROMPT = """Bạn dịch nghĩa TỪNG DÒNG của 1 trang gia phả chữ Hán sang tiếng Việt hiện đại.

Dưới đây là {n} dòng chữ Hán (đánh số 1..{n}), kèm phiên âm Hán-Việt để tham khảo:

{lines_block}

Yêu cầu:
1. Dịch nghĩa TỪNG DÒNG một, GIỮ NGUYÊN đúng {n} dòng — không gộp 2 dòng thành 1,
   không tách 1 dòng thành 2. Nếu 1 câu tràn qua nhiều dòng vật lý, dịch phần ý
   thuộc đúng dòng đó, chấp nhận câu chưa trọn nghĩa hơn là phá vỡ số dòng.
2. Không bịa thêm quan hệ/nhân vật không có trong bản gốc.
3. Giữ nguyên tên người, địa danh, húy nhật.
4. Nếu 1 dòng không chắc nghĩa, dịch trong ngoặc kèm "(không chắc)".

Trả về ĐÚNG định dạng JSON (mảng {n} phần tử theo đúng thứ tự dòng), không thêm
markdown code fence, không thêm giải thích:
[{{"line": 1, "viet": "..."}}, {{"line": 2, "viet": "..."}}, ...]
"""


def find_record_path(doc_id: str) -> Path:
    for track_dir in ("track1_hannom_only", "track2_bilingual", "track3_viet_only"):
        p = DATA_REPO_ROOT / "data" / track_dir / f"{doc_id}.json"
        if p.is_file():
            return p
    raise SystemExit(f"Không tìm thấy record cho doc_id={doc_id}")


def gemini_client():
    from dotenv import load_dotenv
    load_dotenv(FAMILY_TREE / "nlp_family_extractor/.env")
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("Thiếu GOOGLE_API_KEY trong family-tree/nlp_family_extractor/.env")
    from google import genai
    model = os.getenv("GEMINI_MODEL_NAME", "models/gemini-2.5-flash")
    return genai.Client(api_key=key), model


def parse_json_array(text: str) -> list[dict] | None:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    return None


def translate_page(client, model, han_lines: list[str], phien_lines: list[str]) -> list[str] | None:
    n = len(han_lines)
    lines_block = "\n".join(
        f"{i + 1}. Hán: {h}\n   Phiên âm: {p if i < len(phien_lines) else '(không có)'}"
        for i, (h, p) in enumerate(zip(han_lines, phien_lines + [""] * (n - len(phien_lines))))
    )
    prompt = PROMPT.format(n=n, lines_block=lines_block)
    resp = call_with_timeout(client.models.generate_content, model=model, contents=prompt, timeout_s=90.0)
    data = parse_json_array((resp.text or "").strip())
    if data is None or len(data) != n:
        return None
    by_line = {int(item.get("line", 0)): str(item.get("viet", "")) for item in data}
    return [by_line.get(i + 1, "") for i in range(n)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("doc_id")
    ap.add_argument("--pages", default=None, help="vd 001,002 — mặc định tất cả trang có voted_text")
    ap.add_argument("--force", action="store_true", help="dịch lại cả trang đã có l3_dich_nghia (bản cũ, dạng đoạn văn)")
    args = ap.parse_args()

    client, model = gemini_client()

    record_path = find_record_path(args.doc_id)
    record = json.loads(record_path.read_text(encoding="utf-8"))

    # XÁC NHẬN 2026-09-12: đã THỬ song song nhiều trang cho vote_ocr.py (run.py)
    # — CHẬM HƠN 3 lần vì nhiều trang cùng gọi CHUNG 1 nhà cung cấp (ở đây là
    # Gemini cho mọi trang) bị chính server giới hạn tốc độ. Không song song
    # hoá theo trang ở đây, tránh lặp lại bài học đó.
    wanted = set(p.strip() for p in args.pages.split(",")) if args.pages else None
    updated = 0
    for page in record.get("pages", []):
        if wanted and page["page_id"] not in wanted:
            continue
        voted_text = (page.get("l1_ocr") or {}).get("voted_text")
        if not voted_text:
            continue
        if page.get("pairs") and not args.force:
            print(f"  trang {page['page_id']}: đã có pairs, bỏ qua (--force để dịch lại)")
            continue

        han_lines = [ln for ln in voted_text.split("\n") if ln.strip()]
        phien_lines = [ln for ln in (page.get("l2_phien_am") or "").split("\n") if ln.strip()]
        print(f"  trang {page['page_id']}: đang dịch nghĩa từng dòng qua Gemini ({len(han_lines)} dòng)...")
        try:
            viet_lines = translate_page(client, model, han_lines, phien_lines)
        except Exception as exc:
            print(f"    -> LỖI Gemini ({exc.__class__.__name__}): {exc}")
            continue
        if viet_lines is None:
            print("    -> LỖI: Gemini không trả đúng định dạng JSON hoặc sai số dòng, bỏ qua trang này")
            continue

        page["pairs"] = [
            {"han": h, "viet": v, "align_method": "model", "confidence": "trung_binh"}
            for h, v in zip(han_lines, viet_lines) if v
        ]
        page["l3_dich_nghia"] = " ".join(viet_lines)
        updated += 1
        preview = viet_lines[0][:60] if viet_lines else ""
        print(f"    -> {len(page['pairs'])} pairs, dòng 1: {preview}...")

        if record.get("status") in ("l1_done", "l2_done"):
            record["status"] = "l3_done"
        record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    if updated:
        print(f"\nĐã cập nhật {updated} trang, lưu vào {record_path} (status={record['status']})")
    else:
        print("\nKhông có trang nào được cập nhật.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
