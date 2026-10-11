"""Fine-tune NER (token classification) từ CoNLL do ``export_conll.py`` sinh ra — dùng chung cho PhoBERT và SikuBERT.

Thiết kế để chạy trên Google Colab (GPU), nhưng không phụ thuộc Colab. Chỉ cần ``torch`` + ``transformers``.

    # Việt (tệp train/dev/test.conll mức âm tiết)
    python -m label_studio_pipeline.train_ner --model vinai/phobert-base --data-dir vi_v1 --output-dir out/vi

    # Hán (mức ký tự)
    python -m label_studio_pipeline.train_ner --model SIKU-BERT/sikubert --data-dir han_v1 --output-dir out/han

Giấy phép: PhoBERT-base = MIT, SikuBERT = Apache-2.0. KHÔNG dùng ``vinai/phobert-base-v2`` (AGPL-3.0).
Đầu ra: trọng số + tokenizer + ``label_list.json`` + ``model_card.json`` (dữ liệu, siêu tham số, chỉ số dev/test).
Chỉ số là F1 mức thực thể, khớp tuyệt đối (strict), tính trực tiếp — không cần seqeval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence

ENTITY_LABELS = ("PER_NAME", "GENERATION", "DATE", "ORDER", "LOC")  # khớp ls_importer.LABEL_STUDIO_CONFIG
LABEL_LIST = ["O"] + [f"{p}-{l}" for l in ENTITY_LABELS for p in ("B", "I")]
IGNORE_INDEX = -100
FORBIDDEN_MODELS = {"vinai/phobert-base-v2", "vinai/phobert-large-v2"}  # AGPL-3.0


# --------------------------------------------------------------------------- dữ liệu


def read_conll(path: Path, sep: str = "\t") -> list[tuple[list[str], list[str]]]:
    """Đọc CoNLL: mỗi dòng ``token<sep>tag``; dòng trống ngăn câu. Tag lạ → lỗi (không bỏ qua lặng lẽ)."""
    sentences, words, tags = [], [], []
    for lineno, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = raw.rstrip("\n")
        if not line.strip():
            if words:
                sentences.append((words, tags))
                words, tags = [], []
            continue
        parts = line.split(sep) if sep in line else line.rsplit(None, 1)
        if len(parts) != 2:
            raise ValueError(f"{path}:{lineno}: cần 'token{sep!r}tag', gặp {line!r}")
        token, tag = parts[0], parts[1].strip()
        if tag not in LABEL_LIST:
            raise ValueError(f"{path}:{lineno}: nhãn lạ {tag!r}")
        words.append(token)
        tags.append(tag)
    if words:
        sentences.append((words, tags))
    return sentences


def encode_sentence(words: Sequence[str], tags: Sequence[str], tokenizer, max_length: int,
                    label2id: dict[str, int]) -> dict:
    """Mã hoá từng từ riêng (chạy được cả tokenizer chậm như PhoBERT, không cần ``word_ids``).
    Nhãn đặt ở subword ĐẦU của mỗi từ; các subword còn lại = -100 (không tính loss)."""
    cls_id, sep_id = tokenizer.cls_token_id, tokenizer.sep_token_id
    unk_id = tokenizer.unk_token_id
    ids, labels = [cls_id], [IGNORE_INDEX]
    budget = max_length - 1  # chừa chỗ cho [SEP]
    for word, tag in zip(words, tags):
        pieces = tokenizer.convert_tokens_to_ids(tokenizer.tokenize(word)) or [unk_id]
        if len(ids) + len(pieces) > budget:
            break  # cắt cuối câu; câu đã giới hạn ≤128 token ở bước xuất nên hiếm
        ids.extend(pieces)
        labels.extend([label2id[tag]] + [IGNORE_INDEX] * (len(pieces) - 1))
    ids.append(sep_id)
    labels.append(IGNORE_INDEX)
    return {"input_ids": ids, "labels": labels}


def collate(batch: list[dict], pad_id: int) -> dict:
    import torch
    n = max(len(b["input_ids"]) for b in batch)
    ids = torch.full((len(batch), n), pad_id, dtype=torch.long)
    lab = torch.full((len(batch), n), IGNORE_INDEX, dtype=torch.long)
    att = torch.zeros((len(batch), n), dtype=torch.long)
    for i, b in enumerate(batch):
        k = len(b["input_ids"])
        ids[i, :k], lab[i, :k], att[i, :k] = torch.tensor(b["input_ids"]), torch.tensor(b["labels"]), 1
    return {"input_ids": ids, "labels": lab, "attention_mask": att}


# --------------------------------------------------------------------------- chỉ số


def bio_to_spans(tags: Sequence[str]) -> set[tuple[int, int, str]]:
    """BIO → {(start, end, label)}. ``I-X`` mồ côi (không sau B/I cùng loại) mở một span mới."""
    spans, start, cur = set(), None, None
    for i, tag in enumerate(list(tags) + ["O"]):
        prefix, _, label = tag.partition("-")
        if cur is not None and not (prefix == "I" and label == cur):
            spans.add((start, i, cur))
            cur = None
        if prefix in ("B", "I") and cur is None:
            start, cur = i, label
    return spans


def entity_prf(gold: Iterable[Sequence[str]], pred: Iterable[Sequence[str]]) -> dict:
    tp: Counter = Counter()
    fp: Counter = Counter()
    fn: Counter = Counter()
    for g_tags, p_tags in zip(gold, pred):
        g, p = bio_to_spans(g_tags), bio_to_spans(p_tags)
        for s in g & p:
            tp[s[2]] += 1
        for s in p - g:
            fp[s[2]] += 1
        for s in g - p:
            fn[s[2]] += 1

    def prf(t: int, f_p: int, f_n: int) -> dict:
        p = t / (t + f_p) if t + f_p else 0.0
        r = t / (t + f_n) if t + f_n else 0.0
        return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0,
                "tp": t, "fp": f_p, "fn": f_n}

    out = {"micro": prf(sum(tp.values()), sum(fp.values()), sum(fn.values())), "per_label": {}}
    for label in ENTITY_LABELS:
        if tp[label] + fp[label] + fn[label]:
            out["per_label"][label] = prf(tp[label], fp[label], fn[label])
    return out


def bootstrap_f1_ci(gold: list[Sequence[str]], pred: list[Sequence[str]], n: int = 1000, seed: int = 0) -> tuple[float, float]:
    """Khoảng tin cậy 95% của micro-F1, lấy mẫu lại theo CÂU. Gold nhỏ → luôn báo khoảng này, không báo một số trơn."""
    rng = random.Random(seed)
    idx = range(len(gold))
    scores = []
    for _ in range(n):
        pick = [rng.choice(idx) for _ in idx]
        scores.append(entity_prf([gold[i] for i in pick], [pred[i] for i in pick])["micro"]["f1"])
    scores.sort()
    return scores[int(0.025 * n)], scores[int(0.975 * n) - 1]


# --------------------------------------------------------------------------- huấn luyện


def sha256_of(paths: Iterable[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def predict_tags(model, loader, id2label: dict[int, str], device) -> tuple[list[list[str]], list[list[str]]]:
    import torch
    model.eval()
    gold, pred = [], []
    with torch.no_grad():
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            logits = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]).logits
            guess = logits.argmax(-1).cpu().tolist()
            labels = batch["labels"].cpu().tolist()
            for g_row, p_row in zip(labels, guess):
                gold.append([id2label[g] for g in g_row if g != IGNORE_INDEX])
                pred.append([id2label[p] for g, p in zip(g_row, p_row) if g != IGNORE_INDEX])
    return gold, pred


def predict_probs(model, loader, device) -> list[list[list[float]]]:
    """Xác suất softmax của từng từ (subword đầu) theo từng nhãn, theo thứ tự câu của ``loader`` (không xáo trộn).
    Lưu lại để thử gộp model / chỉnh ngưỡng / hậu xử lý ngoại tuyến, không cần huấn luyện lại."""
    import torch
    model.eval()
    out: list[list[list[float]]] = []
    with torch.no_grad():
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            probs = torch.softmax(model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]).logits.float(), -1).cpu()
            labels = batch["labels"].cpu()
            for row_p, row_l in zip(probs, labels):
                out.append([[round(float(x), 4) for x in row_p[i]] for i in range(len(row_l)) if row_l[i] != IGNORE_INDEX])
    return out


def train(args: argparse.Namespace, log: Callable[[str], None] = print) -> dict:
    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoModelForTokenClassification, AutoTokenizer, get_linear_schedule_with_warmup

    if args.model in FORBIDDEN_MODELS:
        raise SystemExit(f"{args.model} có giấy phép AGPL-3.0 — không dùng. Dùng vinai/phobert-base (MIT).")
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    data_dir = Path(args.data_dir)
    # export_conll.py đặt tên val / test_human; hỗ trợ cả dev / test
    pick = lambda *names: next((data_dir / f"{n}.conll" for n in names if (data_dir / f"{n}.conll").exists()), data_dir / f"{names[0]}.conll")
    files = {"train": pick("train"), "dev": pick("dev", "val"), "test": pick(args.test_split, "test", "test_human")}
    missing = [str(p) for s, p in files.items() if s != "test" and not p.exists()]
    if missing:
        raise SystemExit(f"thiếu tệp: {missing}")
    raw = {s: read_conll(p) for s, p in files.items() if p.exists()}
    label2id = {l: i for i, l in enumerate(LABEL_LIST)}
    id2label = {i: l for l, i in label2id.items()}

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForTokenClassification.from_pretrained(
        args.model, num_labels=len(LABEL_LIST), id2label=id2label, label2id=label2id).to(device)
    max_len = min(args.max_length, getattr(model.config, "max_position_embeddings", 512) - 2)
    enc = {s: [encode_sentence(w, t, tokenizer, max_len, label2id) for w, t in sents] for s, sents in raw.items()}
    pad = tokenizer.pad_token_id
    make = lambda s, shuffle: DataLoader(enc[s], batch_size=args.batch_size, shuffle=shuffle,
                                         collate_fn=lambda b: collate(b, pad))
    train_loader = make("train", True)
    log(f"thiết bị={device} câu: " + ", ".join(f"{s}={len(v)}" for s, v in enc.items()))

    optim = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    steps = len(train_loader) * args.epochs
    sched = get_linear_schedule_with_warmup(optim, int(0.1 * steps), steps)
    amp = device.type == "cuda"
    scaler = torch.cuda.amp.GradScaler(enabled=amp)

    best_f1, best_epoch, history = -1.0, 0, []
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for epoch in range(1, args.epochs + 1):
        model.train()
        total = 0.0
        for batch in train_loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            with torch.autocast(device_type=device.type, enabled=amp):
                loss = model(**batch).loss
            optim.zero_grad()
            scaler.scale(loss).backward()
            scaler.unscale_(optim)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optim)
            scaler.update()
            sched.step()
            total += loss.item()
        g, p = predict_tags(model, make("dev", False), id2label, device)
        dev = entity_prf(g, p)
        history.append({"epoch": epoch, "train_loss": round(total / max(1, len(train_loader)), 4), "dev_micro_f1": dev["micro"]["f1"]})
        log(f"epoch {epoch}: loss={history[-1]['train_loss']} dev_F1={dev['micro']['f1']}")
        if dev["micro"]["f1"] > best_f1:
            best_f1, best_epoch = dev["micro"]["f1"], epoch
            model.save_pretrained(out_dir)
            tokenizer.save_pretrained(out_dir)

    best = AutoModelForTokenClassification.from_pretrained(out_dir).to(device)
    card = {
        "base_model": args.model, "task": "ner", "labels": LABEL_LIST, "best_epoch": best_epoch,
        "hyperparameters": {k: getattr(args, k) for k in ("epochs", "lr", "batch_size", "max_length", "seed", "test_split")},
        "data": {"dir": str(data_dir), "sha256": sha256_of([p for p in files.values() if p.exists()]),
                 "sentences": {s: len(v) for s, v in raw.items()}},
        "history": history,
    }
    g, p = predict_tags(best, make("dev", False), id2label, device)
    card["dev"] = entity_prf(g, p)
    if "test" in enc:
        g, p = predict_tags(best, make("test", False), id2label, device)
        card["test"] = entity_prf(g, p)
        card["test"]["micro_f1_ci95_bootstrap"] = list(bootstrap_f1_ci(g, p))
        log(f"TEST micro-F1={card['test']['micro']['f1']} CI95={card['test']['micro_f1_ci95_bootstrap']}")
    if getattr(args, "save_probs", False):
        dump = {}
        for split in ("dev", "test"):
            if split in enc:
                probs = predict_probs(best, make(split, False), device)
                dump[split] = [{"words": raw[split][i][0][:len(p)], "gold": raw[split][i][1][:len(p)], "probs": p}
                               for i, p in enumerate(probs)]
        (out_dir / "probs.json").write_text(json.dumps(dump, ensure_ascii=False), encoding="utf-8")
    (out_dir / "label_list.json").write_text(json.dumps(LABEL_LIST, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "model_card.json").write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    return card


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="vinai/phobert-base (Việt) hoặc SIKU-BERT/sikubert (Hán)")
    ap.add_argument("--data-dir", required=True, type=Path, help="thư mục chứa train.conll, dev.conll, [test.conll]")
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--max-length", type=int, default=256)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--save-probs", action="store_true", help="ghi probs.json (xác suất từng từ trên dev/test)")
    ap.add_argument("--test-split", default="test_human", help="tên tệp test (không đuôi); mặc định test_human = gold người soát")
    train(ap.parse_args(argv))
    return 0


if __name__ == "__main__":
    sys.exit(main())
