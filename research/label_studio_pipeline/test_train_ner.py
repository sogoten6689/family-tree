import pytest

from label_studio_pipeline import train_ner as tn

L2I = {l: i for i, l in enumerate(tn.LABEL_LIST)}


class FakeTok:
    cls_token_id, sep_token_id, unk_token_id, pad_token_id = 0, 1, 2, 3

    def tokenize(self, w):  # từ dài chia 2 subword để kiểm tra căn nhãn
        return [w[:2], w[2:]] if len(w) > 2 else [w]

    def convert_tokens_to_ids(self, toks):
        return [10 + sum(map(ord, t)) % 50 for t in toks]


def test_read_conll_and_bad_tag(tmp_path):
    p = tmp_path / "a.conll"
    p.write_text("Nguyễn\tB-PER_NAME\nVăn\tI-PER_NAME\n\nsinh\tO\n", encoding="utf-8")
    assert tn.read_conll(p) == [(["Nguyễn", "Văn"], ["B-PER_NAME", "I-PER_NAME"]), (["sinh"], ["O"])]
    p.write_text("x\tB-FOO\n", encoding="utf-8")
    with pytest.raises(ValueError):
        tn.read_conll(p)


def test_encode_labels_only_first_subword():
    e = tn.encode_sentence(["abcd", "e"], ["B-LOC", "O"], FakeTok(), 16, L2I)
    assert e["labels"] == [-100, L2I["B-LOC"], -100, L2I["O"], -100]
    assert len(e["input_ids"]) == len(e["labels"]) and e["input_ids"][0] == 0 and e["input_ids"][-1] == 1


def test_encode_truncates_to_max_length():
    e = tn.encode_sentence(["ab"] * 50, ["O"] * 50, FakeTok(), 10, L2I)
    assert len(e["input_ids"]) <= 10 and e["input_ids"][-1] == 1


def test_bio_to_spans_handles_orphan_I_and_adjacent():
    assert tn.bio_to_spans(["B-LOC", "I-LOC", "O", "I-DATE", "B-DATE", "B-DATE"]) == {
        (0, 2, "LOC"), (3, 4, "DATE"), (4, 5, "DATE"), (5, 6, "DATE")}
    assert tn.bio_to_spans(["B-LOC", "I-DATE"]) == {(0, 1, "LOC"), (1, 2, "DATE")}


def test_entity_prf_strict():
    gold = [["B-PER_NAME", "I-PER_NAME", "O", "B-LOC"]]
    pred = [["B-PER_NAME", "O", "O", "B-LOC"]]  # tên bị cắt = sai strict
    r = tn.entity_prf(gold, pred)
    assert r["per_label"]["LOC"]["f1"] == 1.0
    assert r["per_label"]["PER_NAME"] == {"precision": 0.0, "recall": 0.0, "f1": 0.0, "tp": 0, "fp": 1, "fn": 1}
    assert r["micro"]["tp"] == 1 and r["micro"]["fp"] == 1 and r["micro"]["fn"] == 1


def test_bootstrap_ci_brackets_point_estimate():
    gold = [["B-LOC", "O"]] * 20 + [["O", "B-DATE"]] * 20
    pred = [["B-LOC", "O"]] * 20 + [["O", "O"]] * 20
    lo, hi = tn.bootstrap_f1_ci(gold, pred, n=200)
    assert lo <= tn.entity_prf(gold, pred)["micro"]["f1"] <= hi


def test_forbidden_model_refused(tmp_path):
    args = tn.argparse.Namespace(model="vinai/phobert-base-v2", data_dir=tmp_path, output_dir=tmp_path,
                                 epochs=1, lr=1e-5, batch_size=1, max_length=8, seed=0, test_split="test_human")
    with pytest.raises(SystemExit):
        tn.train(args)


def test_collate_pads():
    b = tn.collate([{"input_ids": [0, 5, 1], "labels": [-100, 1, -100]}, {"input_ids": [0, 1], "labels": [-100, -100]}], 3)
    assert b["input_ids"].shape == (2, 3) and b["attention_mask"].tolist() == [[1, 1, 1], [1, 1, 0]]
