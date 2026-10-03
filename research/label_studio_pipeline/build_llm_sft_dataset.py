"""Build a chat-format SFT dataset (Phả ký text → entities + relations JSON) from gold labels.

Nguồn nhãn (đọc kỹ trước khi trích số liệu):
- Mặc định ``01_interim/gemini_review/v2/<tree_id>/gold.training.json`` (139 cây) = nhãn **silver**:
  rule + sơ đồ pha_he, rồi Gemini web rà/bổ sung (``gemini_review_labels.py``). Chưa người kiểm.
- ``gold_labels/<tree_id>/gold.training.json`` (bản cũ, ``--gold-dir``) = silver kiểu khác: Gemini
  trích + pha_he + regex (``gold_builder.py``), ``gold_source = auto_gold_pending_review``.
- ``gold_labels/v1_human/<tree_id>/`` (25 cây stratified) = export Label Studio do người duyệt.

Chia tập theo ``stratified_sample.json``: 5 cây ``split=test`` bị loại khỏi train/val và được
xuất thành 2 file test (nhãn human và nhãn silver). Phần còn lại chia train/val theo cây.

Văn bản dài được cắt theo dòng thành các đoạn ≤ ``--max-chars`` (mặc định 3000 = đúng cách cắt của
bước Gemini rà). Nhãn của một đoạn = mọi entity có chữ xuất hiện (nguyên từ) trong đoạn — không chỉ
lần xuất hiện đầu tiên, nếu không model học cách bỏ qua tên đã nhắc ở đoạn trước. Một quan hệ được
giữ khi cả head và tail có trong đoạn; số quan hệ không rơi vào đoạn nào ghi ở ``stats.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from label_studio_pipeline.corpus_store import load_json
from label_studio_pipeline.data_layout import DATA_ROOT, GOLD_LABELS, GOLD_STRATIFIED

DEFAULT_GOLD_DIR = DATA_ROOT / "01_interim" / "gemini_review" / "v2"
DEFAULT_OUTPUT = DATA_ROOT / "03_derived" / "llm_sft" / "v2"
DEFAULT_HUMAN_DIR = GOLD_LABELS / "v1_human"
DEFAULT_MAX_CHARS = 3000
DEFAULT_VAL_RATIO = 0.1
DEFAULT_SEED = 42

SYSTEM_PROMPT = (
    "Bạn là hệ thống trích xuất thông tin gia phả tiếng Việt. "
    "Đọc đoạn Phả ký và trả về DUY NHẤT một JSON có dạng "
    '{"entities": [{"text": ..., "label": ...}], "relations": [{"type": ..., "head": ..., "tail": ...}]}. '
    "Nhãn entity: PER_NAME, LOC, DATE, GENERATION, ORDER. "
    "Loại quan hệ: FATHER_OF, MOTHER_OF, SPOUSE (head/tail là PER_NAME). "
    "Chỉ dùng chữ xuất hiện nguyên văn trong đoạn; không suy đoán người không được nhắc tới. "
    "Nếu không có gì, trả về danh sách rỗng."
)

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _split_long_line(start: int, end: int, text: str, max_chars: int) -> list[tuple[int, int]]:
    """Split [start, end) into pieces ≤ max_chars, preferring sentence then whitespace breaks."""
    pieces: list[tuple[int, int]] = []
    while end - start > max_chars:
        window = text[start : start + max_chars]
        cut = window.rfind(". ")
        cut = cut + 2 if cut > max_chars // 2 else window.rfind(" ")
        if cut <= 0:
            cut = max_chars
        pieces.append((start, start + cut))
        start += cut
    pieces.append((start, end))
    return pieces


def chunk_spans(text: str, max_chars: int) -> list[tuple[int, int]]:
    """Return [start, end) chunk offsets that cover ``text``, breaking at newlines."""
    lines: list[tuple[int, int]] = []
    pos = 0
    for line in text.splitlines(keepends=True):
        lines.extend(_split_long_line(pos, pos + len(line), text, max_chars))
        pos += len(line)

    chunks: list[tuple[int, int]] = []
    cur_start, cur_end = None, None
    for start, end in lines:
        if cur_start is None:
            cur_start, cur_end = start, end
        elif end - cur_start <= max_chars:
            cur_end = end
        else:
            chunks.append((cur_start, cur_end))
            cur_start, cur_end = start, end
    if cur_start is not None:
        chunks.append((cur_start, cur_end))
    return chunks


def _occurs(chunk_text: str, needle: str) -> int:
    """Vị trí đầu tiên của ``needle`` như một cụm từ trọn vẹn trong đoạn (-1 nếu không có).

    Chặn ranh giới chữ để tên ngắn như "Lan" không khớp bên trong "Lang".
    """
    match = re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", chunk_text)
    return match.start() if match else -1


def build_examples(doc: dict, *, max_chars: int, label_source: str, counters: Counter) -> list[dict]:
    """Turn one gold.training.json document into chunk-level chat examples."""
    text = doc["text"]
    entities = doc.get("entities") or []
    relations = doc.get("relations") or []
    counters["entities_in"] += len(entities)
    counters["relations_in"] += len(relations)

    # Nhãn theo chữ, bỏ trùng (text, label); quan hệ theo chữ head/tail.
    unique_entities: list[tuple[str, str]] = []
    for ent in entities:
        key = (ent["text"], ent["label"])
        if key not in unique_entities:
            unique_entities.append(key)
    rel_texts: list[tuple[str, str, str]] = []
    for rel in relations:
        key = (rel["type"], entities[rel["head"]]["text"], entities[rel["tail"]]["text"])
        if key not in rel_texts:
            rel_texts.append(key)

    examples: list[dict] = []
    chunks = chunk_spans(text, max_chars)
    placed_entities: set[tuple[str, str]] = set()
    placed_relations: set[tuple[str, str, str]] = set()
    for chunk_idx, (c_start, c_end) in enumerate(chunks):
        chunk_text = text[c_start:c_end].strip()
        if not chunk_text:
            continue
        found = sorted(
            ((pos, key) for key in unique_entities if (pos := _occurs(chunk_text, key[0])) >= 0),
            key=lambda item: item[0],
        )
        chunk_entities = [key for _, key in found]
        placed_entities |= set(chunk_entities)
        names = {t for t, label in chunk_entities if label == "PER_NAME"}
        chunk_rels = [r for r in rel_texts if r[1] in names and r[2] in names]
        placed_relations |= set(chunk_rels)
        target = {
            "entities": [{"text": t, "label": label} for t, label in chunk_entities],
            "relations": [{"type": typ, "head": h, "tail": t} for typ, h, t in chunk_rels],
        }
        if not target["entities"]:
            counters["empty_chunks"] += 1
        examples.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": chunk_text},
                    {"role": "assistant", "content": json.dumps(target, ensure_ascii=False)},
                ],
                "meta": {
                    "doc_id": doc.get("doc_id"),
                    "tree_id": doc.get("tree_id"),
                    "chunk": chunk_idx,
                    "n_chunks": len(chunks),
                    "label_source": label_source,
                    "char_count": len(chunk_text),
                },
            }
        )
    counters["chunks"] += len(examples)
    counters["entities_unique"] += len(unique_entities)
    counters["entities_not_in_any_chunk"] += len(unique_entities) - len(placed_entities)
    counters["relations_unique"] += len(rel_texts)
    counters["relations_lost_cross_chunk"] += len(rel_texts) - len(placed_relations)
    counters["relations_kept"] += len(placed_relations)
    return examples


def _load_doc(base: Path, tree_id: int) -> dict | None:
    return load_json(base / str(tree_id) / "gold.training.json")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_dataset(
    *,
    gold_dir: Path,
    human_dir: Path,
    stratified_path: Path,
    output_dir: Path,
    max_chars: int,
    val_ratio: float,
    seed: int,
    prefer_human: bool,
) -> dict:
    stratified = load_json(stratified_path) or {}
    test_ids = sorted(int(d["tree_id"]) for d in stratified.get("documents", []) if d.get("split") == "test")
    human_ids = {int(p.name) for p in human_dir.iterdir() if p.is_dir() and p.name.isdigit()}
    all_ids = sorted(int(p.name) for p in gold_dir.iterdir() if p.is_dir() and p.name.isdigit())
    pool = [t for t in all_ids if t not in test_ids]

    rng = random.Random(seed)
    shuffled = pool[:]
    rng.shuffle(shuffled)
    n_val = max(1, round(len(pool) * val_ratio))
    val_ids = sorted(shuffled[:n_val])
    train_ids = sorted(shuffled[n_val:])

    splits: dict[str, list[dict]] = {}
    stats: dict[str, dict] = {}
    plan = {
        "train": [(t, "human" if prefer_human and t in human_ids else "silver") for t in train_ids],
        "val": [(t, "human" if prefer_human and t in human_ids else "silver") for t in val_ids],
        "test_human": [(t, "human") for t in test_ids],
        "test_silver": [(t, "silver") for t in test_ids],
    }
    for split, items in plan.items():
        counters: Counter = Counter()
        rows: list[dict] = []
        for tree_id, source in items:
            doc = _load_doc(human_dir if source == "human" else gold_dir, tree_id)
            if doc is None:
                counters["missing_docs"] += 1
                logger.warning("missing %s doc for tree %s", source, tree_id)
                continue
            counters["docs"] += 1
            counters[f"docs_{source}"] += 1
            # Ghi đúng nguồn nhãn của từng cây (vd "gemini-review-v2:reviewed") thay vì chỉ "silver".
            label_source = f"{source}:{doc['source']}" if doc.get("source") else source
            rows.extend(build_examples(doc, max_chars=max_chars, label_source=label_source, counters=counters))
        splits[split] = rows
        stats[split] = {"tree_ids": [t for t, _ in items], **dict(counters)}

    output_dir.mkdir(parents=True, exist_ok=True)
    for split, rows in splits.items():
        _write_jsonl(output_dir / f"{split}.jsonl", rows)

    summary = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "params": {
            "max_chars": max_chars,
            "val_ratio": val_ratio,
            "seed": seed,
            "prefer_human": prefer_human,
            "gold_dir": str(gold_dir),
            "human_dir": str(human_dir),
            "stratified": str(stratified_path),
        },
        "label_note": (
            "silver = gold_builder (Gemini + pha_he + regex), chưa người duyệt; "
            "human = Label Studio v1_human export"
        ),
        "splits": stats,
    }
    (output_dir / "stats.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build chat-format SFT JSONL from gold labels.")
    parser.add_argument("--gold-dir", type=Path, default=DEFAULT_GOLD_DIR)
    parser.add_argument("--human-dir", type=Path, default=DEFAULT_HUMAN_DIR)
    parser.add_argument("--stratified", type=Path, default=GOLD_STRATIFIED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--val-ratio", type=float, default=DEFAULT_VAL_RATIO)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--prefer-human",
        action="store_true",
        help="Dùng nhãn v1_human thay silver cho các cây train/val có bản người duyệt.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    _configure_logging(args.verbose)
    summary = build_dataset(
        gold_dir=args.gold_dir,
        human_dir=args.human_dir,
        stratified_path=args.stratified,
        output_dir=args.output,
        max_chars=args.max_chars,
        val_ratio=args.val_ratio,
        seed=args.seed,
        prefer_human=args.prefer_human,
    )
    json.dump(summary["splits"], sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
