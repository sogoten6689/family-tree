#!/usr/bin/env python3
"""P0 đối soát Ô.cố + glossary tinh hoa (tuần 28/08).

From repo root:

  python nlp_family_extractor/tools/week_28_08_process.py
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZipFile
import xml.etree.ElementTree as ET

_TOOLS = Path(__file__).resolve().parent
import sys

if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from build_hannom_catalog import CJK_RE, W_NS, find_named_dir, fold_name, repo_root

# OCR page → Ô.cố mục (semantic; Word is Quốc ngữ paraphrase, not Hán transcription).
PAGE_MAP: dict[int, dict[str, str]] = {
    0: {
        "genre": "thuận phân gia tài (分家財)",
        "oco": "§5 — vợ chồng phân chia ruộng đất cho con",
        "align": "cùng thể loại; tên con OCR = 阮泰 / 阮朋 / 阮珠, cha 阮文顛 — Word ghi Thị Khảm / Khảng / Chinh (sai hoặc khác hệ thống húy)",
    },
    1: {
        "genre": "tiếp 分家 + nhận lãnh",
        "oco": "§5 (mặt sau / tờ kê đồ vật)",
        "align": "認領阮朋 / 阮遯 / 阮珠 — cùng vụ phân sản trang 0",
    },
    2: {
        "genre": "ký nhận 保大八年",
        "oco": "§5 kết / chữ ký",
        "align": "長子阮泰 仲子阮朋 季子阮珠; 保大捌年陸月初陸日. Word không ghi niên hiệu Bảo Đại 8",
    },
    3: {
        "genre": "乞除著 / sổ điền 成泰",
        "oco": "§1 hoặc §6 (công văn đất) — không khớp từng chữ",
        "align": "OCR yếu (mean ~0.56). Có 阮文顛, 為穀, 延慶/延度 phủ. Word §1 là Kiều Văn Lộc 1907 — khác vụ",
    },
    4: {
        "genre": "khế tuyệt mại",
        "oco": "§6 tư liệu công vụ chưa rõ",
        "align": "OCR rất yếu; đủ nhận 絕賣 / 阮文顛. Không map chắc sang một mục Word",
    },
    5: {
        "genre": "tuyệt mại 成泰十五年",
        "oco": "§6",
        "align": "niên hiệu đọc được; địa danh 為穀. Word không trích Thành Thái 15",
    },
    6: {
        "genre": "tuyệt mại 成泰十年",
        "oco": "§6",
        "align": "tên 阮氏亥 / 阮文錦. Word không có các húy này",
    },
    7: {
        "genre": "đoạn mại",
        "oco": "§6",
        "align": "OCR yếu; còn 斷賣 / 延慶 phủ",
    },
    8: {
        "genre": "đoạn mại 嗣德",
        "oco": "§6 — không phải cùng tờ với §1 (ghi chú thầy trong Word)",
        "align": "Word P023: ảnh mục 1 và mục 6 là một tài liệu. OCR p.8 ≠ p.14 (p.14 mới là 喬文祿)",
    },
    9: {
        "genre": "tuyệt mại huynh → đệ",
        "oco": "§2 đóng góp Nguyễn Hữu Bằng — gần nhất",
        "align": "胞兄 阮有朋 + 黎氏征 tuyệt mại cho 胞弟 阮玉珠. 阮有朋 ≈ Nguyễn Hữu Bằng. Word §2 không kể vụ bán này",
    },
    10: {
        "genre": "ký 保大十四年 + header Pháp",
        "oco": "mặt sau khế p.9 / không có trong Word",
        "align": "REQUÊTES / CHINE in sẵn; 作詞人阮有朋. Paddle Latin+Hán mean cao (~0.91) vì form in",
    },
    11: {
        "genre": "công văn (札) phủ → xã Phú Lộc",
        "oco": "§1 mặt công văn — có thể; Word dịch rất lệch",
        "align": "OCR yếu. Có 富祿社, 侵耕. Không thấy 成泰十九 / Kiều Văn Lộc",
    },
    12: {
        "genre": "khế quả phụ? + rác Latin",
        "oco": "§4 vợ giữ phẩm hạnh? (giả thuyết yếu)",
        "align": "孀婦氏花; Paddle đọc nhầm khối in/đóng dấu thành '学堂定堂'. Không đủ để khẳng định §4",
    },
    13: {
        "genre": "trùng p.9",
        "oco": "— (không đối Word lần 2)",
        "align": "FACT: cùng 9 dòng CJK với p.9 (ảnh chụp lại / mặt giống). Không đếm 2 khế",
    },
    14: {
        "genre": "đơn 喬文祿",
        "oco": "§1 Lễ đơn Kiều Văn Lộc (Thành Thái 19 / 1907)",
        "align": "喬文祿 ≈ Kiều Văn Lộc; 延慶府中洲總富祿. Word thêm 'mùng 6 tháng chạp 1907' — OCR trang này không đọc được niên hiệu (thiếu hoặc mờ)",
    },
}


def paddle_scores(payload: dict[str, Any]) -> list[float]:
    scores: list[float] = []
    for item in payload.get("result_bbox") or []:
        if isinstance(item, list) and len(item) >= 2 and isinstance(item[1], (list, tuple)) and len(item[1]) >= 2:
            try:
                scores.append(float(item[1][1]))
            except (TypeError, ValueError):
                pass
    return scores


def read_docx_paras(path: Path) -> list[str]:
    with ZipFile(path) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
    paras: list[str] = []
    for node in root.iter(f"{W_NS}p"):
        text = "".join((t.text or "") for t in node.iter(f"{W_NS}t")).strip()
        if text:
            paras.append(unicodedata.normalize("NFC", text))
    return paras


def write_doi_soat(repo: Path) -> Path:
    week = repo / "data/00_raw/du_lieu_han_nom_moi/25_8_2026"
    huong = find_named_dir(week, "huong")
    if huong is None:
        raise SystemExit("Không thấy thư mục Hương")
    han = find_named_dir(huong, "han")
    if han is None:
        raise SystemExit("Không thấy Nguyễn Kế Hán Nôm")
    paddle = han / "paddleocr"
    docx = next((p for p in han.iterdir() if p.suffix.lower() == ".docx" and "co" in fold_name(p.name)), None)
    paras = read_docx_paras(docx) if docx else []
    oco_cjk = "".join(CJK_RE.findall("\n".join(paras)))

    rows: list[dict[str, Any]] = []
    all_scores: list[float] = []
    for i in range(15):
        payload = json.loads((paddle / f"{i}-paddleocr.json").read_text(encoding="utf-8"))
        scores = paddle_scores(payload)
        all_scores.extend(scores)
        lines = [str(x) for x in (payload.get("result_ocr_text") or [])]
        blob = "\n".join(lines)
        cjk = "".join(CJK_RE.findall(blob))
        overlap = len(set(cjk) & set(oco_cjk)) / max(len(set(cjk)), 1)
        excerpt = " / ".join(lines[:4])
        if len(excerpt) > 80:
            excerpt = excerpt[:80] + "…"
        meta = PAGE_MAP[i]
        rows.append(
            {
                "page": i,
                "n_lines": len(lines),
                "mean": round(sum(scores) / len(scores), 4) if scores else None,
                "cjk": len(cjk),
                "cjk_overlap_word": round(overlap, 3),
                "excerpt": excerpt,
                **meta,
            }
        )

    mean_all = round(sum(all_scores) / len(all_scores), 4) if all_scores else None
    out = huong / "doi_soat_oco.md"
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    lines_md = [
        "# Đối soát OCR Paddle ↔ Ô.cố (Nguyễn Kế Hán-Nôm)",
        "",
        f"> Tạo: `{now}`  ",
        "> Scan: `nguyen-ke-han-nom` 15 trang · Gold: `Tài liệu dịch hán nôm Ô.cố.docx`",
        "",
        "## Kết luận",
        "",
        "**Ô.cố không phải bản phiên âm/Hán song song.** Word là ghi chú + dịch nghĩa Quốc ngữ (46 đoạn, ~9.3k ký tự, gần như không CJK). Không thể tick từng chữ OCR. Đối soát = map **thể loại khế / nhân danh / địa danh** sang 6 mục Word.",
        "",
        f"- Paddle mean mọi dòng: **{mean_all}** (inventory 25/08: 0.7022).  ",
        f"- Lab Kim Hán Nôm: **0/15**.  ",
        f"- Word CJK: **{len(oco_cjk)}** ký tự — overlap chữ Hán với OCR gần 0, đúng kỳ vọng (dịch chứ không chép Hán).  ",
        "- Trang **9 ≡ 13** (cùng văn): đếm **14 khế/tờ độc lập**, không 15.",
        "",
        "## Độ tin cậy",
        "",
        "| Claim | Mức |",
        "|-------|-----|",
        "| Ô.cố = Quốc ngữ, không phải Hán line-by-line | cao (đếm CJK Word) |",
        "| p.0–2 = phân gia tài ba con trai 泰/朋/珠 | cao (OCR) |",
        "| p.9/13 = 阮有朋 bán cho 阮玉珠 | cao |",
        "| p.14 = Kiều Văn Lộc / §1 | cao (喬文祿) |",
        "| p.12 = §4 quả phụ | thấp |",
        "| Tên con trong Word §5 (Thị Khảm…) = OCR | bác bỏ — lệch hệ thống tên |",
        "",
        "## Bảng 15 trang",
        "",
        "| Trang | Mean | Dòng | CJK | Thể OCR | Mục Ô.cố | Lỗi / ghi chú |",
        "|------:|-----:|-----:|----:|---------|----------|---------------|",
    ]
    for row in rows:
        mean = f"{row['mean']:.3f}" if row["mean"] is not None else "—"
        note = row["align"].replace("|", "/")
        lines_md.append(
            f"| {row['page']} | {mean} | {row['n_lines']} | {row['cjk']} | {row['genre']} | {row['oco']} | {note} |"
        )
    lines_md += [
        "",
        "## Mục lục Ô.cố (quan sát trực tiếp)",
        "",
        "| Mục Word | Nội dung Word nói | OCR gần nhất |",
        "|----------|-------------------|--------------|",
        "| 1. Công văn ruộng đất | Kiều Văn Lộc, Thành Thái 19 (1907), Phủ Diên Khánh | **p.14** (喬文祿). p.11 có thể là công văn khác |",
        "| 2. Đóng góp Nguyễn Hữu Bằng | phân chia tài sản, mở rộng Diên Khánh | **p.9–10** (阮有朋) — Word không kể khế tuyệt mại huynh đệ |",
        "| 3. Nhật ký bạn ông Bằng | nhà buôn suy, công cụ hỏng | **không thấy** trên 15 trang OCR |",
        "| 4. Vợ giữ phẩm hạnh | goá phụ | **p.12?** (孀婦) — không chắc |",
        "| 5. Phân chia ruộng cho con | chữ ký Thị Khảm/Khảng/Chinh | **p.0–2** — OCR: 阮泰/朋/珠, cha 阮文顛 |",
        "| 6. Công vụ khác | Bảo Đại 6 (1931)? dân Nguyễn Mẫn | một phần p.3–8; niên hiệu OCR = Thành Thái / Tự Đức / Bảo Đại 8 và 14 |",
        "",
        "## Lỗi dịch Word (đưa thầy)",
        "",
        "1. **§5 đổi nam → nữ họ Thị** — OCR rõ 長子/仲子/季子 họ 阮. Đây là lỗi dịch hoặc nhầm ảnh, không phải biến thể húy thông thường.",
        "2. **Thiếu niên hiệu** trên khế p.2 (Bảo Đại 8) và p.10 (Bảo Đại 14).",
        "3. **Gộp/nhầm ảnh** (ghi chú trong Word: trang 1 mục 1 ≡ trang 8 mục 6). OCR p.8 (Tự Đức đoạn mại) ≠ p.14 (đơn Kiều). Cần thầy/Hương chỉ lại số ảnh gốc.",
        "4. Địa danh OCR hay đọc 延度 / 寫祿 / 窗穀 thay vì 延慶 / 富祿 / 富穀 — Paddle trên thảo.",
        "",
        "## So với tế văn 24/08",
        "",
        "Tế văn in (`24_08_2026/test/`, PP-OCRv6, sau RTL) mean ~**0.91**. Kế ước thảo Hương mean **0.70**. Chênh ~0.21 điểm — khác **script** (in vs thảo) và **layout** (cột thẳng vs khế không đều), không phải khác engine.",
        "",
        "## Trích OCR ngắn (đối chiếu tay)",
        "",
    ]
    for row in rows:
        lines_md.append(f"- **p.{row['page']}** `{row['excerpt']}`")
    lines_md += [
        "",
        "## Không làm tiếp từ bảng này",
        "",
        "- Không coi Ô.cố là gold **ký tự** cho CER/WER.",
        "- Có thể dùng Word như gold **dịch nghĩa lỏng** sau khi sửa §5.",
        "- Lab phiên âm: vẫn 0/15 — chặn Qwen «Hán đã hiệu đính».",
        "",
    ]
    out.write_text("\n".join(lines_md), encoding="utf-8")
    return out


def extract_pdf_text(path: Path, max_pages: int = 40) -> list[str]:
    try:
        import pypdfium2 as pdfium  # type: ignore
    except ImportError:
        return []
    doc = pdfium.PdfDocument(str(path))
    pages: list[str] = []
    try:
        n = min(len(doc), max_pages)
        for i in range(n):
            page = doc[i]
            textpage = page.get_textpage()
            text = (textpage.get_text_bounded() or "").strip()
            textpage.close()
            page.close()
            pages.append(unicodedata.normalize("NFC", text))
    finally:
        doc.close()
    return pages


def write_tinh_hoa_glossary(repo: Path) -> Path:
    sach = repo / "data/04_external/sach"
    pdf = next((p for p in sach.iterdir() if p.suffix.lower() == ".pdf" and "tinh" in fold_name(p.name)), None)
    if pdf is None:
        raise SystemExit("Không thấy Gia phả học tinh hoa.pdf")
    pages = extract_pdf_text(pdf, max_pages=50)
    out_dir = repo / "data/01_interim/docx_extract"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "tinh_hoa_glossary.md"
    blob = "\n".join(pages)
    # Pull likely definition-ish sentences; keep human-curated core below + evidence quotes.
    quotes: list[str] = []
    for page_i, text in enumerate(pages, start=1):
        for raw in re.split(r"(?<=[.:;])\s+", text.replace("\r", "\n")):
            line = " ".join(raw.split())
            if len(line) < 20:
                continue
            key = fold_name(line)
            if any(tok in key for tok in ("toc pha", "tong pha", "chi pha", "gia pha", "pha ky", "pha do", "the pha")):
                quotes.append(f"p.{page_i}: {line[:280]}")
            if len(quotes) >= 24:
                break
        if len(quotes) >= 24:
            break

    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    n_chars = sum(len(p) for p in pages)
    md = f"""# Glossary — *Gia phả học tinh hoa* (1 trang làm việc)

> `sach-gia-pha-hoc-tinh-hoa` · PDF `data/04_external/sach/` · đọc lớp text, **không OCR** · `{now}`

Lớp text 50 trang đầu: {n_chars} ký tự. Dùng đối chiếu thuật ngữ với Lâm Hoài Phương / luận văn — **không** đưa vào gold NER VGP.

## Loại sách / đơn vị họ

| Thuật ngữ | Dùng trong LV / catalog repo | Trong tinh hoa (tóm, không thay SSOT) |
|-----------|------------------------------|----------------------------------------|
| **Gia phả** | tài liệu ghi hệ thống họ | sách = lý thuyết soạn phả hiện đại |
| **Tộc phả** | `loai: toc_pha` — một tộc | phạm vi cả họ, nhiều chi |
| **Tông phả** | `tong_pha` / `tong_pho_pdf` | nhánh lớn / tông; PDF Hán 13/08 là tông phả **in chữ Hán**, khác sách này |
| **Chi phả / hộ phả** | `chi_pha`, `ho_pha` | một chi, một hộ |
| **Thế phả** | Nguyễn Phúc 1995: sách dùng **Hệ** thay «thế» | thứ tự đời; không đồng nghĩa Hệ Nguyễn Phúc |
| **Hệ → Phòng → Chi** | chỉ Nguyễn Phúc (1995) | **không** gán cho họ thường |
| **Phả ký** | tự sự / văn truyện đời tổ | khác **phả đồ** (cây) |
| **Phả đồ** | renderer; Trần 200 **thiếu** phần III | sơ đồ nhân vật |
| **Tu phổ / tục biên** | Trần 1890 / 1920 | lần sửa vs lần nối |
| **Phó ý** | Phạm 1876 — **tách** khỏi cây | danh sách đứng cúng, không phải cạnh cha–con |
| **Kế ước / văn khế** | Hương 15 trang | không phải phả ký |

## Bố cục phả (checklist đọc)

1. Bìa / nhan đề / ký hiệu thư viện  
2. Lời tựa (tuần 17/08: tag `tua`)  
3. Phả ký (văn)  
4. Phả đồ (cây) — có thể thiếu như Trần HN.2011.11.200  
5. Thế thứ / kê húy–thụy–kỵ–mộ  
6. Phụ lục: phó ý, văn tế, bằng khoán, đính chính  

## Ràng buộc corpus

- Tinh hoa = `kind=ly_thuyet`, `not_corpus`.  
- Không OCR hàng loạt. Không trộn metric với VGP / kế ước Hương.  
- Nguyễn Phúc 1995: glossary **Hệ/Phòng/Chi** lấy từ chính sách đó, không copy bảng này.

## Trích lớp text (bằng chứng, cắt)

"""
    if quotes:
        md += "\n".join(f"- {q}" for q in quotes[:18])
    else:
        md += "(Lớp text PDF không bắt được câu có tộc/tông/chi — có thể PDF ảnh. Giữ bảng trên từ catalog + phân tích 24/08.)"
    md += "\n"
    out.write_text(md, encoding="utf-8")
    return out


def main() -> int:
    repo = repo_root()
    doi = write_doi_soat(repo)
    print(f"Wrote {doi}")
    gloss = write_tinh_hoa_glossary(repo)
    print(f"Wrote {gloss}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
