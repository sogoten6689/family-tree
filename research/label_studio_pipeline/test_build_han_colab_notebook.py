import ast
import base64
import io
import json
import zipfile

from label_studio_pipeline import build_han_colab_notebook as n


def make_data(tmp_path):
    for sub in ("han_cv5/fold0", "han_final"):
        d = tmp_path / sub
        d.mkdir(parents=True)
        for split in ("train", "dev", "test"):
            (d / f"{split}.conll").write_text("清\tB-PER_NAME\n閑\tI-PER_NAME\n\n", encoding="utf-8")
    (tmp_path / "dataset_summary.json").write_text("{}", encoding="utf-8")
    return tmp_path


def test_notebook_embeds_data_and_script_and_is_valid_python(tmp_path):
    nb = n.build(make_data(tmp_path))
    code = [c for c in nb["cells"] if c["cell_type"] == "code"]
    first = "".join(code[0]["source"])
    payload = first.split("b64decode('")[1].split("')")[0]
    names = zipfile.ZipFile(io.BytesIO(base64.b64decode(payload))).namelist()
    assert "train_ner.py" in names and "han_final/train.conll" in names and "han_cv5/fold0/test.conll" in names
    for cell in code:  # mọi ô code phải có cú pháp hợp lệ (bỏ dòng lệnh shell bắt đầu bằng !)
        ast.parse("\n".join(l for l in "".join(cell["source"]).splitlines() if not l.startswith("!")))
    assert json.dumps(nb)  # serialize được


def test_notebook_checks_gpu_and_torch_version_and_releases_runtime(tmp_path):
    text = "\n".join("".join(c["source"]) for c in n.build(make_data(tmp_path))["cells"])
    assert "torch.cuda.is_available()" in text and ">= (2, 6)" in text
    assert "runtime.unassign()" in text  # ô cuối ngắt runtime để dừng tính tiền
    assert "SIKU-BERT/sikubert" in text and "xlm-roberta-base" in text
