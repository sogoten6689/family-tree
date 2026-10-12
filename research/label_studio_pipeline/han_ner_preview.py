"""Tạo một trang HTML tĩnh để LƯỚT XEM nhanh nhãn NER máy Hán: chữ Hán tô màu theo loại thực thể, kèm quan hệ và cờ nghi ngờ.

Không cần Label Studio, không gọi mạng. Mở tệp HTML bằng trình duyệt.

    python -m label_studio_pipeline.han_ner_preview --gold-dir <han_llm_trial/gold> --out preview.html [--held-out held_out.json] [--n 12]
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from label_studio_pipeline.han_review_queue import flags_for

COLORS = {"PER_NAME": "#ffd8a8", "GENERATION": "#d0bfff", "DATE": "#a5d8ff", "ORDER": "#b2f2bb", "LOC": "#ffc9c9"}
LABEL_VI = {"PER_NAME": "Tên người", "GENERATION": "Đời", "DATE": "Ngày tháng", "ORDER": "Thứ tự con", "LOC": "Địa danh"}
REL_VI = {"FATHER_OF": "là cha của", "MOTHER_OF": "là mẹ của", "SPOUSE": "là vợ/chồng của"}


def render_text(doc: Dict[str, Any]) -> str:
    text, out, cursor = doc["text"], [], 0
    for e in sorted(doc["entities"], key=lambda e: e["start"]):
        if e["start"] < cursor:
            continue
        out.append(html.escape(text[cursor : e["start"]]))
        out.append(f'<mark class="e" style="background:{COLORS.get(e["label"], "#eee")}" title="{LABEL_VI.get(e["label"], e["label"])}">{html.escape(text[e["start"] : e["end"]])}<sup>{LABEL_VI.get(e["label"], e["label"])}</sup></mark>')
        cursor = e["end"]
    out.append(html.escape(text[cursor:]))
    return "".join(out).replace("\n", "<br>")


def render_card(doc: Dict[str, Any], flags: List[str]) -> str:
    ents = doc["entities"]
    rels = "".join(
        f"<li>{html.escape(ents[r['head']]['text'])} <i>{REL_VI.get(r['type'], r['type'])}</i> {html.escape(ents[r['tail']]['text'])}</li>"
        for r in doc["relations"]
        if 0 <= r["head"] < len(ents) and 0 <= r["tail"] < len(ents)
    )
    counts = ", ".join(f"{LABEL_VI[k]} {sum(1 for e in ents if e['label'] == k)}" for k in COLORS if any(e["label"] == k for e in ents))
    flag_html = "".join(f'<span class="flag">{html.escape(f)}</span>' for f in flags)
    p = doc["provenance"]
    return (
        f'<section class="card"><h3>{html.escape(doc["doc_id"])} <small>(tài liệu #{p["scan_id"]}, trang {p["page_number"]})</small> {flag_html}</h3>'
        f'<div class="han">{render_text(doc)}</div><p class="meta">{len(ents)} thực thể: {counts or "—"}</p>'
        + (f"<p class='meta'>Quan hệ ({len(doc['relations'])}):</p><ul>{rels}</ul>" if rels else "<p class='meta'>Không có quan hệ.</p>")
        + "</section>"
    )


def pick(docs: List[Dict[str, Any]], held: set, n: int) -> List[tuple]:
    rows = [(d, flags_for(d, None, d["doc_id"] in held)) for d in docs]
    test = [r for r in rows if "tap_test" in r[1]][: max(1, n // 4)]
    flagged = [r for r in rows if r[1] and "tap_test" not in r[1]][: n // 3 + 1]
    clean = [r for r in rows if not r[1]]
    step = max(1, len(clean) // max(1, n - len(test) - len(flagged)))
    picked = test + flagged + clean[::step]
    return picked[:n]


def build(gold_dir: Path, out: Path, held_out: Optional[Path] = None, n: int = 12) -> int:
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(gold_dir.glob("*.json"))]
    held = set(json.loads(held_out.read_text(encoding="utf-8"))) if held_out and held_out.exists() else set()
    cards = [render_card(d, f) for d, f in pick(docs, held, n)]
    legend = "".join(f'<mark class="e" style="background:{c}">{LABEL_VI[k]}</mark> ' for k, c in COLORS.items())
    page = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Xem nhanh nhãn NER Hán</title><style>
body{{font-family:system-ui,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;line-height:1.6;background:#fff;color:#222}}
.han{{font-size:22px;line-height:2.1;font-family:"Noto Serif TC","Songti TC","PMingLiU",serif;border:1px solid #ddd;border-radius:8px;padding:12px;background:#fafafa}}
.e{{padding:1px 2px;border-radius:3px}} sup{{font-size:10px;color:#555;margin-left:2px}} .meta{{color:#555;font-size:14px;margin:6px 0}}
.card{{margin:28px 0}} h3{{margin:0 0 6px}} small{{color:#666;font-weight:400}} .flag{{background:#fff3bf;border:1px solid #fcc419;border-radius:10px;padding:0 8px;font-size:12px;margin-left:6px}}
.help{{background:#f1f3f5;border-radius:8px;padding:10px 14px}}
</style></head><body><h1>Xem nhanh nhãn NER chữ Hán</h1>
<div class="help"><b>Cách xem:</b> mỗi thẻ là một trang. Chữ Hán được tô màu theo loại thực thể (chú thích nhỏ ở góc trên). Chỉ cần nhìn: (1) màu có đúng loại không, (2) ranh giới có cắt thừa/thiếu chữ không, (3) quan hệ có đúng chiều không. Thẻ có nhãn vàng là trang nghi ngờ.<br>Chú thích màu: {legend}</div>
{''.join(cards)}</body></html>"""
    out.write_text(page, encoding="utf-8")
    return len(cards)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gold-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--held-out", type=Path)
    parser.add_argument("--n", type=int, default=12)
    args = parser.parse_args()
    print(f"đã tạo {build(args.gold_dir, args.out, args.held_out, args.n)} thẻ -> {args.out}")


if __name__ == "__main__":
    main()
