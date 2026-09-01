#!/usr/bin/env python3
"""Write per-book Markdown analysis for Word files in 24_8_2026."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ANALYSIS: dict[str, dict[str, Any]] = {
    "docx-pham-1876": {
        "loai_guess": "Tộc phả / hộ phả kèm phó ý cúng — không phải tông phả in khắc Trung Quốc.",
        "noi_dung": [
            "Lời tựa 05/10/2018 (Phạm Văn Tiệp, Biên Hòa): gốc Hán ~150 năm, ẩm ướt, thiếu trang; Trung tâm NCTH Gia phả TP.HCM và Lâm Hoài Phương dịch.",
            "Hai khối gốc: (1) Gia phả do Phạm Hữu Huân biên năm Long Phi Tự Đức 30 (1876) tại thôn Tiên Lã, xã An Trung — bốn đời (cố → ông → cha → soạn giả). (2) Phó ý: danh người đứng cúng thủy tổ Thái Bảo kim tử vinh lộc hữu đại phu và **7 chi**.",
            "Truyền thuyết thủy tổ người Kinh Bắc, lấy vợ An Trung, liệt tổ sinh bảy chi; mộ liệt tổ thôn Tiên Lã, xứ Chi Phong.",
            "Chi soạn giả: Phúc Hy (húy Kỳ) → Phúc Hạo (húy Cảnh) → Thiện Tâm (húy Lũng/Dũng) → Phúc Trực (húy Vinh, 1757–1818) → Duy Thông / Khắc Minh (cha soạn giả).",
            "Bảy chi nêu sơ: Cự Trữ–Phương Để; Hạ–Thuế Đông / Trung Lao Hạ; Kênh Đào; Cát Chử; hai–ba chi Cát Chử Ngoại Hạ (có cử nhân Phạm Khắc Thận).",
        ],
        "dia_danh": [
            "An Trung, Tiên Lã, Phương Để, Cự Trữ, Thuế Đông, Trung Lao Hạ, Kênh Đào, Cát Chử, Từ Quán, An Lễ, Mặt Lăng, Nhự Nương, Ngọc Giả, Liễu Đề, Đại An, Lộng Điền, Kim Sơn (ấp Chí Tĩnh).",
        ],
        "pipeline": [
            "Đã có dịch nghĩa + phiên âm → gold văn bản / extract cây, **không** OCR.",
            "Dịch và phiên âm song song: đối chiếu được tên thụy, húy, hướng mộ.",
            "Phó ý liệt kê cúng, ít quan hệ cha–con — tách tag `pho_y`, đừng trộn metric với phả ký.",
        ],
        "han_che": [
            "Gần như không còn chữ Hán trong Word (4 ký tự CJK) — không đối chiếu OCR.",
            "Bảy chi ngoài chi soạn giả chỉ phác thảo; tổ bà đời trên «không biết rõ».",
            "Chưa có ảnh scan gốc trong repo.",
        ],
    },
    "docx-nguyen-van": {
        "loai_guess": "Chi phả / phái phả họ Nguyễn Văn — ghi giỗ, mộ, vợ cả/hai/ba, chi thứ.",
        "noi_dung": [
            "Ba lớp một file: **I. Dịch nghĩa** · **II. Phiên âm** · **III. 漢字** (cùng nội dung, khác chữ).",
            "Lời Hán: dương lịch 1975, Ất Mão tháng 4 ngày 4; tự xưng ~**7 đời**, ~**400 người**; mỗi chi một bản Hán+Quốc ngữ.",
            "Sao lục: Nguyễn Văn Líu (Liếu), cháu nối dõi chi 1; đệ tử Thích Từ Bảo.",
            "Ông sơ Nguyễn Văn Hiếu (giỗ 29/9, mộ rừng Đồng Lành). Ba vợ: Nguyễn thị Định (phái 1, Hội Sơn); Huỳnh thị Trương (Danh, Vang, Thăm, Viếng, Toàn); Phan thị Lãm, Lạc Câu (phái 3, Hội Sơn).",
            "Ông cố Nguyễn Văn Danh. Vợ cả Đỗ thị Tài → chi 1 Huỳnh, chi 2 Huệ, chi 3 Quế, … Vợ hai Lê thị Thọ (Trà Đóa) → chi 4 Hậu, chi 5 Tiệm. Chi 1 đi xuống Diêu / Dụ.",
        ],
        "dia_danh": [
            "Hội Sơn, Đồng Lành, Lạc Câu, Trà Đóa, Tân An (xuất hiện trong bản dịch).",
        ],
        "pipeline": [
            "Lớp III là **nguyên văn Hán** (kể cả chữ Nôm/Hán mở rộng như 𠮩) — corpus song ngữ hiếm trong lô 24/08.",
            "Bố cục một người / một khối ngắn: dễ gán node (húy, giỗ, mộ, phối, sinh hạ).",
            "Gold extract cây Quốc ngữ; lớp Hán để đánh giá OCR/dịch sau này **nếu** có ảnh.",
        ],
        "han_che": [
            "Không có ảnh scan; Word tách đoạn rất mảnh (1820 đoạn / 24 trang) — parser đừng lấy «1 đoạn = 1 sự kiện».",
            "Regex tên dễ dính vì xuống dòng giữa họ và tên.",
            "Một số chỗ «Nguyễn vô danh»; quan hệ chi 2–5 cần đọc tuần tự, không có phả đồ.",
        ],
    },
    "docx-tran-200": {
        "loai_guess": "Tộc phả họ Trần (Thuận Hóa) — tu phổ 1890, tục biên 1920 (cuốn khác).",
        "noi_dung": [
            "Bìa: Sở VHTT TP.HCM, Thư viện KHTH, CLB Hán Nôm; ký hiệu **GSL HN.2011.11.200**.",
            "Biên dịch 05/2018, Lâm Hoài Phương. Mục lục 4 phần: I dịch nghĩa, II phiên âm, III phả đồ, IV nhận xét — **phần III không có trong file**.",
            "Tu phổ tháng 2 Thành Thái 2 (**1890**). Thủy tổ Trần Khánh Hữu (quận Dĩnh Xuyên); khai khẩn Thuận Hóa / Triệu Phong.",
            "Đời 1–5 tương đối rõ (Khánh Hữu → Khánh Dụ → Mộc → Cẩm, Điện Bàn → Khang → Liêm Văn Khoa / Trường).",
            "Đời 6–10: liệt kê tên, người dịch ước ~130 vị, **ít liên kết cha–con**. Đời 11–16 tách hai phái; đời 12/14 có chỗ không rõ thân sinh.",
            "Tục biên 1920: **GSL HN.2011.11.119** (không có trong thư mục này).",
        ],
        "dia_danh": [
            "Thanh Thủy Thượng, phường Thủy Dương, TX Hương Thủy, TT-Huế; Phủ Triệu Phong; Điện Bàn; xã Linh Ti.",
            "Người dịch chú: Hồng Đức bản đồ 1490 viết Phong 寷 (phong phú); gia phả ghi Phong 封 (ban cấp).",
        ],
        "pipeline": [
            "Đời 1–5 + 12–16: extract quan hệ được. Đời 6–10: chỉ NER danh sách, không ép cạnh cha–con.",
            "Đã có dịch + phiên âm; thiếu Hán và thiếu phả đồ.",
        ],
        "han_che": [
            "Word dính chữ (Trần vănXuân, Trần vănKhangngày) — phải tách tay trước NLP.",
            "Chỉ vài chữ Hán (chú Phong 肇/寷/封), không dùng làm gold OCR.",
            "Chưa có scan gốc HN.2011.11.200 / 119.",
        ],
    },
}


def _fmt(n: Any) -> str:
    if n is None:
        return "—"
    if isinstance(n, float):
        return f"{n:.4f}"
    if isinstance(n, int):
        return f"{n:,}".replace(",", ".")
    return str(n)


def analysis_record(book: dict[str, Any], sections: list[dict[str, Any]]) -> dict[str, Any]:
    extra = ANALYSIS.get(book.get("book_id") or "", {})
    stats = book.get("text_stats") or {}
    return {
        "book_id": book.get("book_id"),
        "title_han": book.get("title_han") or "",
        "title_vn": book.get("title_vn") or "",
        "clan_key": book.get("clan_key"),
        "catalog_code": book.get("catalog_code") or "",
        "docx": (book.get("paths") or {}).get("docx") or "",
        "year_source": book.get("year_source"),
        "year_translate": book.get("year_translate"),
        "language": book.get("language"),
        "loai": book.get("loai") or [],
        "layout_tags": book.get("layout_tags") or [],
        "notes": book.get("notes") or "",
        "bytes": book.get("bytes"),
        "stats": stats,
        "sections": [
            {
                "id": s.get("id"),
                "title": s.get("title"),
                "n_paras": s.get("n_paras"),
                "chars": s.get("chars"),
            }
            for s in sections
        ],
        **{k: extra[k] for k in ("loai_guess", "noi_dung", "dia_danh", "pipeline", "han_che") if k in extra},
    }


def render_analysis_md(rec: dict[str, Any], generated_at: str) -> str:
    st = rec.get("stats") or {}
    lines = [
        f"# Phân tích — {rec.get('title_vn')}",
        "",
        f"> `{rec.get('book_id')}` · {rec.get('title_han') or '—'}  ",
        f"> Sinh: {generated_at}",
        "",
        "## 1. Nhận diện",
        "",
        f"| Trường | Giá trị |",
        f"|--------|---------|",
        f"| File | `{rec.get('docx')}` |",
        f"| Họ (`clan_key`) | `{rec.get('clan_key')}` |",
        f"| Ký hiệu | {rec.get('catalog_code') or '—'} |",
        f"| Năm gốc / năm dịch | {rec.get('year_source') or '—'} / {rec.get('year_translate') or '—'} |",
        f"| Ngôn ngữ Word | {rec.get('language')} |",
        f"| Loại (sơ bộ) | {', '.join(rec.get('loai') or []) or '—'} |",
        f"| Tag bố cục | {', '.join(rec.get('layout_tags') or []) or '—'} |",
        f"| Dung lượng | {_fmt(rec.get('bytes'))} byte |",
        "",
        rec.get("loai_guess") or rec.get("notes") or "",
        "",
        "## 2. Thống kê văn bản",
        "",
        "| Chỉ số | Giá trị |",
        "|--------|---------|",
        f"| Trang Word (`app.xml`) | {_fmt(st.get('word_pages'))} |",
        f"| Từ (Word) | {_fmt(st.get('word_words'))} |",
        f"| Đoạn lấy được | {_fmt(st.get('paras'))} |",
        f"| Ký tự (ghép đoạn) | {_fmt(st.get('chars'))} |",
        f"| Chữ Hán/Nôm (CJK) | {_fmt(st.get('cjk_chars'))} |",
        f"| CJK khác nhau | {_fmt(st.get('unique_cjk'))} |",
        f"| Tỉ lệ CJK | {_fmt(st.get('cjk_ratio'))} |",
        "",
        "## 3. Bố cục trong file",
        "",
        "| Phần | Đoạn | Ký tự |",
        "|------|------|-------|",
    ]
    for sec in rec.get("sections") or []:
        lines.append(f"| {sec.get('title')} | {_fmt(sec.get('n_paras'))} | {_fmt(sec.get('chars'))} |")
    lines += ["", "## 4. Nội dung phả hệ", ""]
    for item in rec.get("noi_dung") or [rec.get("notes")]:
        if item:
            lines.append(f"- {item}")
    lines += ["", "## 5. Địa danh", ""]
    for item in rec.get("dia_danh") or []:
        lines.append(f"- {item}")
    if not rec.get("dia_danh"):
        lines.append("- (chưa tách địa danh)")
    lines += ["", "## 6. Phù hợp pipeline", ""]
    for item in rec.get("pipeline") or []:
        lines.append(f"- {item}")
    lines += ["", "## 7. Hạn chế", ""]
    for item in rec.get("han_che") or []:
        lines.append(f"- {item}")
    lines += [
        "",
        "## 8. Đường dẫn",
        "",
        f"- Viewer: [`data/00_raw/hannom/books/{rec.get('book_id')}.html`](../../hannom/books/{rec.get('book_id')}.html)",
        f"- Toàn văn Markdown: [`{rec.get('book_id')}-toan-van.md`](./{rec.get('book_id')}-toan-van.md)",
        "- Catalog: `data/00_raw/hannom/books_catalog.json`",
        "",
    ]
    return "\n".join(lines)


def render_overview_md(records: list[dict[str, Any]], generated_at: str) -> str:
    lines = [
        "# Thống kê Word Hán-Nôm — 24/08/2026",
        "",
        f"> Thư mục `data/00_raw/du_lieu_han_nom_moi/24_8_2026/` · {generated_at}",
        "",
        "Ba file là **bản dịch / phiên âm Quốc ngữ** (một cuốn kèm chữ Hán), không phải ảnh scan. Catalog: `source=local_docx`, `kind=gia_pha_dich`.",
        "",
        "## Bảng so sánh",
        "",
        "| book_id | Họ | Trang Word | Đoạn | Ký tự | CJK | Năm gốc | Năm dịch | Phân tích |",
        "|---------|----|------------|------|-------|-----|---------|----------|-----------|",
    ]
    for rec in records:
        st = rec.get("stats") or {}
        lines.append(
            f"| `{rec.get('book_id')}` | `{rec.get('clan_key')}` | {_fmt(st.get('word_pages'))} | "
            f"{_fmt(st.get('paras'))} | {_fmt(st.get('chars'))} | {_fmt(st.get('cjk_chars'))} | "
            f"{rec.get('year_source') or '—'} | {rec.get('year_translate') or '—'} | "
            f"[{rec.get('book_id')}.md](./{rec.get('book_id')}.md) · "
            f"[toàn văn](./{rec.get('book_id')}-toan-van.md) |"
        )
    lines += [
        "",
        "## Cộng lô",
        "",
    ]
    pages = sum(int((r.get("stats") or {}).get("word_pages") or 0) for r in records)
    paras = sum(int((r.get("stats") or {}).get("paras") or 0) for r in records)
    chars = sum(int((r.get("stats") or {}).get("chars") or 0) for r in records)
    cjk = sum(int((r.get("stats") or {}).get("cjk_chars") or 0) for r in records)
    lines += [
        f"- **{len(records)} cuốn** · **{pages} trang Word** · **{paras} đoạn** · **{chars} ký tự** · **{cjk} CJK** (gần hết nằm ở Gia phả Nguyễn Văn).",
        "- Không OCR lô này. Extract cây: Phạm (phả ký 4 đời + tách phó ý); Nguyễn Văn (giỗ/chi); Trần (đời 1–5 và 12–16, không ép đời 6–10).",
        "",
        "Viewer: [data/00_raw/hannom/index.html](../../hannom/index.html)",
        "",
    ]
    return "\n".join(lines)


def render_fulltext_md(book: dict[str, Any], sections: list[dict[str, Any]], generated_at: str) -> str:
    bid = book.get("book_id") or ""
    lines = [
        f"# {book.get('title_vn') or bid}",
        "",
        f"> `{bid}` · {book.get('title_han') or '—'}  ",
        f"> Nguồn: `{(book.get('paths') or {}).get('docx') or ''}` · xuất {generated_at}",
        "",
        f"Phân tích: [{bid}.md](./{bid}.md)",
        "",
        "## Mục lục",
        "",
    ]
    for i, sec in enumerate(sections, 1):
        title = sec.get("title") or f"Phần {i}"
        slug = title.lower().replace(" ", "-").replace(".", "").replace("—", "-")
        lines.append(f"{i}. [{title}](#{slug})")
    lines.append("")
    for sec in sections:
        title = sec.get("title") or "Phần"
        lines += ["", f"## {title}", ""]
        text = (sec.get("text") or "").strip()
        if text:
            lines.append(text)
        else:
            lines.append("*(trống)*")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_docx_analyses(
    repo: Path,
    books: list[dict[str, Any]],
    load_docx_text,
) -> list[dict[str, Any]]:
    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    folder = repo / "data/00_raw/du_lieu_han_nom_moi/24_8_2026"
    folder.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for book in books:
        if book.get("source") != "local_docx":
            continue
        payload = load_docx_text(book, repo) or {"sections": []}
        rec = analysis_record(book, payload.get("sections") or [])
        records.append(rec)
        out = folder / f"{book['book_id']}.md"
        out.write_text(render_analysis_md(rec, generated_at) + "\n", encoding="utf-8")
        book.setdefault("paths", {})["analysis"] = out.relative_to(repo).as_posix()
        print(f"  analysis → {out.relative_to(repo)}")
        full = folder / f"{book['book_id']}-toan-van.md"
        full.write_text(
            render_fulltext_md(book, payload.get("sections") or [], generated_at),
            encoding="utf-8",
        )
        book["paths"]["fulltext"] = full.relative_to(repo).as_posix()
        print(f"  fulltext → {full.relative_to(repo)}")
    overview = folder / "thong_ke.md"
    overview.write_text(render_overview_md(records, generated_at) + "\n", encoding="utf-8")
    print(f"  analysis → {overview.relative_to(repo)}")
    return records
