"""Dựng bộ dữ liệu NER chữ Hán mức KÝ TỰ (CoNLL IOB2) từ nhãn máy `han_llm_trial/gold/*.json`.

Hai bộ (cùng nguồn, KHÔNG chứa tập test 15 trang):
  han_cv5/fold{k}/{train,dev,test}.conll — kiểm chéo theo SÁCH (scan_id): sách trong test không xuất hiện trong train,
                                          để không rò rỉ giữa các trang cùng sách. Nhãn là nhãn máy (Gemini) → F1 ở đây
                                          đo mức mô hình HỌC ĐƯỢC nhãn máy, KHÔNG phải độ chính xác thật.
  han_final/{train,dev,test}.conll       — huấn luyện bản cuối: dev = 2 sách, train = các sách còn lại, test = 15 trang tập
                                          test (nhãn máy; sau này chấm lại bằng nhãn người). Trang test cùng sách với một số
                                          trang train (khác trang) nên ước lượng trên người sẽ hơi lạc quan.
Tập test (held_out.json) bị loại khỏi mọi tập train/dev của kiểm chéo.

    python -m label_studio_pipeline.build_han_ner_dataset --gold-dir <han_llm_trial/gold> --held-out <han_test_v1/held_out.json> --out <dir>
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from label_studio_pipeline.export_conll import convert_document, write_conll
from label_studio_pipeline.export_cv_folds import plan_folds


def load_docs(gold_dir: Path) -> List[Dict[str, Any]]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(gold_dir.glob("*.json"))]


def book_of(doc: Dict[str, Any]) -> str:
    return str(doc["provenance"]["scan_id"])


def sentences_for(docs: List[Dict[str, Any]], counters: Counter) -> list:
    out = []
    for doc in docs:
        out.extend(convert_document(doc, unit="char", counters=counters))
    return out


def write_split(path: Path, docs: List[Dict[str, Any]]) -> Dict[str, int]:
    counters: Counter = Counter()
    sentences = sentences_for(docs, counters)
    write_conll(path, sentences)
    entities = sum(1 for s in sentences for _, tag in s if tag.startswith("B-"))
    return {"docs": len(docs), "sentences": len(sentences), "tokens": sum(len(s) for s in sentences), "entities": entities}


def build(gold_dir: Path, held_out_path: Optional[Path], out_dir: Path, folds: int = 5, seed: int = 42) -> Dict[str, Any]:
    docs = load_docs(gold_dir)
    held = set(json.loads(held_out_path.read_text(encoding="utf-8"))) if held_out_path and held_out_path.exists() else set()
    test_docs = [d for d in docs if d["doc_id"] in held]
    pool = [d for d in docs if d["doc_id"] not in held]
    by_book: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for doc in pool:
        by_book[book_of(doc)].append(doc)

    summary: Dict[str, Any] = {"books": len(by_book), "pages_pool": len(pool), "pages_test": len(test_docs), "cv": [], "final": {}}
    for fold in plan_folds(sorted(by_book), folds, seed):
        entry = {"fold": fold["fold"], "books": {s: fold[s] for s in ("train", "dev", "test")}}
        for split in ("train", "dev", "test"):
            split_docs = [d for b in fold[split] for d in by_book[b]]
            entry[split] = write_split(out_dir / "han_cv5" / f"fold{fold['fold']}" / f"{split}.conll", split_docs)
        summary["cv"].append(entry)

    books = sorted(by_book)
    random.Random(seed).shuffle(books)
    dev_books, train_books = sorted(books[:2]), sorted(books[2:])
    summary["final"] = {
        "dev_books": dev_books,
        "train": write_split(out_dir / "han_final" / "train.conll", [d for b in train_books for d in by_book[b]]),
        "dev": write_split(out_dir / "han_final" / "dev.conll", [d for b in dev_books for d in by_book[b]]),
        "test": write_split(out_dir / "han_final" / "test.conll", test_docs),
    }
    (out_dir / "dataset_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gold-dir", type=Path, required=True)
    parser.add_argument("--held-out", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    summary = build(args.gold_dir, args.held_out, args.out, args.folds, args.seed)
    print(json.dumps({k: summary[k] for k in ("books", "pages_pool", "pages_test")} | {"final": summary["final"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
