#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ghép từng CHỮ/CỤM TỪ Hán với từ/cụm tiếng Việt tương ứng — chi tiết hơn
`pairs[].han`/`viet` (vốn ghép cả dòng/câu). Ghi vào `pairs[].tu_ghep`.

Dùng Gemini (GOOGLE_API_KEY — TỐN QUOTA THẬT, mỗi PAIR (không phải mỗi trang)
là 1 lần gọi — 1 trang ~8 pairs thì tốn ~8 lần gọi, cân nhắc trước khi chạy
--all cho tài liệu nhiều trang).

Dùng:
  python3 scripts/ghep_tu.py <doc_id> [--pages 001,002] [--force]
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

PROMPT = """Bạn ghép từng CHỮ/CỤM TỪ chữ Hán với từ/cụm từ tiếng Việt tương ứng trong 1 câu đã dịch.

Câu Hán: {han}
Câu Việt (đã dịch nghĩa): {viet}

Tách câu Hán thành các cụm từ có nghĩa (ưu tiên cụm 2-4 chữ nếu là 1 khái niệm,
1 chữ nếu là hư từ/động từ đơn), theo ĐÚNG thứ tự xuất hiện trong câu Hán. Với
mỗi cụm, tìm đúng từ/cụm từ tiếng Việt tương ứng trong câu dịch đã cho — không
dịch lại từ đầu, chỉ tìm phần khớp có sẵn trong câu Việt. Nếu 1 cụm Hán không
có từ tương ứng rõ ràng trong câu Việt (do lược dịch), bỏ qua cụm đó.

Trả về ĐÚNG định dạng JSON (mảng), không thêm markdown code fence, không thêm
giải thích:
[{{"han": "...", "viet": "..."}}, ...]
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


def ghep_tu_pair(client, model, han: str, viet: str) -> list[dict] | None:
    prompt = PROMPT.format(han=han, viet=viet)
    resp = call_with_timeout(client.models.generate_content, model=model, contents=prompt, timeout_s=90.0)
    data = parse_json_array((resp.text or "").strip())
    if data is None:
        return None
    return [{"han": str(item.get("han", "")), "viet": str(item.get("viet", ""))}
            for item in data if item.get("han") and item.get("viet")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("doc_id")
    ap.add_argument("--pages", default=None, help="vd 001,002 — mặc định tất cả trang có pairs")
    ap.add_argument("--force", action="store_true", help="ghép lại cả pair đã có tu_ghep")
    args = ap.parse_args()

    client, model = gemini_client()

    record_path = find_record_path(args.doc_id)
    record = json.loads(record_path.read_text(encoding="utf-8"))

    wanted = set(p.strip() for p in args.pages.split(",")) if args.pages else None
    n_pairs_done = 0
    n_pages_touched = 0
    for page in record.get("pages", []):
        if wanted and page["page_id"] not in wanted:
            continue
        pairs = page.get("pairs") or []
        if not pairs:
            continue
        touched_this_page = False
        print(f"  trang {page['page_id']}: {len(pairs)} pair...")
        for pr in pairs:
            if pr.get("tu_ghep") and not args.force:
                continue
            try:
                tu_ghep = ghep_tu_pair(client, model, pr["han"], pr["viet"])
            except Exception as exc:
                print(f"    -> LỖI Gemini ({exc.__class__.__name__}) cho pair {pr['han'][:20]}...: {exc}")
                continue
            if tu_ghep is None:
                print(f"    -> LỖI định dạng cho pair {pr['han'][:20]}..., bỏ qua")
                continue
            pr["tu_ghep"] = tu_ghep
            n_pairs_done += 1
            touched_this_page = True
            print(f"    -> {pr['han'][:20]}...: {len(tu_ghep)} cụm từ")
        if touched_this_page:
            n_pages_touched += 1

    if n_pairs_done:
        record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nĐã ghép từ cho {n_pairs_done} pair ({n_pages_touched} trang), lưu vào {record_path}")
    else:
        print("\nKhông có pair nào được cập nhật.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
