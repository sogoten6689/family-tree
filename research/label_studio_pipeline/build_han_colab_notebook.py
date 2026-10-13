"""Sinh notebook Colab huấn luyện NER chữ Hán (SikuBERT so với XLM-R-base), dữ liệu và mã NHÚNG SẴN (không cần Google Drive).

Notebook chứa dữ liệu dự án nên KHÔNG đưa vào git; ghi ra thư mục dữ liệu (`data/03_derived/han_ner_v1/`).
TỐN TIỀN (GPU Colab). Notebook tự ngắt runtime ở ô cuối.

    python -m label_studio_pipeline.build_han_colab_notebook --data-dir <han_ner_v1> --out <notebook.ipynb>
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import zipfile
from pathlib import Path

TRAIN_SCRIPT = Path(__file__).resolve().parent / "train_ner.py"

MODELS = [
    {"name": "SIKU-BERT/sikubert", "tag": "siku", "lr": 5e-5, "max_length": 256},
    {"name": "xlm-roberta-base", "tag": "xlmr", "lr": 3e-5, "max_length": 320},
]
EPOCHS = 10
BATCH = 16


def pack(data_dir: Path) -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for sub in ("han_cv5", "han_final"):
            for path in sorted((data_dir / sub).rglob("*.conll")):
                zf.write(path, path.relative_to(data_dir).as_posix())
        zf.write(TRAIN_SCRIPT, "train_ner.py")
        zf.write(data_dir / "dataset_summary.json", "dataset_summary.json")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def cell(kind: str, source: str) -> dict:
    base = {"cell_type": kind, "metadata": {}, "source": source.splitlines(keepends=True)}
    return base | ({"execution_count": None, "outputs": []} if kind == "code" else {})


def build(data_dir: Path) -> dict:
    models = json.dumps(MODELS, ensure_ascii=False)
    cells = [
        cell("markdown", "# NER chữ Hán (mức ký tự): SikuBERT so với XLM-R-base\n"
             "**Tốn tiền (GPU Colab).** Dữ liệu là NHÃN MÁY (Gemini) nên F1 kiểm chéo chỉ đo mô hình học được nhãn máy tới đâu, "
             "KHÔNG phải độ chính xác thật. Kiểm chéo 5 lượt theo SÁCH + bản cuối trên 15 trang test (nhãn người sẽ chấm sau). "
             "Không cần Drive. Ô cuối tự ngắt runtime."),
        cell("code", "import base64\nopen('/content/han_data.zip','wb').write(base64.b64decode('" + pack(data_dir) + "'))\nprint('đã ghi han_data.zip')\n"),
        cell("code", '!pip -q install "transformers>=4.40" sentencepiece\n'
             "import torch; assert torch.cuda.is_available(), 'Chưa bật GPU (Runtime > Change runtime type > T4)'\n"
             "major, minor = (int(x) for x in torch.__version__.split('+')[0].split('.')[:2])\n"
             "assert (major, minor) >= (2, 6), f'torch {torch.__version__} < 2.6: SikuBERT chỉ có trọng số .bin nên cần torch >= 2.6'\n"
             "print(torch.cuda.get_device_name(0))\n!cd /content && unzip -qo han_data.zip && ls\n"),
        cell("code", "import subprocess, json, shutil, os, time\n"
             f"MODELS = {models}\nEPOCHS, BATCH = {EPOCHS}, {BATCH}\nos.makedirs('/content/results', exist_ok=True)\n"
             "def run(model, data_dir, out, extra=()):\n"
             "    t = time.time()\n"
             "    cmd = ['python', '/content/train_ner.py', '--model', model['name'], '--data-dir', data_dir, '--output-dir', out,\n"
             "           '--test-split', 'test', '--epochs', str(EPOCHS), '--lr', str(model['lr']), '--batch-size', str(BATCH),\n"
             "           '--max-length', str(model['max_length']), *extra]\n"
             "    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)\n"
             "    return time.time() - t\n"
             "for m in MODELS:\n"
             "    for k in range(5):\n"
             "        out = f'/content/out/{m[\"tag\"]}_fold{k}'\n"
             "        secs = run(m, f'/content/han_cv5/fold{k}', out)\n"
             "        card = json.load(open(f'{out}/model_card.json'))\n"
             "        shutil.copy(f'{out}/model_card.json', f'/content/results/{m[\"tag\"]}_fold{k}_model_card.json')\n"
             "        shutil.rmtree(out)\n"
             "        t = card['test']['micro']\n"
             "        print(f'{m[\"tag\"]} fold{k}: test F1={t[\"f1\"]} P={t[\"precision\"]} R={t[\"recall\"]} ({secs/60:.1f} phút)', flush=True)\n"),
        cell("code", "from collections import Counter\n"
             "def prf(d):\n"
             "    p = d['tp']/(d['tp']+d['fp']) if d['tp']+d['fp'] else 0; r = d['tp']/(d['tp']+d['fn']) if d['tp']+d['fn'] else 0\n"
             "    return dict(P=round(p,3), R=round(r,3), F1=round(2*p*r/(p+r),3) if p+r else 0)\n"
             "summary = {}\n"
             "for m in MODELS:\n"
             "    tot, labels = Counter(), {}\n"
             "    for k in range(5):\n"
             "        c = json.load(open(f'/content/results/{m[\"tag\"]}_fold{k}_model_card.json'))['test']\n"
             "        for key in ('tp','fp','fn'): tot[key] += c['micro'][key]\n"
             "        for l, v in c['per_label'].items():\n"
             "            d = labels.setdefault(l, Counter())\n"
             "            for key in ('tp','fp','fn'): d[key] += v[key]\n"
             "    summary[m['tag']] = {'micro': prf(tot), 'labels': {l: prf(d) for l, d in labels.items()}}\n"
             "    print('GỘP 5 LƯỢT', m['tag'], summary[m['tag']]['micro'])\n"
             "    for l, v in summary[m['tag']]['labels'].items(): print('   ', l, v)\n"
             "json.dump(summary, open('/content/results/cv_summary.json','w'), ensure_ascii=False, indent=1)\n"),
        cell("code", "for m in MODELS:\n"
             "    out = f'/content/out/{m[\"tag\"]}_final'\n"
             "    secs = run(m, '/content/han_final', out, extra=('--save-probs',))\n"
             "    card = json.load(open(f'{out}/model_card.json'))\n"
             "    for name in ('model_card.json', 'probs.json', 'label_list.json'):\n"
             "        shutil.copy(f'{out}/{name}', f'/content/results/{m[\"tag\"]}_final_{name}')\n"
             "    shutil.rmtree(out)\n"
             "    print(f'{m[\"tag\"]} BẢN CUỐI: dev F1={card[\"dev\"][\"micro\"][\"f1\"]}  test15(nhãn máy) F1={card[\"test\"][\"micro\"][\"f1\"]} ({secs/60:.1f} phút)', flush=True)\n"),
        cell("code", "!cd /content/results && zip -qr /content/han_ner_results.zip . && ls -la /content/han_ner_results.zip\n"
             "from google.colab import files\nfiles.download('/content/han_ner_results.zip')\n"),
        cell("code", "from google.colab import runtime\nruntime.unassign()   # NGẮT RUNTIME để dừng tính tiền\n"),
    ]
    return {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"provenance": []}, "kernelspec": {"display_name": "Python 3", "name": "python3"}}, "nbformat": 4, "nbformat_minor": 5}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    notebook = build(args.data_dir)
    args.out.write_text(json.dumps(notebook, ensure_ascii=False), encoding="utf-8")
    print(f"đã ghi {args.out} ({args.out.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
