"""Dựng mẫu pilot gán nhãn NER cho chữ Hán từ các trang đã OCR trên web.

Đầu vào: TSV 4 cột `scan_id<TAB>page_number<TAB>hannom_text (xuống dòng viết là \\n)<TAB>ocr_vote_meta (JSON)`,
xuất từ bảng gia_pha_page/gia_pha_page_content (version hiện tại). Đầu ra (thư mục mới, không đụng dữ liệu cũ):
  tasks.json   — nhiệm vụ Label Studio (data.text, doc_id, page_number, lang="han", provenance)
  manifest.csv — từng trang được chọn: số chữ Hán, điểm đồng thuận OCR, cờ ký tự ngoài BMP
  report.json — tổng kết: số trang, số ký tự, số sách, rủi ro offset

Chọn trang (xác định, không ngẫu nhiên): mỗi sách tối đa `per_doc` trang, ưu tiên điểm đồng thuận OCR cao
(trung bình `similarity_to_others` của các engine) và đủ dài; dừng khi đạt `target_chars`.
Không gọi dịch vụ ngoài, không tốn tiền.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

HAN_RE = re.compile(r"[㐀-鿿\U00020000-\U0002ffff]")
NON_BMP_RE = re.compile(r"[\U00010000-\U0010ffff]")


def han_count(text: str) -> int:
    return len(HAN_RE.findall(text))


def has_non_bmp(text: str) -> bool:
    return bool(NON_BMP_RE.search(text))


def agreement_score(meta: Optional[Dict[str, Any]]) -> Optional[float]:
    """Trung bình độ giống nhau giữa các engine OCR của trang (0–1); None nếu không có dữ liệu."""
    engines = (meta or {}).get("engines") or {}
    values = [
        info["similarity_to_others"]
        for info in engines.values()
        if isinstance(info, dict) and isinstance(info.get("similarity_to_others"), (int, float))
    ]
    return sum(values) / len(values) if values else None


def utf16_to_codepoint(text: str, utf16_offset: int) -> int:
    """Đổi offset đếm theo đơn vị UTF-16 (trình duyệt/Label Studio) sang offset code point (Python).
    Ký tự ngoài BMP chiếm 2 đơn vị UTF-16 nhưng chỉ 1 code point."""
    units = 0
    for index, char in enumerate(text):
        if units >= utf16_offset:
            return index
        units += 2 if ord(char) > 0xFFFF else 1
    return len(text)


def codepoint_to_utf16(text: str, codepoint_offset: int) -> int:
    return sum(2 if ord(char) > 0xFFFF else 1 for char in text[:codepoint_offset])


def read_pages(lines: Iterable[str]) -> List[Dict[str, Any]]:
    pages = []
    for line in lines:
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            continue
        try:
            meta = json.loads(parts[3]) if len(parts) > 3 and parts[3] else None
        except json.JSONDecodeError:
            meta = None
        text = parts[2].replace("\\n", "\n").strip()
        pages.append({"scan_id": int(parts[0]), "page_number": int(parts[1]), "text": text, "meta": meta})
    return pages


def select_pages(
    pages: List[Dict[str, Any]],
    *,
    per_doc: int = 6,
    target_chars: int = 25000,
    min_han: int = 150,
    exclude_docs: Iterable[int] = (),
) -> List[Dict[str, Any]]:
    skip = set(exclude_docs)
    pages = [p for p in pages if p["scan_id"] not in skip]
    by_doc: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for page in pages:
        page["han"] = han_count(page["text"])
        page["agreement"] = agreement_score(page["meta"])
        if page["han"] >= min_han:
            by_doc[page["scan_id"]].append(page)
    # Trong mỗi sách: điểm đồng thuận cao trước (thiếu dữ liệu xếp cuối), rồi trang dài hơn, rồi số trang nhỏ.
    ranked = {
        doc: sorted(items, key=lambda p: (-(p["agreement"] if p["agreement"] is not None else -1), -p["han"], p["page_number"]))[:per_doc]
        for doc, items in by_doc.items()
    }
    chosen: List[Dict[str, Any]] = []
    total = 0
    # Vòng tròn qua các sách (mỗi lượt 1 trang/sách) để mẫu trải đều, không dồn vào vài sách.
    for rank in range(per_doc):
        for doc in sorted(ranked):
            if rank < len(ranked[doc]) and total < target_chars:
                page = ranked[doc][rank]
                chosen.append(page)
                total += page["han"]
    return sorted(chosen, key=lambda p: (p["scan_id"], p["page_number"]))


def to_task(page: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "data": {
            "text": page["text"],
            "doc_id": f"han-{page['scan_id']}-p{page['page_number']:03d}",
            "scan_id": page["scan_id"],
            "page_number": page["page_number"],
            "lang": "han",
            "provenance": {"scan_id": page["scan_id"], "page_number": page["page_number"], "source": "gia_pha_page_content.current_version"},
            "non_bmp": has_non_bmp(page["text"]),
        }
    }


def build(pages: List[Dict[str, Any]], out_dir: Path, *, per_doc: int = 6, target_chars: int = 25000, min_han: int = 150, exclude_docs: Iterable[int] = ()) -> Dict[str, Any]:
    chosen = select_pages(pages, per_doc=per_doc, target_chars=target_chars, min_han=min_han, exclude_docs=exclude_docs)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tasks.json").write_text(json.dumps([to_task(p) for p in chosen], ensure_ascii=False, indent=1), encoding="utf-8")
    with (out_dir / "manifest.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["scan_id", "page_number", "han_chars", "agreement", "non_bmp"])
        for p in chosen:
            writer.writerow([p["scan_id"], p["page_number"], p["han"], "" if p["agreement"] is None else round(p["agreement"], 3), int(has_non_bmp(p["text"]))])
    agreements = [p["agreement"] for p in chosen if p["agreement"] is not None]
    report = {
        "pages_available": len(pages),
        "pages_selected": len(chosen),
        "docs_selected": len({p["scan_id"] for p in chosen}),
        "han_chars_selected": sum(p["han"] for p in chosen),
        "mean_agreement": round(sum(agreements) / len(agreements), 3) if agreements else None,
        "pages_with_non_bmp": sum(1 for p in chosen if has_non_bmp(p["text"])),
        "params": {"per_doc": per_doc, "target_chars": target_chars, "min_han": min_han, "exclude_docs": sorted(set(exclude_docs))},
    }
    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pages_tsv", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--per-doc", type=int, default=6)
    parser.add_argument("--target-chars", type=int, default=25000)
    parser.add_argument("--min-han", type=int, default=150)
    parser.add_argument("--exclude-docs", type=int, nargs="*", default=[], help="scan_id bỏ qua (ví dụ bản hỗn hợp Việt–Hán)")
    args = parser.parse_args()
    with args.pages_tsv.open(encoding="utf-8") as fh:
        pages = read_pages(fh)
    print(json.dumps(build(pages, args.out, per_doc=args.per_doc, target_chars=args.target_chars, min_han=args.min_han, exclude_docs=args.exclude_docs), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
