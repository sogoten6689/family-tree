"""Làm sạch ``gold.training.json`` TRƯỚC khi huấn luyện — không phá huỷ: ghi ra thư mục mới, không sửa bản gốc.

Mỗi bước là một hàm riêng, xác định (cùng đầu vào → cùng đầu ra), có đếm và ghi vào ``clean_report.json``:

C1  Bỏ ký tự vô hình (zero-width, điều khiển), CRLF → LF, NBSP → dấu cách, chuẩn hoá NFC.
    Dời offset của mọi entity theo đúng phần văn bản đã đổi (không bao giờ "đoán lại" offset).
C2  Cắt khoảng trắng và dấu câu thừa ở mép entity (``" Nguyễn"``, ``"Hà."``); entity rỗng sau khi cắt bị bỏ.
C3  Bỏ entity chồng nhau / trùng span (giữ cái bắt đầu sớm hơn, dài hơn); quan hệ trỏ vào entity đã bỏ cũng bị bỏ.
C4  Kiểm tra sau cùng: ``text[start:end] == entity["text"]`` cho MỌI entity, chỉ số quan hệ hợp lệ. Vi phạm = lỗi cứng.

Chỉ GẮN CỜ (không tự sửa) những thứ cần quyết định của con người/thầy:
  - entity chứa xuống dòng (có thể là tên vắt qua hai cột OCR hoặc lỗi bôi);
  - tài liệu trùng văn bản (``duplicate_of``) và đoạn dài dùng chung nhiều tài liệu (nguy cơ rò rỉ train/test).

Chạy (từ ``research/``)::

    python -m label_studio_pipeline.clean_gold --input-dir <gold dir> --output-dir <dir mới>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Callable, Iterable, Optional

CLEAN_VERSION = 1
_ZERO_WIDTH = {"​", "‌", "‍", "⁠", "﻿"}
_EDGE_PUNCT = ".,;:!?)([]{}\"'“”‘’"


# --------------------------------------------------------------------------- C1


def _clean_segment(segment: str, counters: Counter) -> str:
    out = []
    for ch in segment:
        if ch in _ZERO_WIDTH:
            counters["c1_zero_width_removed"] += 1
            continue
        if unicodedata.category(ch) == "Cc" and ch not in "\n\t\r":
            counters["c1_control_removed"] += 1
            continue
        if ch == " ":
            counters["c1_nbsp_replaced"] += 1
            ch = " "
        out.append(ch)
    cleaned = "".join(out)
    if "\r\n" in cleaned:
        counters["c1_crlf_replaced"] += cleaned.count("\r\n")
        cleaned = cleaned.replace("\r\n", "\n")
    cleaned = cleaned.replace("\r", "\n")
    nfc = unicodedata.normalize("NFC", cleaned)
    if nfc != cleaned:
        counters["c1_nfc_changed_segments"] += 1
    return nfc


def transform_text_and_entities(text: str, entities: list[dict], counters: Counter) -> tuple[str, list[dict]]:
    """Áp C1 lên văn bản mà vẫn giữ đúng offset: cắt văn bản tại MỌI ranh giới entity, làm sạch từng đoạn rồi
    ghép lại; offset mới = tổng độ dài các đoạn đã làm sạch đứng trước."""
    cuts = sorted({0, len(text), *[e["start"] for e in entities], *[e["end"] for e in entities]})
    cuts = [c for c in cuts if 0 <= c <= len(text)]
    new_pos: dict[int, int] = {}
    pieces: list[str] = []
    cursor = 0
    for a, b in zip(cuts, cuts[1:]):
        new_pos[a] = cursor
        piece = _clean_segment(text[a:b], counters)
        pieces.append(piece)
        cursor += len(piece)
    new_pos[cuts[-1]] = cursor
    new_text = "".join(pieces)
    new_entities = []
    for e in entities:
        ne = dict(e)
        ne["start"], ne["end"] = new_pos[e["start"]], new_pos[e["end"]]
        ne["text"] = new_text[ne["start"]:ne["end"]]
        new_entities.append(ne)
    return new_text, new_entities


# --------------------------------------------------------------------------- C2


def trim_entities(text: str, entities: list[dict], counters: Counter) -> list[tuple[int, dict]]:
    """Trả về [(chỉ số cũ, entity đã cắt)] cho entity còn lại; entity rỗng sau khi cắt bị bỏ."""
    kept = []
    for idx, e in enumerate(entities):
        start, end = e["start"], e["end"]
        while start < end and (text[start].isspace() or text[start] in "([{\"'“‘"):
            start += 1
        while end > start and (text[end - 1].isspace() or text[end - 1] in _EDGE_PUNCT):
            end -= 1
        if start >= end:
            counters["c2_entity_empty_dropped"] += 1
            continue
        if (start, end) != (e["start"], e["end"]):
            counters["c2_entity_trimmed"] += 1
        ne = dict(e)
        ne["start"], ne["end"], ne["text"] = start, end, text[start:end]
        kept.append((idx, ne))
    return kept


# --------------------------------------------------------------------------- C3


def drop_overlaps(indexed: list[tuple[int, dict]], counters: Counter) -> list[tuple[int, dict]]:
    ordered = sorted(indexed, key=lambda it: (it[1]["start"], -(it[1]["end"] - it[1]["start"])))
    kept, last_end = [], -1
    for old_idx, e in ordered:
        if e["start"] < last_end:
            counters["c3_overlap_or_duplicate_dropped"] += 1
            continue
        kept.append((old_idx, e))
        last_end = e["end"]
    return kept


def remap_relations(relations: list[dict], old_to_new: dict[int, int], counters: Counter) -> list[dict]:
    out = []
    for rel in relations:
        h, t = old_to_new.get(rel.get("head")), old_to_new.get(rel.get("tail"))
        if h is None or t is None:
            counters["c3_relation_dropped_missing_entity"] += 1
            continue
        out.append({**rel, "head": h, "tail": t})
    return out


# --------------------------------------------------------------------------- C4


def verify(doc: dict) -> list[str]:
    problems = []
    text, entities = doc["text"], doc["entities"]
    for i, e in enumerate(entities):
        if not (0 <= e["start"] < e["end"] <= len(text)) or text[e["start"]:e["end"]] != e["text"]:
            problems.append(f"entity {i}: text[{e['start']}:{e['end']}] != {e['text']!r}")
    for j, rel in enumerate(doc.get("relations") or []):
        if not (0 <= rel["head"] < len(entities) and 0 <= rel["tail"] < len(entities)):
            problems.append(f"relation {j}: chỉ số ngoài phạm vi")
    return problems


# --------------------------------------------------------------------------- tổng hợp


def clean_document(doc: dict) -> tuple[dict, Counter]:
    counters: Counter = Counter()
    all_entities = [dict(e) for e in (doc.get("entities") or [])]
    # offset hỏng từ đầu thì không dời được một cách đáng tin: loại khỏi đầu ra, đếm và đánh dấu lỗi cứng
    entities = [e for e in all_entities if 0 <= e["start"] < e["end"] <= len(doc["text"])]
    bad = len(all_entities) - len(entities)
    if bad:
        counters["input_entity_out_of_range"] += bad
        counters["verify_failed_docs"] += 1
    text, entities = transform_text_and_entities(doc["text"], entities, counters)
    indexed = trim_entities(text, entities, counters)
    indexed = drop_overlaps(indexed, counters)
    kept_orig = [i for i, e in enumerate(all_entities) if 0 <= e["start"] < e["end"] <= len(doc["text"])]
    old_to_new = {kept_orig[old]: new for new, (old, _) in enumerate(indexed)}
    new_entities = [e for _, e in indexed]
    new_relations = remap_relations(doc.get("relations") or [], old_to_new, counters)
    counters["entities_in"] += len(doc.get("entities") or [])
    counters["entities_out"] += len(new_entities)
    counters["relations_in"] += len(doc.get("relations") or [])
    counters["relations_out"] += len(new_relations)
    counters["flag_entity_contains_newline"] += sum(1 for e in new_entities if "\n" in e["text"])

    cleaned = {**doc, "text": text, "entities": new_entities, "relations": new_relations}
    problems = verify(cleaned)
    cleaned["cleaning"] = {"version": CLEAN_VERSION, "steps": ["C1", "C2", "C3", "C4"],
                           "changes": {k: v for k, v in counters.items() if v and not k.startswith("entities_") and not k.startswith("relations_")}}
    if bad:
        problems.append(f"{bad} entity ngoài phạm vi văn bản ở đầu vào (đã loại khỏi đầu ra)")
    if problems:
        if not bad:
            counters["verify_failed_docs"] += 1
        cleaned["cleaning"]["verify_problems"] = problems
    return cleaned, counters


def find_duplicates(docs: dict[int, dict], min_paragraph_chars: int = 40) -> dict:
    by_hash: dict[str, list[int]] = {}
    para_docs: dict[str, set[int]] = {}
    for tree_id, doc in docs.items():
        by_hash.setdefault(hashlib.sha1(re.sub(r"\s+", " ", doc["text"]).strip().encode()).hexdigest(), []).append(tree_id)
        for line in doc["text"].splitlines():
            line = line.strip()
            if len(line) >= min_paragraph_chars:
                para_docs.setdefault(hashlib.sha1(line.encode()).hexdigest(), set()).add(tree_id)
    duplicate_of = {ids[i]: ids[0] for ids in by_hash.values() if len(ids) > 1 for i in range(1, len(ids))}
    shared_pairs: Counter = Counter()
    for ids in para_docs.values():
        if len(ids) > 1:
            ordered = sorted(ids)
            for i, a in enumerate(ordered):
                for b in ordered[i + 1:]:
                    shared_pairs[(a, b)] += 1
    return {"duplicate_of": {str(k): v for k, v in duplicate_of.items()},
            "doc_pairs_sharing_paragraphs": [{"docs": list(pair), "shared_paragraphs": n} for pair, n in shared_pairs.most_common(10)]}


def load_dir(base: Path) -> dict[int, dict]:
    docs = {}
    for sub in sorted(p for p in base.iterdir() if p.is_dir() and p.name.isdigit()):
        path = sub / "gold.training.json"
        if path.exists():
            docs[int(sub.name)] = json.loads(path.read_text(encoding="utf-8"))
    return docs


def clean_directory(input_dir: Path, output_dir: Path, *, progress: Callable[[str], None] = print) -> dict:
    docs = load_dir(input_dir)
    total: Counter = Counter()
    per_doc: dict[str, dict] = {}
    cleaned_docs: dict[int, dict] = {}
    for tree_id, doc in docs.items():
        cleaned, counters = clean_document(doc)
        cleaned_docs[tree_id] = cleaned
        total.update(counters)
        changes = {k: v for k, v in counters.items() if v and k.startswith(("c1_", "c2_", "c3_", "flag_", "input_", "verify"))}
        if changes:
            per_doc[str(tree_id)] = changes
        out = output_dir / str(tree_id)
        out.mkdir(parents=True, exist_ok=True)
        (out / "gold.training.json").write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")
    dup = find_duplicates(cleaned_docs)
    report = {
        "version": CLEAN_VERSION,
        "input_dir": str(input_dir),
        "docs": len(docs),
        "totals": dict(total),
        "docs_with_changes_or_flags": per_doc,
        **dup,
    }
    (output_dir / "clean_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    progress(f"{len(docs)} tài liệu → {output_dir}")
    return report


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.output_dir.resolve() == args.input_dir.resolve():
        parser.error("--output-dir phải khác --input-dir (không ghi đè dữ liệu gốc)")
    report = clean_directory(args.input_dir, args.output_dir)
    t = report["totals"]
    print(f"thực thể {t.get('entities_in', 0)} → {t.get('entities_out', 0)}; quan hệ {t.get('relations_in', 0)} → {t.get('relations_out', 0)}; "
          f"tài liệu trùng: {len(report['duplicate_of'])}; lỗi kiểm tra cuối: {t.get('verify_failed_docs', 0)}")
    return 1 if t.get("verify_failed_docs") else 0


if __name__ == "__main__":
    sys.exit(main())
