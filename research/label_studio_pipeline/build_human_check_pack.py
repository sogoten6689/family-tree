"""Build a human-check pack for machine labels (đo độ chính xác nhãn silver trên tập test).

Đầu vào: ``<labels-dir>/<tree_id>/gold.training.json`` (mặc định nhãn Gemini rà v2) cho các cây
``split=test`` trong ``stratified_sample.json``.

Đầu ra ``<output>/``:
- ``index.html`` + ``<tree_id>.html``: văn bản Phả ký tô màu theo nhãn + bảng quan hệ (chỉ để đọc).
- ``check.csv`` (UTF-8 BOM, mở bằng Excel): mỗi dòng là một entity / quan hệ máy gán. Người kiểm điền
  cột ``dung`` = ``Đ`` hoặc ``S``; nếu sai ghi bản đúng vào ``sua_thanh``. Nhãn máy bỏ sót thì thêm
  dòng mới với ``loai`` = ``thieu_entity`` / ``thieu_quan_he``.
  → precision = Đ / (Đ + S); recall ≈ Đ / (Đ + số dòng thiếu).
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from pathlib import Path

from label_studio_pipeline.corpus_store import load_json
from label_studio_pipeline.data_layout import DATA_ROOT, GOLD_STRATIFIED

DEFAULT_LABELS_DIR = DATA_ROOT / "01_interim" / "gemini_review" / "v2"
DEFAULT_OUTPUT = DATA_ROOT / "03_derived" / "llm_sft" / "v2" / "human_check"
CONTEXT_CHARS = 60

LABEL_COLORS = {
    "PER_NAME": "#FFA726",
    "GENERATION": "#66BB6A",
    "DATE": "#42A5F5",
    "ORDER": "#AB47BC",
    "LOC": "#EF5350",
}

CSV_COLUMNS = ["tree_id", "loai", "id", "nhan", "text_hoac_head", "tail", "ngu_canh", "dung", "sua_thanh", "ghi_chu"]


def _occurrences(text: str, needle: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in re.finditer(rf"(?<!\w){re.escape(needle)}(?!\w)", text)]


def _context(text: str, needle: str) -> str:
    spans = _occurrences(text, needle)
    if not spans:
        return ""
    start, end = spans[0]
    left = text[max(0, start - CONTEXT_CHARS) : start]
    right = text[end : end + CONTEXT_CHARS]
    return " ".join(f"…{left}[{text[start:end]}]{right}…".split())


def highlight(text: str, entities: list[dict]) -> str:
    """HTML of ``text`` with every occurrence of each entity marked; longer spans win overlaps."""
    marks: list[tuple[int, int, str]] = []
    taken = [False] * len(text)
    for ent in sorted(entities, key=lambda e: -len(e["text"])):
        for start, end in _occurrences(text, ent["text"]):
            if any(taken[start:end]):
                continue
            for i in range(start, end):
                taken[i] = True
            marks.append((start, end, ent["label"]))
    out, pos = [], 0
    for start, end, label in sorted(marks):
        out.append(html.escape(text[pos:start]))
        color = LABEL_COLORS.get(label, "#BDBDBD")
        out.append(
            f'<mark style="background:{color}33;border-bottom:2px solid {color}" title="{label}">'
            f"{html.escape(text[start:end])}<sub>{label}</sub></mark>"
        )
        pos = end
    out.append(html.escape(text[pos:]))
    return "".join(out)


PAGE_CSS = """
body{font:15px/1.6 system-ui,sans-serif;max-width:960px;margin:24px auto;padding:0 16px;color:#222;background:#fff}
pre{white-space:pre-wrap;font:inherit}
sub{font-size:9px;color:#555;margin-left:2px}
table{border-collapse:collapse;width:100%;margin:12px 0}
td,th{border:1px solid #ddd;padding:4px 8px;text-align:left;vertical-align:top}
.legend span{display:inline-block;margin-right:12px;padding:0 6px;border-radius:3px}
"""


def _legend() -> str:
    return '<p class="legend">' + "".join(
        f'<span style="background:{c}33;border-bottom:2px solid {c}">{lbl}</span>' for lbl, c in LABEL_COLORS.items()
    ) + "</p>"


def build_tree_page(doc: dict, rel_rows: list[dict]) -> str:
    rows = "".join(
        f"<tr><td>{r['id']}</td><td>{html.escape(r['nhan'])}</td><td>{html.escape(r['text_hoac_head'])}</td>"
        f"<td>{html.escape(r['tail'])}</td></tr>"
        for r in rel_rows
    ) or '<tr><td colspan="4">(không có quan hệ)</td></tr>'
    title = html.escape(f"{doc.get('tree_id')} — {doc.get('title', '')}")
    return (
        f"<!doctype html><meta charset='utf-8'><title>{title}</title><style>{PAGE_CSS}</style>"
        f"<p><a href='index.html'>← Danh sách</a></p><h1>{title}</h1>"
        f"<p>Nguồn nhãn: <code>{html.escape(str(doc.get('source', '')))}</code> · "
        f"<a href='{html.escape(str(doc.get('source_url', '')))}'>bản gốc</a></p>"
        f"{_legend()}<h2>Quan hệ</h2><table><tr><th>id</th><th>loại</th><th>head</th><th>tail</th></tr>{rows}</table>"
        f"<h2>Văn bản</h2><pre>{highlight(doc['text'], doc.get('entities') or [])}</pre>"
    )


def build_index(summaries: list[dict]) -> str:
    rows = "".join(
        f"<tr><td><a href='{s['tree_id']}.html'>{s['tree_id']}</a></td><td>{html.escape(s['title'])}</td>"
        f"<td>{s['entities']}</td><td>{s['relations']}</td><td>{s['chars']}</td></tr>"
        for s in summaries
    )
    return (
        f"<!doctype html><meta charset='utf-8'><title>Kiểm nhãn tập test</title><style>{PAGE_CSS}</style>"
        "<h1>Kiểm nhãn tập test</h1>"
        "<ol><li>Mở từng cây bên dưới để đọc văn bản đã tô màu nhãn.</li>"
        "<li>Mở <code>check.csv</code> bằng Excel. Mỗi dòng là một nhãn máy gán: điền cột <b>dung</b> = "
        "<b>Đ</b> (đúng) hoặc <b>S</b> (sai); sai thì ghi bản đúng ở <b>sua_thanh</b>.</li>"
        "<li>Nhãn máy <b>bỏ sót</b>: thêm dòng mới, <b>loai</b> = <code>thieu_entity</code> hoặc "
        "<code>thieu_quan_he</code>.</li>"
        "<li>Tiêu chí theo <code>research/label_studio_pipeline/ENTITY_RELATIONSHIP_LIST.md</code> "
        "(PER_NAME không gộp danh xưng; quan hệ chỉ khi văn bản nói rõ).</li></ol>"
        f"{_legend()}<table><tr><th>tree</th><th>dòng họ</th><th>entity</th><th>quan hệ</th><th>ký tự</th></tr>"
        f"{rows}</table>"
    )


def build_pack(*, labels_dir: Path, stratified_path: Path, output: Path, tree_ids: list[int] | None) -> dict:
    if not tree_ids:
        stratified = load_json(stratified_path) or {}
        tree_ids = [int(d["tree_id"]) for d in stratified.get("documents", []) if d.get("split") == "test"]
    output.mkdir(parents=True, exist_ok=True)
    csv_rows: list[dict] = []
    summaries: list[dict] = []
    for tree_id in tree_ids:
        doc = load_json(labels_dir / str(tree_id) / "gold.training.json")
        if doc is None:
            raise FileNotFoundError(f"missing labels for tree {tree_id} in {labels_dir}")
        text, entities, relations = doc["text"], doc.get("entities") or [], doc.get("relations") or []
        for i, ent in enumerate(entities):
            csv_rows.append(
                {"tree_id": tree_id, "loai": "entity", "id": f"E{i}", "nhan": ent["label"],
                 "text_hoac_head": ent["text"], "tail": "", "ngu_canh": _context(text, ent["text"])}
            )
        rel_rows = []
        for i, rel in enumerate(relations):
            head, tail = entities[rel["head"]]["text"], entities[rel["tail"]]["text"]
            row = {"tree_id": tree_id, "loai": "quan_he", "id": f"R{i}", "nhan": rel["type"],
                   "text_hoac_head": head, "tail": tail, "ngu_canh": _context(text, head)}
            rel_rows.append(row)
            csv_rows.append(row)
        (output / f"{tree_id}.html").write_text(build_tree_page(doc, rel_rows), encoding="utf-8")
        summaries.append({"tree_id": tree_id, "title": str(doc.get("title", "")), "entities": len(entities),
                          "relations": len(relations), "chars": len(text)})
    (output / "index.html").write_text(build_index(summaries), encoding="utf-8")
    with (output / "check.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in csv_rows:
            writer.writerow({col: row.get(col, "") for col in CSV_COLUMNS})
    return {"output": str(output), "trees": summaries, "csv_rows": len(csv_rows)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build an HTML + CSV pack for humans to check machine labels.")
    parser.add_argument("--labels-dir", type=Path, default=DEFAULT_LABELS_DIR)
    parser.add_argument("--stratified", type=Path, default=GOLD_STRATIFIED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--tree-id", type=int, action="append", dest="tree_ids")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = build_pack(
        labels_dir=args.labels_dir, stratified_path=args.stratified, output=args.output, tree_ids=args.tree_ids
    )
    json.dump(summary, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
