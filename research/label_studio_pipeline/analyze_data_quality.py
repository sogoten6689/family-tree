"""Phân tích chất lượng dữ liệu NER/RE — chỉ ĐỌC, không sửa dữ liệu, không gọi API tốn tiền.

Bốn phần (mỗi phần trả lời một câu hỏi cụ thể trong kế hoạch tích hợp model):

1. ``silver_vs_human``  — nhãn máy (Gemini) khớp nhãn người đến đâu? (nhãn người là chuẩn)
2. ``regex_baseline``   — bộ trích xuất quy tắc hiện tại (FamilyExtractor) đạt F1 bao nhiêu so với nhãn người?
3. ``clean_checks``     — văn bản/nhãn quốc ngữ có lỗi "bẩn" nào cần làm sạch trước khi huấn luyện?
4. ``han_ocr_profile``  — văn bản Hán OCR (lớp ``l1_ocr``) bẩn/không chắc chắn đến mức nào?

Chạy (từ thư mục ``research/``)::

    python -m label_studio_pipeline.analyze_data_quality \
        --human-dir <v1_human> --silver-dir <gemini_review/v2> \
        --han-dataset <hannom-bilingual-dataset> --output <dir>

Lưu ý khi diễn giải: nhãn người trong Label Studio được tạo bằng cách SỬA nhãn Gemini gán trước, nên mức
khớp silver–human có thể bị đánh giá CAO hơn thực tế (người gán bị "neo" theo gợi ý máy).
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
from statistics import mean, median
from typing import Iterable, Optional

LABELS = ("PER_NAME", "GENERATION", "DATE", "ORDER", "LOC")
_ZERO_WIDTH = {"​", "‌", "‍", "⁠", "﻿"}
_PLACEHOLDERS = set("□〓○◯▢■●◆?？")
_TRAILING_PUNCT = tuple(".,;:!?)")


# --------------------------------------------------------------------------- số liệu


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4)}


def _overlap(a: dict, b: dict) -> float:
    inter = max(0, min(a["end"], b["end"]) - max(a["start"], b["start"]))
    union = max(a["end"], b["end"]) - min(a["start"], b["start"])
    return inter / union if union else 0.0


def compare_entities(reference: list[dict], predicted: list[dict], *, iou: float = 0.5) -> dict[str, Counter]:
    """So hai danh sách entity (chuẩn vs dự đoán) theo từng nhãn.

    ``strict``: khớp đúng (start, end, label). ``lenient``: cùng nhãn và IoU ≥ ``iou`` (mỗi entity chỉ ghép 1 lần).
    Trả về {"strict": Counter(tp,fp,fn theo "label:tp"...), "lenient": ...}.
    """
    out = {"strict": Counter(), "lenient": Counter()}
    ref_keys = {(e["start"], e["end"], e["label"]) for e in reference}
    pred_keys = {(e["start"], e["end"], e["label"]) for e in predicted}
    for label in LABELS:
        r = {k for k in ref_keys if k[2] == label}
        p = {k for k in pred_keys if k[2] == label}
        out["strict"][f"{label}:tp"] += len(r & p)
        out["strict"][f"{label}:fp"] += len(p - r)
        out["strict"][f"{label}:fn"] += len(r - p)

        used: set[int] = set()
        tp = 0
        ref_l = [e for e in reference if e["label"] == label]
        pred_l = [e for e in predicted if e["label"] == label]
        for pe in pred_l:
            best, best_i = 0.0, None
            for i, re_ in enumerate(ref_l):
                if i in used:
                    continue
                score = _overlap(pe, re_)
                if score > best:
                    best, best_i = score, i
            if best_i is not None and best >= iou:
                used.add(best_i)
                tp += 1
        out["lenient"][f"{label}:tp"] += tp
        out["lenient"][f"{label}:fp"] += len(pred_l) - tp
        out["lenient"][f"{label}:fn"] += len(ref_l) - tp
    return out


def summarize(counter: Counter) -> dict:
    """Từ Counter 'LABEL:tp/fp/fn' → bảng P/R/F1 theo nhãn + micro."""
    table = {}
    total = Counter()
    for label in LABELS:
        tp, fp, fn = counter[f"{label}:tp"], counter[f"{label}:fp"], counter[f"{label}:fn"]
        table[label] = prf(tp, fp, fn)
        total["tp"] += tp
        total["fp"] += fp
        total["fn"] += fn
    table["micro"] = prf(total["tp"], total["fp"], total["fn"])
    return table


# --------------------------------------------------------------------------- nạp dữ liệu


def load_docs(base: Path) -> dict[int, dict]:
    docs: dict[int, dict] = {}
    if not base.is_dir():
        return docs
    for sub in sorted(p for p in base.iterdir() if p.is_dir() and p.name.isdigit()):
        path = sub / "gold.training.json"
        if path.exists():
            docs[int(sub.name)] = json.loads(path.read_text(encoding="utf-8"))
    return docs


def norm_name(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip(" .,;:!?").casefold()


# --------------------------------------------------------------------------- 1. silver vs human


def silver_vs_human(human: dict[int, dict], silver: dict[int, dict]) -> dict:
    strict, lenient = Counter(), Counter()
    compared, text_differs, missing = 0, 0, 0
    for tree_id, h in human.items():
        s = silver.get(tree_id)
        if s is None:
            missing += 1
            continue
        if s["text"] != h["text"]:
            text_differs += 1  # offset của hai bên không so được với nhau
            continue
        cmp = compare_entities(h.get("entities") or [], s.get("entities") or [])
        strict.update(cmp["strict"])
        lenient.update(cmp["lenient"])
        compared += 1
    return {
        "docs_compared": compared,
        "docs_missing_silver": missing,
        "docs_text_differs_skipped": text_differs,
        "note": "người = chuẩn; nhãn người sinh ra bằng cách sửa nhãn máy nên mức khớp có thể bị đánh giá cao",
        "strict": summarize(strict),
        "lenient_iou50": summarize(lenient),
    }


# --------------------------------------------------------------------------- 2. baseline regex


def _relation_triples(doc: dict) -> set[tuple]:
    """Quan hệ người → bộ ba chuẩn hoá: parent_of(head,tail) có hướng; spouse_of không phân hướng."""
    entities = doc.get("entities") or []
    triples = set()
    for rel in doc.get("relations") or []:
        try:
            head, tail = norm_name(entities[rel["head"]]["text"]), norm_name(entities[rel["tail"]]["text"])
        except (IndexError, KeyError, TypeError):
            continue
        if rel["type"] in ("FATHER_OF", "MOTHER_OF"):
            triples.add(("parent_of", head, tail))
        elif rel["type"] == "SPOUSE":
            triples.add(("spouse_of", *sorted((head, tail))))
    return triples


def regex_triples(parsed: dict) -> tuple[set[str], set[tuple]]:
    names = {p["id"]: norm_name(p["full_name"]) for p in parsed["people"]}
    triples = set()
    for rel in parsed["relationships"]:
        head, tail = names.get(rel["from_id"]), names.get(rel["to_id"])
        if not head or not tail or head == tail:
            continue
        if rel["type"] == "parent_of":
            triples.add(("parent_of", head, tail))
        elif rel["type"] == "spouse_of":
            triples.add(("spouse_of", *sorted((head, tail))))
    return {n for n in names.values() if n}, triples


def regex_baseline(human: dict[int, dict], extractor_cls, *, max_docs: Optional[int] = None) -> dict:
    """Chạy bộ trích xuất quy tắc trên văn bản của các cây có nhãn người và so theo CHUỖI tên (không theo offset,
    vì bộ này không trả vị trí)."""
    pn, rel_all = Counter(), Counter()
    per_doc, errors = [], 0
    for n, (tree_id, doc) in enumerate(human.items()):
        if max_docs is not None and n >= max_docs:
            break
        try:
            parsed = extractor_cls().parse(doc["text"])
        except Exception:  # noqa: BLE001 — ghi nhận rồi bỏ qua tài liệu lỗi
            errors += 1
            continue
        pred_names, pred_rel = regex_triples(parsed)
        gold_names = {norm_name(e["text"]) for e in doc.get("entities") or [] if e["label"] == "PER_NAME"}
        gold_names.discard("")
        gold_rel = _relation_triples(doc)
        pn["tp"] += len(pred_names & gold_names)
        pn["fp"] += len(pred_names - gold_names)
        pn["fn"] += len(gold_names - pred_names)
        rel_all["tp"] += len(pred_rel & gold_rel)
        rel_all["fp"] += len(pred_rel - gold_rel)
        rel_all["fn"] += len(gold_rel - pred_rel)
        per_doc.append({"tree_id": tree_id, "gold_names": len(gold_names), "pred_names": len(pred_names),
                        "gold_relations": len(gold_rel), "pred_relations": len(pred_rel)})
    return {
        "docs": len(per_doc),
        "docs_errored": errors,
        "match": "so theo chuỗi tên đã chuẩn hoá (NFC, chữ thường, bỏ dấu câu đầu/cuối); không dùng offset",
        "person_names": prf(pn["tp"], pn["fp"], pn["fn"]),
        "relations": prf(rel_all["tp"], rel_all["fp"], rel_all["fn"]),
        "per_doc": per_doc,
    }


# --------------------------------------------------------------------------- 3. làm sạch


def clean_checks(docs: dict[int, dict]) -> dict:
    c: Counter = Counter()
    lengths, densities = [], []
    text_hash: dict[str, list[int]] = {}
    para_docs: dict[str, set[int]] = {}
    label_counts: Counter = Counter()
    for tree_id, doc in docs.items():
        text = doc["text"]
        c["docs"] += 1
        lengths.append(len(text))
        if unicodedata.normalize("NFC", text) != text:
            c["docs_not_nfc"] += 1
        c["zero_width_chars"] += sum(1 for ch in text if ch in _ZERO_WIDTH)
        c["control_chars"] += sum(1 for ch in text if unicodedata.category(ch) == "Cc" and ch not in "\n\t\r")
        c["nbsp_chars"] += text.count(" ")
        c["crlf_lines"] += text.count("\r\n")
        text_hash.setdefault(hashlib.sha1(re.sub(r"\s+", " ", text).strip().encode()).hexdigest(), []).append(tree_id)
        for line in text.splitlines():
            line = line.strip()
            if len(line) >= 40:
                para_docs.setdefault(hashlib.sha1(line.encode()).hexdigest(), set()).add(tree_id)

        entities = doc.get("entities") or []
        densities.append(1000 * len(entities) / max(len(text), 1))
        seen = set()
        for e in entities:
            label_counts[e["label"]] += 1
            et = e["text"]
            if et != et.strip():
                c["entity_edge_whitespace"] += 1
            if "\n" in et:
                c["entity_contains_newline"] += 1
            if et.strip().endswith(_TRAILING_PUNCT):
                c["entity_trailing_punct"] += 1
            if (e["start"], e["end"]) in seen:
                c["entity_duplicate_span"] += 1
            seen.add((e["start"], e["end"]))
            if e["label"] == "PER_NAME":
                words = et.split()
                if len(words) < 2:
                    c["per_name_single_word"] += 1
                if any(ch.isdigit() for ch in et):
                    c["per_name_has_digit"] += 1
                if words and words[0][:1].islower() and words[0].casefold() in {"ông", "bà", "cụ", "anh", "chị", "con"}:
                    c["per_name_starts_with_honorific"] += 1
            if e["label"] == "DATE" and not any(ch.isdigit() for ch in et):
                c["date_without_digit"] += 1
    dup_groups = [ids for ids in text_hash.values() if len(ids) > 1]
    shared = [ids for ids in para_docs.values() if len(ids) > 1]
    n_para = len(para_docs)
    result = {
        "docs": c["docs"],
        "text_length_chars": {"median": median(lengths) if lengths else 0, "mean": round(mean(lengths), 1) if lengths else 0,
                              "min": min(lengths, default=0), "max": max(lengths, default=0)},
        "entities_per_1000_chars": {"median": round(median(densities), 2) if densities else 0},
        "label_counts": dict(label_counts),
        "duplicate_documents": {"groups": len(dup_groups), "docs_involved": sum(len(g) for g in dup_groups),
                                "examples": [g[:4] for g in dup_groups[:3]]},
        "paragraphs_shared_across_docs": {"unique_paragraphs_ge_40_chars": n_para, "appearing_in_multiple_docs": len(shared),
                                           "fraction": round(len(shared) / n_para, 4) if n_para else 0},
        "issues": {k: v for k, v in c.items() if k != "docs" and v},
    }
    return result


# --------------------------------------------------------------------------- 4. OCR Hán


def _is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return (0x4E00 <= cp <= 0x9FFF) or (0x3400 <= cp <= 0x4DBF) or (0x20000 <= cp <= 0x2FA1F) or (0xF900 <= cp <= 0xFAFF)


def han_ocr_profile(dataset_root: Path) -> dict:
    records = []
    for path in sorted((dataset_root / "data").glob("track*/*.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    books, totals = [], Counter()
    line_counter: Counter = Counter()
    for rec in records:
        pages = rec.get("pages") or []
        b = Counter()
        rates = []
        for page in pages:
            l1 = page.get("l1_ocr") or {}
            text = (l1.get("voted_text") or "").replace("\n", "")
            b["pages"] += 1
            if not text.strip():
                b["pages_empty"] += 1
                continue
            b["chars"] += len(text)
            cjk = sum(1 for ch in text if _is_cjk(ch))
            b["cjk_chars"] += cjk
            b["placeholder_chars"] += sum(1 for ch in text if ch in _PLACEHOLDERS)
            b["ascii_letter_digit_chars"] += sum(1 for ch in text if ch.isascii() and ch.isalnum())
            rate = l1.get("uncertain_rate")
            if isinstance(rate, (int, float)):
                rates.append(rate)
                if rate >= 0.1:
                    b["pages_uncertain_ge_10pct"] += 1
            for line in (l1.get("voted_text") or "").splitlines():
                if len(line) >= 6:
                    line_counter[line] += 1
        if b["pages"] and b["chars"]:
            books.append({
                "doc_id": rec.get("doc_id"), "pages": b["pages"], "pages_empty": b["pages_empty"], "chars": b["chars"],
                "cjk_ratio": round(b["cjk_chars"] / b["chars"], 4),
                "placeholder_chars": b["placeholder_chars"], "ascii_alnum_chars": b["ascii_letter_digit_chars"],
                "uncertain_rate_mean": round(mean(rates), 4) if rates else None,
                "pages_uncertain_ge_10pct": b["pages_uncertain_ge_10pct"],
            })
        totals.update({k: v for k, v in b.items()})
    repeated = [(line, n) for line, n in line_counter.items() if n >= 3]
    repeated.sort(key=lambda x: -x[1])
    return {
        "records": len(records),
        "books_with_text": len(books),
        "totals": dict(totals),
        "cjk_ratio_overall": round(totals["cjk_chars"] / totals["chars"], 4) if totals["chars"] else None,
        "books": books,
        "repeated_lines_ge3": {"distinct_lines": len(repeated), "top": [{"line": l, "count": n} for l, n in repeated[:5]]},
        "note": "chỉ lớp l1_ocr (văn bản đã vote); chưa có nhãn NER Hán nào để đo chất lượng nhãn",
    }


# --------------------------------------------------------------------------- CLI


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--human-dir", type=Path, required=True)
    parser.add_argument("--silver-dir", type=Path, required=True)
    parser.add_argument("--han-dataset", type=Path, help="thư mục gốc hannom-bilingual-dataset (có data/track*/*.json)")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--regex-max-docs", type=int, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)

    human, silver = load_docs(args.human_dir), load_docs(args.silver_dir)
    report: dict = {"inputs": {"human_docs": len(human), "silver_docs": len(silver)}}
    report["silver_vs_human"] = silver_vs_human(human, silver)

    repo_app = Path(__file__).resolve().parents[2] / "nlp_family_extractor"
    sys.path.insert(0, str(repo_app))
    try:
        from app.domains.extraction.extractor import FamilyExtractor  # noqa: WPS433 — chỉ cần khi chạy baseline
        report["regex_baseline"] = regex_baseline(human, FamilyExtractor, max_docs=args.regex_max_docs)
    except ImportError as error:
        report["regex_baseline"] = {"skipped": f"không import được FamilyExtractor: {error}"}
    report["clean_checks_human"] = clean_checks(human)
    report["clean_checks_silver"] = clean_checks(silver)
    if args.han_dataset:
        report["han_ocr_profile"] = han_ocr_profile(args.han_dataset)

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    sv = report["silver_vs_human"]
    print(f"silver vs human ({sv['docs_compared']} cây): micro strict F1={sv['strict']['micro']['f1']}  lenient F1={sv['lenient_iou50']['micro']['f1']}")
    rb = report["regex_baseline"]
    if "person_names" in rb:
        print(f"regex baseline ({rb['docs']} cây): tên người F1={rb['person_names']['f1']}  quan hệ F1={rb['relations']['f1']}")
    print(f"đã ghi {args.output / 'quality_report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
