import json
import zipfile

from label_studio_pipeline import prepare_retrain as pr


def write_tree(base, tid, text, entities):
    d = base / str(tid)
    d.mkdir(parents=True)
    (d / "gold.training.json").write_text(json.dumps({"text": text, "entities": entities, "relations": []}, ensure_ascii=False), encoding="utf-8")


def make(base, ids, offset=0):
    for i in ids:
        name = f"Ông Nguyễn Văn Số{i + offset} sinh năm {1900 + i}. Quê ở làng Bình Hòa số {i}."
        s = name.index("Nguyễn")
        write_tree(base, i, name, [{"start": s, "end": s + 16 if False else name.index(" sinh"), "label": "PER_NAME",
                                    "text": name[s:name.index(" sinh")]}])


def test_end_to_end(tmp_path):
    old, new, out = tmp_path / "old", tmp_path / "new", tmp_path / "out"
    make(old, range(1, 11))
    make(new, [10, 11, 12], offset=100)  # cây 10 bị ghi đè
    m = pr.prepare(old, new, out, folds=5, progress=lambda *_: None)
    assert m["merge"]["total"] == 12 and m["merge"]["overridden"] == ["10"]
    assert m["trees_used"] == 12 and m["final"]["train"] + m["final"]["dev"] == 12
    for name in ("vi_cv5.zip", "vi_final.zip", "manifest.json", "clean_report.json"):
        assert (out / name).exists(), name
    names = zipfile.ZipFile(out / "vi_cv5.zip").namelist()
    assert "vi_cv5/fold0/train.conll" in names and "vi_cv5/folds.json" in names
    folds = json.loads(zipfile.ZipFile(out / "vi_cv5.zip").read("vi_cv5/folds.json"))["folds"]
    tests = sorted(t for f in folds for t in f["test"])
    assert tests == sorted(m["tree_ids"])  # mỗi cây làm test đúng 1 lần
    assert all(not set(f["train"]) & set(f["test"]) for f in folds)


def test_duplicate_documents_are_dropped(tmp_path):
    old, out = tmp_path / "old", tmp_path / "out"
    make(old, range(1, 13))
    same = (old / "1" / "gold.training.json").read_text(encoding="utf-8")
    (old / "99").mkdir()
    (old / "99" / "gold.training.json").write_text(same, encoding="utf-8")
    m = pr.prepare(old, None, out, folds=5, progress=lambda *_: None)
    assert m["duplicates_dropped"] == ["99"] and "99" not in m["tree_ids"]


def test_final_split_has_minimum_dev():
    tr, dev = pr.final_split([str(i) for i in range(10)])
    assert len(dev) == 3 and not set(tr) & set(dev)
