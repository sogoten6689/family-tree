"""NER chữ Hán mức ký tự (SikuBERT, ``NER_MODEL_DIR_HAN``) với session ONNX giả + tokenizer WordPiece giả."""

import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.ner import phobert_onnx as pn

LABELS = ["O", "B-PER_NAME", "I-PER_NAME", "B-DATE", "I-DATE", "B-GENERATION", "I-GENERATION", "B-ORDER", "I-ORDER", "B-LOC", "I-LOC"]
# id 0..3 cố ý KHÔNG theo thứ tự RoBERTa (<s>=0, </s>=2) để bắt lỗi lấy nhầm id đặc biệt.
VOCAB = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "始", "祖", "清", "閑", "公", "配", "陳", "氏", "生", "子", "。", "𠀋"]
ID = {t: i for i, t in enumerate(VOCAB)}
TAG_OF_ID = {ID["陳"]: "B-PER_NAME", ID["氏"]: "I-PER_NAME", ID["清"]: "B-PER_NAME", ID["閑"]: "I-PER_NAME"}


def make_model_dir(tmp_path: Path) -> Path:
    from tokenizers import Tokenizer, models, pre_tokenizers

    tok = Tokenizer(models.WordPiece({t: i for i, t in enumerate(VOCAB)}, unk_token="[UNK]"))
    tok.pre_tokenizer = pre_tokenizers.BertPreTokenizer()
    tok.save(str(tmp_path / "tokenizer.json"))
    (tmp_path / "label_list.json").write_text(json.dumps(LABELS), encoding="utf-8")
    return tmp_path


class FakeSession:
    """Nhãn suy từ id token (``TAG_OF_ID``); ghi lại mọi chuỗi id đã nhận để kiểm [CLS]/[SEP] và cách chia câu."""

    def __init__(self):
        self.calls: list[list[int]] = []

    def run(self, _, feeds):
        ids = [int(i) for i in feeds["input_ids"][0]]
        self.calls.append(ids)
        logits = np.full((len(ids), len(LABELS)), -5.0)
        for pos, i in enumerate(ids):
            logits[pos, LABELS.index(TAG_OF_ID.get(i, "O"))] = 5.0
        return [logits[None]]


def fake_model(tmp_path):
    return pn.NerModel(make_model_dir(tmp_path), session=FakeSession(), language="han")


def test_split_chars_skips_whitespace_and_keeps_code_point_offsets():
    text = "始 祖\n𠀋公"  # 𠀋 nằm ngoài BMP: 1 code point (2 đơn vị UTF-16)
    words = pn.split_chars(text)
    assert [(w.text, w.start, w.end) for w in words] == [("始", 0, 1), ("祖", 2, 3), ("𠀋", 4, 5), ("公", 5, 6)]


def test_han_sentences_end_after_period_and_cap_at_128():
    words = pn.split_chars("始祖。清閑公")
    assert pn.split_han_sentences(words) == [(0, 3), (3, 6)]
    long = pn.split_chars("公" * 300)
    assert pn.split_han_sentences(long) == [(0, 128), (128, 256), (256, 300)]
    assert pn.split_han_sentences(pn.split_chars("公" * 128 + "。")) == [(0, 128), (128, 129)]
    assert pn.split_han_sentences([]) == []


def test_bert_special_ids_come_from_tokenizer(tmp_path):
    t = pn.load_tokenizer(make_model_dir(tmp_path))
    assert (t.cls_id, t.pad_id, t.sep_id, t.unk_id) == (ID["[CLS]"], ID["[PAD]"], ID["[SEP]"], ID["[UNK]"])
    assert t.word_ids("陳") == [ID["陳"]] and t.word_ids("龍") == [ID["[UNK]"]]


def test_extract_offsets_spans_and_cls_sep(tmp_path):
    m = fake_model(tmp_path)
    text = "始祖 清閑公。配陳氏\n生子"
    ents = m.extract(text)
    assert [(e["label"], e["text"], e["start"], e["end"]) for e in ents] == [("PER_NAME", "清閑", 3, 5), ("PER_NAME", "陳氏", 8, 10)]
    assert all(text[e["start"]:e["end"]] == e["text"] for e in ents) and all(0.9 < e["confidence"] <= 1.0 for e in ents)
    # hai câu (tách sau 。, xuống dòng không tách); mỗi câu bọc [CLS] … [SEP], khoảng trắng không thành token
    assert m.session.calls == [
        [ID["[CLS]"]] + [ID[c] for c in "始祖清閑公。"] + [ID["[SEP]"]],
        [ID["[CLS]"]] + [ID[c] for c in "配陳氏生子"] + [ID["[SEP]"]],
    ]


def test_extract_long_text_is_split_into_128_char_sentences(tmp_path):
    m = fake_model(tmp_path)
    text = "公" * 127 + "陳氏" + "公" * 10  # thực thể vắt qua ranh giới 128 ký tự → bị cắt làm hai
    ents = m.extract(text)
    assert [len(ids) - 2 for ids in m.session.calls] == [128, 11]
    assert [(e["text"], e["start"], e["end"]) for e in ents] == [("陳", 127, 128), ("氏", 128, 129)]
    assert ents[1]["label"] == "PER_NAME"  # I-PER_NAME mồ côi ở đầu câu mới vẫn mở span


def test_get_ner_model_han_unavailable(monkeypatch, tmp_path):
    monkeypatch.delenv("NER_MODEL_DIR_HAN", raising=False)
    with pytest.raises(pn.NerUnavailable, match="NER_MODEL_DIR_HAN"):
        pn.get_ner_model("han")
    (tmp_path / "model.int8.onnx").write_bytes(b"")
    (tmp_path / "label_list.json").write_text(json.dumps(LABELS), encoding="utf-8")
    monkeypatch.setenv("NER_MODEL_DIR_HAN", str(tmp_path))
    with pytest.raises(pn.NerUnavailable, match="tokenizer.json"):
        pn.get_ner_model("han")


def test_get_ner_model_han_onnx_file_option(monkeypatch, tmp_path):
    # SikuBERT chạy fp32 (int8 mất ~23% thực thể): NER_ONNX_FILE_HAN chọn tệp, mặc định vẫn model.int8.onnx.
    monkeypatch.setattr(pn, "_cache", {})
    make_model_dir(tmp_path)
    (tmp_path / "model.int8.onnx").write_bytes(b"")
    monkeypatch.setenv("NER_MODEL_DIR_HAN", str(tmp_path))
    monkeypatch.setenv("NER_ONNX_FILE_HAN", "model.onnx")
    with pytest.raises(pn.NerUnavailable, match="model.onnx"):
        pn.get_ner_model("han")

    opened = []

    class FakeOrt:
        class SessionOptions:
            intra_op_num_threads = 1

        @staticmethod
        def InferenceSession(path, *_, **__):
            opened.append(Path(path).name)
            return FakeSession()

    monkeypatch.setitem(__import__("sys").modules, "onnxruntime", FakeOrt)
    (tmp_path / "model.onnx").write_bytes(b"")
    m = pn.get_ner_model("han")
    assert opened == ["model.onnx"] and m.precision == "fp32"
    monkeypatch.delenv("NER_ONNX_FILE_HAN")
    assert pn.get_ner_model("han").precision == "int8" and opened == ["model.onnx", "model.int8.onnx"]


def test_endpoint_hannom(monkeypatch, tmp_path):
    import api

    client = TestClient(api.app)
    body = {"text": "始祖清閑公。配陳氏", "language": "hannom", "model_version": "sikubert"}
    monkeypatch.delenv("NER_MODEL_DIR_HAN", raising=False)
    r = client.post("/api/genealogy/extract", json=body).json()
    assert r["success"] is False and r["data"] is None and "NER_MODEL_DIR_HAN" in r["error"]

    asked = []

    def only_han(lang="vi"):
        asked.append(lang)
        if lang != "han":
            raise pn.NerUnavailable(f"Chưa cấu hình model cho {lang}")
        return fake_model(tmp_path)

    monkeypatch.setattr("app.ner.get_ner_model", only_han)
    r = client.post("/api/genealogy/extract", json=body).json()
    assert r["success"] is True and asked == ["han"]
    data = r["data"]
    assert data["persons"] == ["清閑", "陳氏"] and data["relations"] == []
    assert [(e["start"], e["end"]) for e in data["entities"]] == [(2, 4), (7, 9)]
    info = data["model_info"]
    assert info["language"] == "hannom" and "SikuBERT" in info["model_name"] and "ONNX int8" in info["model_name"]
    assert "NHÃN MÁY" in info["note"] and "Gemini" in info["note"] and "CHƯA được người soát" in info["note"]
    assert "chưa có quan hệ" in info["note"]

    # chỉ cần một trong hai: language="hannom" hoặc model_version="sikubert"
    for alt in ({"language": "hannom", "model_version": "ner"}, {"language": "vietnamese", "model_version": "sikubert"}):
        assert client.post("/api/genealogy/extract", json={**body, **alt}).json()["success"] is True
    assert asked == ["han", "han", "han"]
