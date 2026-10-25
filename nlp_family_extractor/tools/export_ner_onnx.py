"""Xuất model NER đã huấn luyện sang ONNX (+ lượng tử hoá int8) để chạy trên CPU của VPS, rồi ĐỐI CHIẾU với bản gốc.

Bản lưu trong repo của ``data/03_derived/colab_bundle/family_tree_ner/export_onnx.py`` (thư mục data bị gitignore).
Dùng chung cho tiếng Việt (PhoBERT/XLM-R) và chữ Hán (SikuBERT, BERT [CLS]/[SEP]: id lấy từ tokenizer nên không cần sửa gì).

    python tools/export_ner_onnx.py --model-dir out_final --output-dir onnx_out --sample-conll dev.conll

SikuBERT (thư mục tải từ Drive ``MyDrive/family_tree_ner/sikubert_family_han_v1/``: model.safetensors, tokenizer.json,
label_list.json, config.json; CoNLL mức ký tự)::

    python tools/export_ner_onnx.py --model-dir sikubert_family_han_v1 --output-dir han_onnx \
        --sample-conll data/03_derived/han_ner_v1/han_final/test.conll
    export NER_MODEL_DIR_HAN=$PWD/han_onnx   # API cần model.int8.onnx + tokenizer.json + label_list.json

Cần: torch, transformers, onnx, onnxruntime (``numpy<2`` nếu torch cũ biên dịch với NumPy 1.x).

Đầu ra: model.onnx (fp32), model.int8.onnx, tokenizer.json, label_list.json, onnx_report.json.
Báo cáo gồm: tỉ lệ nhãn khớp torch ↔ onnx (fp32, int8) trên câu mẫu, kích thước tệp, độ trễ CPU/câu, và số từ mà
``tokenizer.json`` (đường API dùng, thư viện ``tokenizers``) cho id KHÁC ``AutoTokenizer`` (đường huấn luyện) — phải bằng 0.
Độ trễ đo trên máy chạy script (Colab CPU ≠ VPS) — phải đo lại trên VPS trước khi cam kết.
"""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import sys
import time
from pathlib import Path
from typing import Optional, Sequence


def read_sentences(path: Path, limit: int) -> list[list[str]]:
    sents, cur = [], []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            if cur:
                sents.append(cur)
                cur = []
            continue
        cur.append(line.split("\t")[0])
    if cur:
        sents.append(cur)
    return sents[:limit]


def encode(words: Sequence[str], tokenizer, max_len: int = 256) -> tuple[list[int], list[int]]:
    """Giống train_ner.encode_sentence: mã hoá từng từ; trả (input_ids, vị trí subword đầu mỗi từ)."""
    ids, first = [tokenizer.cls_token_id], []
    for w in words:
        pieces = tokenizer.convert_tokens_to_ids(tokenizer.tokenize(w)) or [tokenizer.unk_token_id]
        if len(ids) + len(pieces) > max_len - 1:
            break
        first.append(len(ids))
        ids.extend(pieces)
    ids.append(tokenizer.sep_token_id)
    return ids, first


def _export_kwargs(torch) -> dict:
    """torch ≥ 2.5 mặc định có thể chọn exporter dynamo; ép exporter TorchScript. Torch cũ không có tham số ``dynamo``."""
    import inspect

    return {"dynamo": False} if "dynamo" in inspect.signature(torch.onnx.export).parameters else {}


def main(argv: Optional[Sequence[str]] = None) -> int:
    import numpy as np
    import onnxruntime as ort
    import torch
    from onnxruntime.quantization import QuantType, quantize_dynamic
    from transformers import AutoModelForTokenClassification, AutoTokenizer

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--sample-conll", type=Path, required=True, help="CoNLL để lấy câu mẫu đối chiếu/đo tốc độ")
    ap.add_argument("--samples", type=int, default=100)
    args = ap.parse_args(argv)
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    tok = AutoTokenizer.from_pretrained(args.model_dir)
    model = AutoModelForTokenClassification.from_pretrained(args.model_dir).eval().cpu()
    fp32, int8 = out / "model.onnx", out / "model.int8.onnx"

    dummy = torch.tensor([[tok.cls_token_id, 10, 11, tok.sep_token_id]])
    torch.onnx.export(
        model, (dummy, torch.ones_like(dummy)), str(fp32), input_names=["input_ids", "attention_mask"],
        output_names=["logits"], dynamic_axes={"input_ids": {0: "b", 1: "s"}, "attention_mask": {0: "b", 1: "s"}, "logits": {0: "b", 1: "s"}},
        opset_version=17, **_export_kwargs(torch))
    quantize_dynamic(str(fp32), str(int8), weight_type=QuantType.QInt8)

    sents = read_sentences(args.sample_conll, args.samples)
    sessions = {n: ort.InferenceSession(str(p), providers=["CPUExecutionProvider"]) for n, p in (("fp32", fp32), ("int8", int8))}
    agree = {"fp32": [0, 0], "int8": [0, 0]}
    lat = {"torch": [], "fp32": [], "int8": []}
    for words in sents:
        ids, first = encode(words, tok)
        x = torch.tensor([ids])
        mask = torch.ones_like(x)
        t0 = time.perf_counter()
        with torch.no_grad():
            ref = model(input_ids=x, attention_mask=mask).logits[0].argmax(-1).numpy()
        lat["torch"].append(time.perf_counter() - t0)
        for name, sess in sessions.items():
            t0 = time.perf_counter()
            logits = sess.run(None, {"input_ids": x.numpy(), "attention_mask": mask.numpy()})[0][0]
            lat[name].append(time.perf_counter() - t0)
            pred = logits.argmax(-1)
            agree[name][0] += int(sum(pred[i] == ref[i] for i in first))
            agree[name][1] += len(first)

    from tokenizers import Tokenizer

    tok_mismatch = []
    if (args.model_dir / "tokenizer.json").exists():
        api_tok = Tokenizer.from_file(str(args.model_dir / "tokenizer.json"))
        for w in sorted({w for words in sents for w in words}):
            hf_ids = tok.convert_tokens_to_ids(tok.tokenize(w)) or [tok.unk_token_id]
            if (list(api_tok.encode(w, add_special_tokens=False).ids) or [tok.unk_token_id]) != hf_ids:
                tok_mismatch.append(w)

    report = {
        "samples": len(sents),
        "tokenizer_json_mismatch": {"count": len(tok_mismatch), "examples": tok_mismatch[:20]},
        "size_mb": {"fp32": round(fp32.stat().st_size / 1e6, 1), "int8": round(int8.stat().st_size / 1e6, 1)},
        "label_agreement_with_torch": {k: round(v[0] / max(1, v[1]), 4) for k, v in agree.items()},
        "latency_ms_per_sentence": {k: {"median": round(statistics.median(v) * 1000, 1), "p95": round(sorted(v)[int(0.95 * len(v)) - 1] * 1000, 1)} for k, v in lat.items()},
        "cpu_threads": torch.get_num_threads(),
        "note": "đo trên máy chạy script, KHÔNG phải VPS",
    }
    (out / "onnx_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for name in ("tokenizer.json", "tokenizer_config.json", "label_list.json", "model_card.json", "config.json", "vocab.txt", "bpe.codes"):
        if (args.model_dir / name).exists():
            shutil.copy(args.model_dir / name, out / name)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
