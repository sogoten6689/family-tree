import pytest

from label_studio_pipeline import analyze_probs as ap
from label_studio_pipeline.train_ner import LABEL_LIST


def onehot(label, p=0.9):
    v = [(1 - p) / (len(LABEL_LIST) - 1)] * len(LABEL_LIST)
    v[LABEL_LIST.index(label)] = p
    return v


def sent(words, gold, pred_labels, p=0.9):
    return {"words": words, "gold": gold, "probs": [onehot(l, p) for l in pred_labels]}


def test_repair_bio_and_decode():
    assert ap.repair_bio(["I-LOC", "I-LOC", "O", "I-DATE"]) == ["B-LOC", "I-LOC", "O", "B-DATE"]
    assert ap.decode_word(onehot("B-LOC", 0.9), {"LOC": 0.5}) == "B-LOC"
    assert ap.decode_word(onehot("I-LOC", 0.4), {"LOC": 0.5}) == "O"  # dưới ngưỡng
    assert ap.decode_word(onehot("O", 0.99), {}) == "O"


def test_threshold_trades_recall_for_precision():
    folds = [[sent(["a", "b"], ["B-LOC", "O"], ["B-LOC", "B-LOC"], 0.6)]]
    low = ap.score(folds, [0], {"LOC": 0.3})["micro"]
    high = ap.score(folds, [0], {"LOC": 0.9})["micro"]
    assert low["tp"] == 1 and low["fp"] == 1
    assert high["tp"] == 0 and high["fp"] == 0  # ngưỡng cao loại hết


def test_average_runs_and_mismatch():
    a = [[sent(["x"], ["B-LOC"], ["B-LOC"], 0.9)]]
    b = [[sent(["x"], ["B-LOC"], ["O"], 0.9)]]
    m = ap.average_runs([a, b])
    p = m[0][0]["probs"][0]
    assert abs(p[LABEL_LIST.index("B-LOC")] - (0.9 + 0.1 / 10) / 2) < 1e-6
    with pytest.raises(ValueError):
        ap.average_runs([a, [[sent(["y"], ["B-LOC"], ["B-LOC"])]]])


def test_nested_evaluate_runs():
    folds = [[sent(["a", "b"], ["B-LOC", "O"], ["B-LOC", "O"], 0.9)] for _ in range(5)]
    rep = ap.evaluate(folds)
    assert rep["pooled_default"]["f1"] == 1.0 and rep["nested_global"]["micro"]["f1"] == 1.0
    assert len(rep["nested_per_label_thresholds"]) == 5
