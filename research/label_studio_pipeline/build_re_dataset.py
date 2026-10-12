"""Dựng dữ liệu phân loại QUAN HỆ (RE) từ ``gold.training.json``: mỗi mẫu là một cặp tên người có thứ tự (đầu, đuôi).

Nhãn: ``FATHER_OF`` / ``MOTHER_OF`` / ``SPOUSE`` hoặc ``NONE``. ``SPOUSE`` đối xứng: cả hai chiều đều là dương.
Văn bản mẫu = đoạn quanh hai tên, có đánh dấu ``<h>…</h>`` (đầu) và ``<t>…</t>`` (đuôi).

Quan trọng — nguồn nhãn:
- ``train``/``dev``: nhãn quan hệ do Gemini sinh (nhiễu, CHƯA người soát) trên các cây KHÔNG thuộc tập người soát.
- ``test``: các cây người soát CÓ ghi quan hệ (rất ít: ~30 quan hệ) → số đo chỉ mang tính tham khảo.
Cặp xa hơn ``window`` ký tự không được xét (trần recall được báo trong ``stats.json``).

    python -m label_studio_pipeline.build_re_dataset --silver-dir <gemini_review/v2> --human-dir <v1_human> --output <dir>
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, Optional

LABELS = ["NONE", "FATHER_OF", "MOTHER_OF", "SPOUSE"]
H_OPEN, H_CLOSE, T_OPEN, T_CLOSE = "<h>", "</h>", "<t>", "</t>"


def mark_pair(text: str, head: dict, tail: dict, ctx: int = 60) -> str:
    """Cắt đoạn quanh hai thực thể và chèn dấu đầu/đuôi (chèn từ cuối về đầu để không lệch vị trí)."""
    lo = max(0, min(head["start"], tail["start"]) - ctx)
    hi = min(len(text), max(head["end"], tail["end"]) + ctx)
    inserts = [(head["start"], H_OPEN), (head["end"], H_CLOSE), (tail["start"], T_OPEN), (tail["end"], T_CLOSE)]
    out, cursor = [], lo
    for pos, tag in sorted(inserts, key=lambda x: (x[0], 0 if x[1] in (H_CLOSE, T_CLOSE) else 1)):
        out.append(text[cursor:pos])
        out.append(tag)
        cursor = pos
    out.append(text[cursor:hi])
    return "".join(out)


def gold_relations(doc: dict) -> dict[tuple[int, int], str]:
    rels = {}
    for r in doc.get("relations") or []:
        rels[(r["head"], r["tail"])] = r["type"]
        if r["type"] == "SPOUSE":
            rels[(r["tail"], r["head"])] = "SPOUSE"
    return rels


def build_pairs(doc: dict, tree_id: str, window: int = 300) -> tuple[list[dict], dict]:
    text, ents = doc["text"], doc["entities"]
    persons = [i for i, e in enumerate(ents) if e["label"] == "PER_NAME"]
    rels = gold_relations(doc)
    pairs, in_window = [], set()
    for i in persons:
        for j in persons:
            if i == j or abs(ents[i]["start"] - ents[j]["start"]) > window:
                continue
            if ents[i]["start"] < ents[j]["end"] and ents[j]["start"] < ents[i]["end"]:
                continue  # chồng nhau
            label = rels.get((i, j), "NONE")
            in_window.add((i, j))
            pairs.append({"tree": tree_id, "head": i, "tail": j, "head_text": ents[i]["text"], "tail_text": ents[j]["text"],
                          "text": mark_pair(text, ents[i], ents[j]), "label": label})
    positives = {k for k, v in rels.items() if v != "NONE"}
    missed = [k for k in positives if k not in in_window and not (rels[k] == "SPOUSE" and (k[1], k[0]) in in_window)]
    return pairs, {"gold_relations": len([r for r in doc.get("relations") or []]), "gold_out_of_window": len(missed)}


def load_docs(base: Path) -> dict[str, dict]:
    return {p.parent.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted(base.glob("*/gold.training.json"))}


def downsample_negatives(pairs: list[dict], ratio: float, rng: random.Random) -> list[dict]:
    pos = [p for p in pairs if p["label"] != "NONE"]
    neg = [p for p in pairs if p["label"] == "NONE"]
    keep = min(len(neg), int(ratio * max(1, len(pos))))
    return pos + rng.sample(neg, keep)


def build(silver_dir: Path, human_dir: Path, output: Path, *, window: int = 300, neg_ratio: float = 3.0,
          dev_ratio: float = 0.1, seed: int = 42) -> dict:
    rng = random.Random(seed)
    human = load_docs(human_dir)
    silver = {k: v for k, v in load_docs(silver_dir).items() if k not in human}
    ids = sorted(silver)
    rng.shuffle(ids)
    n_dev = max(1, int(dev_ratio * len(ids)))
    split_ids = {"dev": ids[:n_dev], "train": ids[n_dev:]}
    test_ids = [k for k, d in sorted(human.items()) if d.get("relations")]
    stats: dict = {"window": window, "neg_ratio": neg_ratio, "seed": seed, "splits": {}}
    output.mkdir(parents=True, exist_ok=True)
    for name, tids, src in (("train", split_ids["train"], silver), ("dev", split_ids["dev"], silver), ("test", test_ids, human)):
        rows, gold_total, missed = [], 0, 0
        for tid in tids:
            pairs, info = build_pairs(src[tid], tid, window)
            rows += pairs
            gold_total += info["gold_relations"]
            missed += info["gold_out_of_window"]
        full = Counter(r["label"] for r in rows)
        if name == "train":
            rows = downsample_negatives(rows, neg_ratio, rng)
        (output / f"{name}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
        stats["splits"][name] = {"trees": len(tids), "pairs_before_downsample": dict(full), "pairs_written": dict(Counter(r["label"] for r in rows)),
                                 "gold_relations": gold_total, "gold_out_of_window": missed}
    (output / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


def main(argv: Optional[Iterable[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--silver-dir", type=Path, required=True)
    ap.add_argument("--human-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--window", type=int, default=300)
    ap.add_argument("--neg-ratio", type=float, default=3.0)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(list(argv) if argv is not None else None)
    print(json.dumps(build(args.silver_dir, args.human_dir, args.output, window=args.window, neg_ratio=args.neg_ratio, seed=args.seed),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
