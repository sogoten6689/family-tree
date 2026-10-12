"""Gán nhãn QUAN HỆ (cha/mẹ/vợ chồng) bằng Gemini (qua RamCloud, API kiểu OpenAI) cho các tên người đã có sẵn.

Khác nhãn Gemini cũ: Gemini nhìn cả đoạn văn với các tên được đánh số ``[#id]`` và chỉ trả quan hệ giữa các id đó
(không sinh thực thể mới), kèm câu chứng cứ. Kết quả ghi theo cây vào ``--output-dir/<tree>.json`` (chạy lại thì bỏ qua cây đã có).
Có lệnh ``evaluate`` so với quan hệ người soát (khớp theo CHỮ tên, ``SPOUSE`` không phân biệt chiều).

TỐN TIỀN (gọi API). Khoá đọc từ biến môi trường ``RAMCLOUD_KEY``; không ghi khoá vào mã/log.

    python -m label_studio_pipeline.gemini_relation_labels label --docs-dir <v1_human> --output-dir <dir> --trees 423,321
    python -m label_studio_pipeline.gemini_relation_labels evaluate --pred-dir <dir> --human-dir <v1_human>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

BASE_URL = os.getenv("RAMCLOUD_BASE_URL", "https://ramclouds.me/v1")
MODEL = os.getenv("RAMCLOUD_MODEL", "gemini-3.8-flash")
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
REL_TYPES = {"FATHER_OF", "MOTHER_OF", "SPOUSE"}

SYSTEM_PROMPT = """Bạn là chuyên gia gia phả Việt Nam. Bạn nhận một đoạn văn gia phả tiếng Việt, trong đó các tên người được đánh dấu dạng `Tên[#số]`.
Nhiệm vụ: liệt kê CÁC QUAN HỆ giữa các tên người đã đánh dấu, chỉ dùng số `#id` đã có.

Loại quan hệ:
- FATHER_OF: head = người CHA, tail = người CON (con trai hoặc con gái).
- MOTHER_OF: head = người MẸ, tail = người CON.
- SPOUSE: hai người là VỢ CHỒNG (ghi một lần, thứ tự tuỳ ý).

Quy tắc nghiêm ngặt:
1. Chỉ ghi quan hệ mà văn bản NÓI RÕ hoặc theo cách viết gia phả thông thường chắc chắn suy ra được (ví dụ "ông A sinh B, C" → A là cha của B và C; "bà X, vợ ông A" → SPOUSE).
2. KHÔNG suy ra quan hệ anh/chị/em, ông/cháu, hoặc "cùng họ". Không đoán khi không chắc.
3. Hướng quan hệ phải đúng: head là cha/mẹ, tail là con. Không ghi đồng thời cả hai chiều.
4. Nếu một tên xuất hiện nhiều lần, chọn bất kỳ id nào của đúng người đó.
5. Mỗi quan hệ kèm "evidence": trích ngắn (≤ 15 từ) từ văn bản làm căn cứ.

Chỉ trả về JSON: {"relations": [{"head": <id>, "tail": <id>, "type": "FATHER_OF|MOTHER_OF|SPOUSE", "evidence": "..."}]}. Nếu không có quan hệ nào: {"relations": []}."""


def annotate(doc: dict) -> tuple[str, dict[int, dict]]:
    """Chèn ``[#id]`` sau mỗi PER_NAME (từ cuối về đầu để không lệch vị trí). Trả (văn bản, {id: thực thể})."""
    text = doc["text"]
    persons = {i: e for i, e in enumerate(doc["entities"]) if e["label"] == "PER_NAME"}
    out, cursor = [], 0
    for i, e in sorted(persons.items(), key=lambda kv: kv[1]["start"]):
        if e["start"] < cursor:
            continue
        out.append(text[cursor:e["end"]])
        out.append(f"[#{i}]")
        cursor = e["end"]
    out.append(text[cursor:])
    return "".join(out), persons


def parse_response(raw: str, valid_ids: set[int]) -> list[dict]:
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        s = s.rsplit("```", 1)[0]
    data = json.loads(s)
    rels, seen = [], set()
    for r in data.get("relations", []):
        try:
            h, t, ty = int(r["head"]), int(r["tail"]), str(r["type"]).upper()
        except (KeyError, TypeError, ValueError):
            continue
        key = (min(h, t), max(h, t), ty) if ty == "SPOUSE" else (h, t, ty)
        if ty not in REL_TYPES or h == t or h not in valid_ids or t not in valid_ids or key in seen:
            continue
        seen.add(key)
        rels.append({"head": h, "tail": t, "type": ty, "evidence": str(r.get("evidence", ""))[:200]})
    return rels


def call_llm(text: str, *, transport=None, timeout: float = 180.0, retries: int = 8, wait: float = 30.0) -> tuple[str, dict]:
    """Gọi API; gặp 429/5xx (hạn mức nguội, lỗi tạm) thì chờ rồi thử lại tối đa ``retries`` lần."""
    last = ""
    for attempt in range(retries + 1):
        try:
            return _call_once(text, transport=transport, timeout=timeout)
        except _Transient as error:
            last = str(error)
            if attempt < retries:
                time.sleep(wait)
    raise RuntimeError(f"hết lần thử lại: {last}")


class _Transient(RuntimeError):
    pass


def _call_once(text: str, *, transport=None, timeout: float = 180.0) -> tuple[str, dict]:
    import httpx

    key = os.environ.get("RAMCLOUD_KEY", "")
    if not key:
        raise SystemExit("Thiếu biến môi trường RAMCLOUD_KEY")
    payload = {"model": MODEL, "temperature": 0, "response_format": {"type": "json_object"},
               "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}]}
    with httpx.Client(timeout=httpx.Timeout(timeout, connect=20.0), transport=transport,
                      headers={"Authorization": f"Bearer {key}", "User-Agent": _UA, "Content-Type": "application/json"}) as c:
        resp = c.post(f"{BASE_URL}/chat/completions", json=payload)
    if resp.status_code in (429, 500, 502, 503, 504):
        raise _Transient(f"HTTP {resp.status_code}: {resp.text[:160].replace(key, '***')}")
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200].replace(key, '***')}")
    body = resp.json()
    return body["choices"][0]["message"]["content"], body.get("usage") or {}


def label_tree(doc: dict, ask: Callable[[str], tuple[str, dict]] = call_llm) -> dict:
    text, persons = annotate(doc)
    if len(persons) < 2:
        return {"relations": [], "usage": {}, "note": "ít hơn 2 tên người"}
    raw, usage = ask(text)
    rels = parse_response(raw, set(persons))
    for r in rels:
        r["head_text"], r["tail_text"] = persons[r["head"]]["text"], persons[r["tail"]]["text"]
    return {"relations": rels, "usage": usage}


def name_triples(relations: Iterable[dict], names: dict[int, str]) -> set[tuple]:
    out = set()
    for r in relations:
        h, t = names[r["head"]].strip(), names[r["tail"]].strip()
        if r["type"] == "SPOUSE":
            h, t = sorted((h, t))
        out.add((h, t, r["type"]))
    return out


def evaluate(pred_dir: Path, human_dir: Path) -> dict:
    tp = fp = fn = 0
    per_type: dict[str, list[int]] = {}
    for pf in sorted(Path(pred_dir).glob("*.json")):
        tid = pf.stem
        hdoc = json.loads((Path(human_dir) / tid / "gold.training.json").read_text(encoding="utf-8"))
        if not hdoc.get("relations"):
            continue
        hnames = {i: e["text"] for i, e in enumerate(hdoc["entities"])}
        gold = name_triples(hdoc["relations"], hnames)
        pred_raw = json.loads(pf.read_text(encoding="utf-8"))["relations"]
        pred = {(a, b, t) for a, b, t in name_triples(pred_raw, {r["head"]: r["head_text"] for r in pred_raw} | {r["tail"]: r["tail_text"] for r in pred_raw})}
        # chỉ tính dự đoán mà cả hai tên đều là tên người trong gold người
        known = {e["text"].strip() for e in hdoc["entities"] if e["label"] == "PER_NAME"}
        pred = {x for x in pred if x[0] in known and x[1] in known}
        tp += len(gold & pred)
        fp += len(pred - gold)
        fn += len(gold - pred)
        for ty in REL_TYPES:
            g, p = {x for x in gold if x[2] == ty}, {x for x in pred if x[2] == ty}
            c = per_type.setdefault(ty, [0, 0, 0])
            c[0] += len(g & p); c[1] += len(p - g); c[2] += len(g - p)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0, "tp": tp, "fp": fp, "fn": fn,
            "per_type_tp_fp_fn": per_type}


def run_label(docs_dir: Path, output_dir: Path, trees: list[str], ask=call_llm, progress=print) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    totals = {"trees": 0, "skipped": 0, "prompt_tokens": 0, "completion_tokens": 0, "errors": 0}
    for tid in trees:
        out = output_dir / f"{tid}.json"
        if out.exists():
            totals["skipped"] += 1
            continue
        doc = json.loads((docs_dir / tid / "gold.training.json").read_text(encoding="utf-8"))
        try:
            res = label_tree(doc, ask)
        except Exception as error:  # noqa: BLE001
            totals["errors"] += 1
            progress(f"cây {tid}: lỗi {str(error)[:120]}")
            continue
        out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        totals["trees"] += 1
        totals["prompt_tokens"] += int(res["usage"].get("prompt_tokens", 0) or 0)
        totals["completion_tokens"] += int(res["usage"].get("completion_tokens", 0) or 0)
        progress(f"cây {tid}: {len(res['relations'])} quan hệ")
        time.sleep(0.5)
    return totals


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    lb = sub.add_parser("label")
    lb.add_argument("--docs-dir", type=Path, required=True)
    lb.add_argument("--output-dir", type=Path, required=True)
    lb.add_argument("--trees", required=True, help="danh sách mã cây, ngăn cách bằng dấu phẩy, hoặc 'all'")
    ev = sub.add_parser("evaluate")
    ev.add_argument("--pred-dir", type=Path, required=True)
    ev.add_argument("--human-dir", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.cmd == "label":
        ids = sorted(p.parent.name for p in args.docs_dir.glob("*/gold.training.json")) if args.trees == "all" else args.trees.split(",")
        print(json.dumps(run_label(args.docs_dir, args.output_dir, ids), ensure_ascii=False))
    else:
        print(json.dumps(evaluate(args.pred_dir, args.human_dir), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
