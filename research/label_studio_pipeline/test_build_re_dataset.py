import json
import random

from label_studio_pipeline import build_re_dataset as b


def doc():
    text = "Ông Nguyễn Văn An sinh Nguyễn Văn Bình. Bà Trần Thị Hoa vợ ông An."
    def span(s, label="PER_NAME"):
        i = text.index(s)
        return {"start": i, "end": i + len(s), "label": label, "text": s}
    ents = [span("Nguyễn Văn An"), span("Nguyễn Văn Bình"), span("Trần Thị Hoa"), span("Hà Nội" if False else "Ông", "DATE")]
    return {"text": text, "entities": ents, "relations": [{"type": "FATHER_OF", "head": 0, "tail": 1}, {"type": "SPOUSE", "head": 0, "tail": 2}]}


def test_mark_pair_inserts_markers_in_order():
    d = doc()
    m = b.mark_pair(d["text"], d["entities"][0], d["entities"][1], ctx=5)
    assert "<h>Nguyễn Văn An</h>" in m and "<t>Nguyễn Văn Bình</t>" in m and m.index("<h>") < m.index("<t>")
    m2 = b.mark_pair(d["text"], d["entities"][1], d["entities"][0], ctx=5)  # đầu đứng sau đuôi
    assert "<h>Nguyễn Văn Bình</h>" in m2 and "<t>Nguyễn Văn An</t>" in m2


def test_pairs_labels_and_spouse_symmetry():
    pairs, info = b.build_pairs(doc(), "1")
    by = {(p["head"], p["tail"]): p["label"] for p in pairs}
    assert by[(0, 1)] == "FATHER_OF" and by[(1, 0)] == "NONE"
    assert by[(0, 2)] == "SPOUSE" and by[(2, 0)] == "SPOUSE"
    assert all(p["head"] != 3 and p["tail"] != 3 for p in pairs)  # chỉ PER_NAME
    assert info == {"gold_relations": 2, "gold_out_of_window": 0}


def test_window_counts_missed_gold():
    _, info = b.build_pairs(doc(), "1", window=5)
    assert info["gold_out_of_window"] >= 1


def test_downsample_keeps_all_positives():
    rows = [{"label": "FATHER_OF"}] + [{"label": "NONE"}] * 20
    out = b.downsample_negatives(rows, 3.0, random.Random(0))
    assert sum(r["label"] == "FATHER_OF" for r in out) == 1 and sum(r["label"] == "NONE" for r in out) == 3


def test_build_end_to_end_no_leak(tmp_path):
    sil, hum = tmp_path / "s", tmp_path / "h"
    for base, ids in ((sil, range(1, 13)), (hum, [3, 99])):
        for i in ids:
            (base / str(i)).mkdir(parents=True)
            (base / str(i) / "gold.training.json").write_text(json.dumps(doc(), ensure_ascii=False), encoding="utf-8")
    st = b.build(sil, hum, tmp_path / "o")
    assert st["splits"]["test"]["trees"] == 2  # cây 3 và 99 của tập người soát
    train_trees = {json.loads(l)["tree"] for l in (tmp_path / "o" / "train.jsonl").read_text(encoding="utf-8").splitlines()}
    assert "3" not in train_trees  # cây người soát không rò vào train
