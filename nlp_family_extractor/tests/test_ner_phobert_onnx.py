import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.ner import phobert_onnx as pn

LABELS = ["O", "B-PER_NAME", "I-PER_NAME", "B-DATE", "I-DATE", "B-GENERATION", "I-GENERATION", "B-ORDER", "I-ORDER", "B-LOC", "I-LOC"]


def make_model_dir(tmp_path: Path) -> Path:
    (tmp_path / "vocab.txt").write_text("a 5\nb 4\nab 3\nc 2\n", encoding="utf-8")
    (tmp_path / "bpe.codes").write_text("a b 9\n", encoding="utf-8")  # PhoBERT: dòng 'x y freq'
    (tmp_path / "label_list.json").write_text(json.dumps(LABELS), encoding="utf-8")
    return tmp_path


class FakeSession:
    """Gán B-PER_NAME cho token thứ 2 của câu (ngay sau [CLS] + từ đầu), còn lại O."""

    def run(self, _, feeds):
        ids = feeds["input_ids"][0]
        logits = np.full((len(ids), len(LABELS)), -5.0)
        logits[:, 0] = 5.0
        if len(ids) > 3:
            logits[2, 0], logits[2, 1] = -5.0, 5.0
        return [logits[None]]


def fake_model(tmp_path):
    d = make_model_dir(tmp_path)
    return pn.NerModel(d, session=FakeSession())


def test_split_words_and_sentences():
    text = "Ông Lan sinh năm 1900. Con là Hoa;\nBà Mai"
    words = pn.split_words(text)
    assert [w.text for w in words][:5] == ["Ông", "Lan", "sinh", "năm", "1900"]
    sents = pn.split_sentences(text, words)
    assert [" ".join(w.text for w in words[a:b]) for a, b in sents] == ["Ông Lan sinh năm 1900 .", "Con là Hoa ;", "Bà Mai"]


def test_long_sentence_is_cut():
    words = [pn.Word("x", i, i + 1) for i in range(300)]
    assert pn.split_sentences("x" * 300, words, max_tokens=128) == [(0, 128), (128, 256), (256, 300)]


def test_bio_to_spans():
    assert pn.bio_to_spans(["B-LOC", "I-LOC", "O", "I-DATE"]) == [(0, 2, "LOC"), (3, 4, "DATE")]


def test_extract_offsets_and_confidence(tmp_path):
    m = fake_model(tmp_path)
    text = "a ab c."  # mỗi từ đúng một subword → token thứ 2 là "ab"
    ents = m.extract(text)
    assert len(ents) == 1 and ents[0]["label"] == "PER_NAME" and text[ents[0]["start"]:ents[0]["end"]] == "ab" == ents[0]["text"]
    assert 0.9 < ents[0]["confidence"] <= 1.0


def test_bpe_matches_huggingface(tmp_path):
    tr = pytest.importorskip("transformers.models.phobert.tokenization_phobert")
    d = make_model_dir(tmp_path)
    hf = tr.PhobertTokenizer(str(d / "vocab.txt"), str(d / "bpe.codes"))
    mine = pn.PhobertBpe(d / "vocab.txt", d / "bpe.codes")
    for w in ["ab", "abc", "a", "cab", "Lan", "xyz", "abab"]:
        assert mine.word_ids(w) == (hf.convert_tokens_to_ids(hf.tokenize(w)) or [hf.unk_token_id]), w


def test_get_ner_model_unavailable(monkeypatch, tmp_path):
    monkeypatch.delenv("NER_MODEL_DIR_VI", raising=False)
    with pytest.raises(pn.NerUnavailable):
        pn.get_ner_model("vi")
    monkeypatch.setenv("NER_MODEL_DIR_VI", str(tmp_path))
    with pytest.raises(pn.NerUnavailable, match="Thiếu tệp"):
        pn.get_ner_model("vi")


def test_endpoint_phobert(monkeypatch, tmp_path):
    import api

    client = TestClient(api.app)
    body = {"text": "a ab c.", "language": "vietnamese", "model_version": "phobert"}
    monkeypatch.delenv("NER_MODEL_DIR_VI", raising=False)
    r = client.post("/api/genealogy/extract", json=body).json()
    assert r["success"] is False and "chưa sẵn sàng" in r["error"]

    monkeypatch.setattr("app.ner.get_ner_model", lambda lang="vi": fake_model(tmp_path))
    r = client.post("/api/genealogy/extract", json=body).json()
    assert r["success"] is True
    assert r["data"]["persons"] == ["ab"] and r["data"]["entities"][0]["label"] == "PER_NAME" and r["data"]["relations"] == []
    assert "PhoBERT" in r["data"]["model_info"]["model_name"]

    body["model_version"] = "sikubert"
    assert client.post("/api/genealogy/extract", json=body).json()["success"] is False


def test_tokenizer_json_path_and_loader_choice(tmp_path):
    from tokenizers import Tokenizer, models, pre_tokenizers

    vocab = {"<s>": 0, "<pad>": 1, "</s>": 2, "<unk>": 3, "▁ab": 4, "▁c": 5}
    tok = Tokenizer(models.WordLevel(vocab, unk_token="<unk>"))
    tok.pre_tokenizer = pre_tokenizers.Metaspace()
    d = make_model_dir(tmp_path)
    tok.save(str(d / "tokenizer.json"))
    t = pn.load_tokenizer(d)
    assert isinstance(t, pn.HFTokenizerJson)
    assert t.word_ids("ab") == [4] and t.word_ids("zzz") == [3]
    assert (t.cls_id, t.pad_id, t.sep_id, t.unk_id) == (0, 1, 2, 3)
    # không có tokenizer.json → quay về PhoBERT BPE
    (d / "tokenizer.json").unlink()
    assert isinstance(pn.load_tokenizer(d), pn.PhobertBpe)
