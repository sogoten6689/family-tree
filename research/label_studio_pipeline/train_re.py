"""Fine-tune bộ phân loại QUAN HỆ giữa hai tên người (xem ``build_re_dataset.py``). Chạy trên Colab (GPU).

    python train_re.py --model xlm-roberta-base --data-dir re_v1 --output-dir out_re

Chỉ số: F1 mức quan hệ (khớp (đầu, đuôi, loại); ``SPOUSE`` không phân biệt chiều) trên các cặp NẰM TRONG cửa sổ, và
recall đầu-cuối (tính cả quan hệ nằm ngoài cửa sổ nên model không xét tới). Test chỉ ~30 quan hệ → kèm khoảng tin cậy bootstrap.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Optional, Sequence

LABELS = ["NONE", "FATHER_OF", "MOTHER_OF", "SPOUSE"]


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def canon(row: dict, label: str) -> tuple:
    a, b = row["head"], row["tail"]
    if label == "SPOUSE":
        a, b = sorted((a, b))
    return (row["tree"], a, b, label)


def relation_prf(rows: Sequence[dict], preds: Sequence[str], out_of_window_gold: int = 0) -> dict:
    gold = {canon(r, r["label"]) for r in rows if r["label"] != "NONE"}
    pred = {canon(r, p) for r, p in zip(rows, preds) if p != "NONE"}
    tp = len(gold & pred)
    p = tp / len(pred) if pred else 0.0
    r_ = tp / len(gold) if gold else 0.0
    f1 = 2 * p * r_ / (p + r_) if p + r_ else 0.0
    e2e = tp / (len(gold) + out_of_window_gold) if gold or out_of_window_gold else 0.0
    return {"precision": round(p, 4), "recall_in_window": round(r_, 4), "f1": round(f1, 4), "recall_end_to_end": round(e2e, 4),
            "tp": tp, "fp": len(pred) - tp, "fn_in_window": len(gold) - tp, "gold_in_window": len(gold), "gold_out_of_window": out_of_window_gold}


def per_type(rows: Sequence[dict], preds: Sequence[str]) -> dict:
    out = {}
    for t in LABELS[1:]:
        g = {canon(r, t) for r in rows if r["label"] == t}
        p = {canon(r, t) for r, pr in zip(rows, preds) if pr == t}
        tp = len(g & p)
        out[t] = {"gold": len(g), "pred": len(p), "tp": tp}
    return out


def bootstrap_f1_ci(rows: list[dict], preds: list[str], out_of_window_gold: int, n: int = 1000, seed: int = 0) -> list[float]:
    """Lấy mẫu lại theo CÂY."""
    rng = random.Random(seed)
    trees = sorted({r["tree"] for r in rows})
    by_tree = {t: [i for i, r in enumerate(rows) if r["tree"] == t] for t in trees}
    scores = []
    for _ in range(n):
        idx = [i for t in (rng.choice(trees) for _ in trees) for i in by_tree[t]]
        scores.append(relation_prf([rows[i] for i in idx], [preds[i] for i in idx], 0)["f1"])
    scores.sort()
    return [scores[int(0.025 * n)], scores[int(0.975 * n) - 1]]


def train(args: argparse.Namespace, log=print) -> dict:
    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    d = Path(args.data_dir)
    data = {s: read_jsonl(d / f"{s}.jsonl") for s in ("train", "dev", "test")}
    stats = json.loads((d / "stats.json").read_text(encoding="utf-8"))
    l2i = {l: i for i, l in enumerate(LABELS)}
    tok = AutoTokenizer.from_pretrained(args.model)
    tok.add_tokens(["<h>", "</h>", "<t>", "</t>"])
    model = AutoModelForSequenceClassification.from_pretrained(args.model, num_labels=len(LABELS), id2label=dict(enumerate(LABELS)), label2id=l2i)
    model.resize_token_embeddings(len(tok))
    model.to(device)

    def loader(split, shuffle):
        def collate(batch):
            enc = tok([b["text"] for b in batch], truncation=True, max_length=args.max_length, padding=True, return_tensors="pt")
            enc["labels"] = torch.tensor([l2i[b["label"]] for b in batch])
            return enc
        return DataLoader(data[split], batch_size=args.batch_size, shuffle=shuffle, collate_fn=collate)

    def predict(split):
        model.eval()
        preds, probs = [], []
        with torch.no_grad():
            for batch in loader(split, False):
                batch = {k: v.to(device) for k, v in batch.items() if k != "labels"}
                p = torch.softmax(model(**batch).logits.float(), -1).cpu()
                probs += p.tolist()
                preds += [LABELS[i] for i in p.argmax(-1).tolist()]
        return preds, probs

    train_loader = loader("train", True)
    counts = [sum(1 for r in data["train"] if r["label"] == l) for l in LABELS]
    weights = torch.tensor([len(data["train"]) / (len(LABELS) * max(1, c)) for c in counts], dtype=torch.float, device=device)
    loss_fn = torch.nn.CrossEntropyLoss(weight=weights)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    steps = len(train_loader) * args.epochs
    sched = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)
    best, best_ep, hist = -1.0, 0, []
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    dev_miss = stats["splits"]["dev"]["gold_out_of_window"]
    for ep in range(1, args.epochs + 1):
        model.train()
        tot = 0.0
        for batch in train_loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            labels = batch.pop("labels")
            loss = loss_fn(model(**batch).logits, labels)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            tot += loss.item()
        dp, _ = predict("dev")
        dev = relation_prf(data["dev"], dp, dev_miss)
        hist.append({"epoch": ep, "train_loss": round(tot / len(train_loader), 4), "dev_f1": dev["f1"]})
        log(f"epoch {ep}: loss={hist[-1]['train_loss']} dev_F1={dev['f1']} (P {dev['precision']} R {dev['recall_in_window']})")
        if dev["f1"] > best:
            best, best_ep = dev["f1"], ep
            model.save_pretrained(out)
            tok.save_pretrained(out)
    model = AutoModelForSequenceClassification.from_pretrained(out).to(device)
    tp_, tprobs = predict("test")
    dp_, dprobs = predict("dev")
    miss = stats["splits"]["test"]["gold_out_of_window"]
    card = {"base_model": args.model, "task": "relation-classification", "labels": LABELS, "best_epoch": best_ep,
            "hyperparameters": {k: getattr(args, k) for k in ("epochs", "lr", "batch_size", "max_length", "seed")}, "history": hist, "data_stats": stats,
            "dev": relation_prf(data["dev"], dp_, dev_miss),
            "test": relation_prf(data["test"], tp_, miss) | {"per_type": per_type(data["test"], tp_),
                                                              "f1_ci95_bootstrap_by_tree": bootstrap_f1_ci(data["test"], tp_, miss)},
            "caveat": "train/dev dùng nhãn quan hệ của Gemini (chưa người soát); test chỉ ~30 quan hệ người soát"}
    (out / "model_card.json").write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "test_predictions.json").write_text(json.dumps(
        [{**r, "pred": p, "probs": [round(x, 4) for x in pr]} for r, p, pr in zip(data["test"], tp_, tprobs)], ensure_ascii=False), encoding="utf-8")
    log("TEST: " + json.dumps({k: card["test"][k] for k in ("precision", "recall_in_window", "f1", "recall_end_to_end", "f1_ci95_bootstrap_by_tree")}, ensure_ascii=False))
    return card


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="xlm-roberta-base")
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--max-length", type=int, default=192)
    ap.add_argument("--seed", type=int, default=42)
    train(ap.parse_args(argv))
    return 0


if __name__ == "__main__":
    sys.exit(main())
