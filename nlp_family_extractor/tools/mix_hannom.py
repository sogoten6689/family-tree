#!/usr/bin/env python3
"""Mix 2 OCR (lab Kim Hán Nôm + Paddle) → data/01_interim/.../mix/{n}.han.txt

Thứ tự & văn bản chính lấy từ lab `result_ocr_text` (khung đọc cột đã đúng —
xem đối soát p.0 trong docs/planning/mix_translate_family_tree_plan.md §1).
Paddle chỉ dùng để đối chiếu: dòng không khớp lab (theo tỉ lệ tương đồng ký
tự) được ghi vào file *.mix_notes.md riêng cho người soát, KHÔNG trộn vào
*.han.txt để tránh làm bẩn input cho bước phiên âm/dịch nghĩa kế tiếp.

Chỉ đọc pages/*.json và paddleocr/*.txt của sách — không sửa/ghi đè gì trong
thư mục nguồn.

  python nlp_family_extractor/tools/mix_hannom.py --book nguyen-ke-han-nom --pages 0,2
"""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path
from typing import Any

_TOOLS = Path(__file__).resolve().parent
REPO = _TOOLS.parents[1]

SIM_MATCH = 0.92
SIM_NOTE_MIN = 0.30


def load_catalog() -> list[dict[str, Any]]:
    path = REPO / "data/00_raw/hannom/books_catalog.json"
    return list(json.loads(path.read_text(encoding="utf-8")).get("books") or [])


def book_root(book: dict[str, Any]) -> Path:
    if book.get("source") == "tong_pho_pdf":
        return REPO / "data/00_raw/du_lieu_han_nom_moi/13_8_2026" / book["book_id"]
    rel = (book.get("paths") or {}).get("root") or ""
    path = REPO / rel
    return path.parent if path.is_file() else path


def lab_conf_map(bbox_entries: list) -> dict[str, float]:
    conf: dict[str, float] = {}
    for entry in bbox_entries:
        try:
            _, (text, score) = entry
        except (ValueError, TypeError):
            continue
        conf[text] = max(conf.get(text, 0.0), float(score))
    return conf


def best_paddle_match(lab_line: str, paddle_lines: list[str]) -> tuple[str | None, float]:
    best_text, best_ratio = None, 0.0
    for line in paddle_lines:
        ratio = difflib.SequenceMatcher(None, lab_line, line).ratio()
        if ratio > best_ratio:
            best_text, best_ratio = line, ratio
    return best_text, best_ratio


def mix_page(lab_json: Path, paddle_txt: Path, han_dest: Path, notes_dest: Path) -> None:
    lab = json.loads(lab_json.read_text(encoding="utf-8"))
    lab_lines: list[str] = [str(t).strip() for t in (lab.get("result_ocr_text") or []) if str(t).strip()]
    conf = lab_conf_map(lab.get("result_bbox") or [])
    paddle_lines = (
        [line.strip() for line in paddle_txt.read_text(encoding="utf-8").splitlines() if line.strip()]
        if paddle_txt.is_file()
        else []
    )

    notes = [
        f"# mix notes — {lab_json.stem}\n",
        f"- nguồn lab: `{lab_json.relative_to(REPO)}`\n",
        f"- nguồn paddle: `{paddle_txt.relative_to(REPO) if paddle_txt.is_file() else '(không có)'}`\n",
        "- quy tắc: văn bản chính (`*.han.txt`) = lab, theo thứ tự cột lab.\n",
        "  Paddle chỉ đối chiếu; không tự ý thay lab bằng paddle.\n\n",
        "| # | lab_conf | paddle đối chiếu | sim |\n",
        "|---|----------|-------------------|-----|\n",
    ]
    for i, lab_line in enumerate(lab_lines):
        lab_conf = conf.get(lab_line)
        conf_str = f"{lab_conf:.2f}" if lab_conf is not None else "?"
        match_text, ratio = best_paddle_match(lab_line, paddle_lines)
        if match_text is None or ratio < SIM_NOTE_MIN:
            paddle_col, sim_str = "(không tìm được dòng khớp)", "-"
        elif ratio >= SIM_MATCH:
            paddle_col, sim_str = "(khớp)", f"{ratio:.2f}"
        else:
            paddle_col, sim_str = match_text.replace("|", "\\|"), f"{ratio:.2f}"
        notes.append(f"| {i} | {conf_str} | {paddle_col} | {sim_str} |\n")

    han_dest.write_text("\n".join(lab_lines) + "\n", encoding="utf-8")
    notes_dest.write_text("".join(notes), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--book", required=True)
    parser.add_argument("--pages", required=True, help="vd: 0,2")
    parser.add_argument(
        "--out-root",
        default="data/01_interim/huong_nguyen_ke",
        help="Thư mục 01_interim đích (KHÔNG phải dich/ trong thư mục sách gốc).",
    )
    args = parser.parse_args()

    catalog = {b["book_id"]: b for b in load_catalog()}
    book = catalog.get(args.book)
    if book is None:
        raise SystemExit(f"Không có book_id {args.book}")
    root = book_root(book)
    pages_dir = root / "pages"
    paddle_dir = root / "paddleocr"
    out_dir = REPO / args.out_root / "mix"
    out_dir.mkdir(parents=True, exist_ok=True)

    for stem in [p.strip() for p in args.pages.split(",") if p.strip()]:
        lab_json = pages_dir / f"{stem}-ocr-raw.json"
        paddle_txt = paddle_dir / f"{stem}-paddleocr.txt"
        if not lab_json.is_file():
            print(f"— thiếu {lab_json.relative_to(REPO)}")
            continue
        han_dest = out_dir / f"{stem}.han.txt"
        notes_dest = out_dir / f"{stem}.mix_notes.md"
        mix_page(lab_json, paddle_txt, han_dest, notes_dest)
        print(f"  wrote {han_dest.relative_to(REPO)} (+ {notes_dest.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
