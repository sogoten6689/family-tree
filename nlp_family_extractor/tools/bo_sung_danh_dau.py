"""Chạy bổ sung cho các dòng người soát đã đánh dấu ở thẻ Soát: tạo <cuon>/goi_y.json để web hiện thành gợi ý.

Gợi ý không bao giờ ghi đè bài soát: người soát phải tự bấm nhận hoặc sửa tay. Chỉ dòng đang đánh dấu mới được gửi đi.

Thư mục cuốn cần có soat_nhap.json và anh/<trang>.jpg|jpeg|png (lấy về từ máy chủ, soát xong thì tải goi_y.json lên lại).

    # Chỉ xem sẽ gửi gì, không gọi dịch vụ:
    python nlp_family_extractor/tools/bo_sung_danh_dau.py <thu-muc-cuon>

    # Ghép câu trả lời đã lưu ở <thu-muc>/<trang>*.txt thành gợi ý, không gọi dịch vụ:
    python nlp_family_extractor/tools/bo_sung_danh_dau.py <thu-muc-cuon> --cau-tra-loi <thu-muc>

    # Gọi Gemini web (TOOL_Gemini_API), việc tốn tiền nên chỉ chạy khi có tùy chọn này. Câu trả lời thô lưu vào <thu-muc>:
    python nlp_family_extractor/tools/bo_sung_danh_dau.py <thu-muc-cuon> --cau-tra-loi <thu-muc> --goi-gemini <tool.ini>
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DRAFT_NAME = "soat_nhap.json"
SUGGESTION_NAME = "goi_y.json"
OCR = "ocr"
UNTRANSLATED = "chua_dich"
ROOT = Path(__file__).resolve().parents[2]
PROFILE = "/tmp/gemini_api_chrome"
PROFILE_WAIT_SECONDS = 1800
HAN_RE = re.compile(r"[㐀-䶿一-鿿豈-﫿\U00020000-\U0003ffff]")
ITEM_RE = re.compile(r"\{[^{}]*\}")
PROMPT = """Đây là ảnh một trang gia phả chữ Hán in khắc, chữ viết dọc, đọc từ cột phải sang trái. Người soát đã đánh dấu các dòng dưới đây.
Với mục loại "ocr": tìm đúng chỗ đó trên ảnh, chép lại NGUYÊN VĂN chữ Hán, giữ nguyên dạng chữ, không sửa, không thêm; chữ không đọc được ghi [?]; rồi dịch sang tiếng Việt.
Với mục loại "chua_dich": chỉ dịch phần chữ Hán đã cho sang tiếng Việt, đối chiếu ảnh để hiểu ngữ cảnh.
Bản dịch chỉ dùng chữ quốc ngữ, không lẫn chữ Hán, tên riêng viết âm Hán Việt. Không ghi "(không chắc)": chỗ không chắc thì ghi [?].
Chỉ trả về JSON, không thêm lời: {{"goi_y": [{{"ma": "...", "han": "...", "viet": "..."}}]}}. Với mục loại "chua_dich", để "han" rỗng.

Các dòng cần làm:
{items}"""


def marked_rows(draft: dict, suggestions: dict | None = None) -> dict[str, list[dict]]:
    """Các dòng cần chạy, theo trang: đang đánh dấu, có mã, chưa bỏ, và chưa có gợi ý đang chờ người soát xem.

    Gợi ý người soát đã bỏ thì được chạy lại, nếu dòng vẫn đánh dấu.
    """
    suggestions = suggestions or {}
    pages: dict[str, list[dict]] = {}
    for row in draft.get("rows", []):
        waiting = suggestions.get(row.get("ma"), {}).get("lan", 0) > (row.get("bo_goi_y") or 0)
        if row.get("danh_dau") and row.get("ma") and not row.get("bo") and not waiting:
            pages.setdefault(row["trang"], []).append(row)
    return pages


def build_prompt(rows: list[dict]) -> str:
    items = [
        {
            "ma": row["ma"],
            "loai": row["danh_dau"],
            "han_hien_tai": row.get("han", ""),
            "viet_hien_tai": row.get("viet", ""),
            "ghi_chu_nguoi_soat": row.get("ghi_chu") or "",
        }
        for row in rows
    ]
    return PROMPT.format(items=json.dumps(items, ensure_ascii=False, indent=1))


def _reply_items(reply: str) -> list[dict]:
    """Từng mục trong câu trả lời. Gemini hay trả JSON hỏng cả khối, nên đọc từng mục để mất ít nhất có thể."""
    items = []
    for raw in ITEM_RE.findall(reply or ""):
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and "ma" in item:
            items.append(item)
    return items


def parse_reply(reply: str, rows: list[dict]) -> dict[str, dict]:
    """Gợi ý theo mã. Bỏ mã lạ; dòng chưa dịch thì giữ nguyên chữ Hán; bản dịch lẫn chữ Hán là sai định dạng nên bỏ."""
    kinds = {row["ma"]: row["danh_dau"] for row in rows}
    found: dict[str, dict] = {}
    for item in _reply_items(reply):
        code = item.get("ma")
        if code not in kinds:
            continue
        suggestion = {}
        han = str(item.get("han") or "").strip()
        viet = str(item.get("viet") or "").strip()
        if han and kinds[code] == OCR:
            suggestion["han"] = han
        if viet and not HAN_RE.search(viet):
            suggestion["viet"] = viet
        if suggestion:
            found[code] = suggestion
    return found


def merge_suggestions(old: dict, new: dict[str, dict], stamp: str) -> dict:
    """Thêm gợi ý mới. `lan` tăng dần để gợi ý chạy lại vẫn hiện dù người soát đã bỏ lần trước."""
    merged = dict(old)
    for code, suggestion in new.items():
        merged[code] = {**suggestion, "lan": old.get(code, {}).get("lan", 0) + 1, "luc": stamp}
    return merged


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _profile_busy() -> bool:
    # Mã 0 là có tiến trình, 1 là không có; mã khác là pgrep lỗi, phải coi như đang bận.
    patterns = (f"--user-data-dir={PROFILE}", r"python.*(doc_anh|chay_tool_gemini)")
    return any(subprocess.run(["pgrep", "-f", "--", p], capture_output=True).returncode != 1 for p in patterns)


def _wait_for_profile() -> None:
    """Hồ sơ Chrome dùng chung với các phiên khác, chen vào thì hỏng cả hai. Phải rảnh liên tục một phút."""
    deadline = time.time() + PROFILE_WAIT_SECONDS
    free = 0
    while free < 3:
        if time.time() > deadline:
            raise SystemExit("Hồ sơ Chrome vẫn bận sau 30 phút, không chạy.")
        free = 0 if _profile_busy() else free + 1
        time.sleep(20)


def call_gemini(book_dir: Path, pages: dict[str, list[dict]], replies: Path, config: Path) -> None:
    _wait_for_profile()
    sys.path.insert(0, str(ROOT / "research/hannom-bilingual-dataset/TOOL_Gemini_API"))
    from selenium.common.exceptions import WebDriverException
    from tool_gemini_api import ToolGeminiAPI

    tool = ToolGeminiAPI(str(config))
    try:
        for page, rows in sorted(pages.items()):
            image = next(p for p in (book_dir / "anh" / f"{page}{e}" for e in (".jpg", ".jpeg", ".png")) if p.is_file())
            try:
                tool.reset()
                tool.upload_file(str(image))
                reply = tool.send_request(build_prompt(rows))
                (replies / f"{page}.txt").write_text(reply or "(rỗng)", encoding="utf-8")
                print(f"{page}: đã nhận câu trả lời cho {len(rows)} dòng", flush=True)
            except WebDriverException as exc:
                print(f"{page}: LỖI {type(exc).__name__}: {str(exc)[:150]}", flush=True)
    finally:
        tool.quit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("book_dir", type=Path)
    parser.add_argument("--cau-tra-loi", type=Path, help="thư mục câu trả lời <trang>*.txt")
    parser.add_argument("--goi-gemini", type=Path, help="tệp tool.ini của TOOL_Gemini_API; có tùy chọn này mới gọi dịch vụ")
    args = parser.parse_args()

    pages = marked_rows(_read_json(args.book_dir / DRAFT_NAME), _read_json(args.book_dir / SUGGESTION_NAME))
    total = sum(len(rows) for rows in pages.values())
    print(f"{total} dòng cần chạy ở {len(pages)} trang: {', '.join(sorted(pages)) or '(không có)'}")
    if not total:
        return
    if not args.cau_tra_loi:
        for page, rows in sorted(pages.items()):
            print(f"\n=== Trang {page} ===\n{build_prompt(rows)}")
        return

    args.cau_tra_loi.mkdir(parents=True, exist_ok=True)
    if args.goi_gemini:
        call_gemini(args.book_dir, pages, args.cau_tra_loi, args.goi_gemini)

    found: dict[str, dict] = {}
    for page, rows in sorted(pages.items()):
        for path in sorted(args.cau_tra_loi.glob(f"{page}*.txt")):
            found.update(parse_reply(path.read_text(encoding="utf-8"), rows))
    target = args.book_dir / SUGGESTION_NAME
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _write_atomic(target, json.dumps(merge_suggestions(_read_json(target), found, stamp), ensure_ascii=False, indent=1))
    print(f"Có gợi ý cho {len(found)}/{total} dòng, ghi vào {target}")


if __name__ == "__main__":
    main()
