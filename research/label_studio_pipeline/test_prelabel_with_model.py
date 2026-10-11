import json

from label_studio_pipeline import prelabel_with_model as pm


def doc(text, ents=()):
    return {"text": text, "title": "t", "source_url": "u", "entities": list(ents)}


def ent(text, start, label="PER_NAME", confidence=0.9):
    return {"label": label, "text": text, "start": start, "end": start + len(text), "confidence": confidence}


def test_build_task_regions_and_scores():
    d = doc("Ông Lan ở Hà Nội")
    ents = [ent("Lan", 4), ent("Hà Nội", 10, "LOC", 0.7)]
    t = pm.build_task(d, ents, 5)
    pred = t["predictions"][0]
    assert t["data"]["tree_id"] == 5 and pred["model_version"] == pm.MODEL_VERSION
    regs = pred["result"]
    assert [r["value"]["labels"][0] for r in regs] == ["PER_NAME", "LOC"] and regs[1]["value"]["score"] == 0.7
    assert pred["score"] == 0.8 and all(r["value"]["text"] == d["text"][r["value"]["start"]:r["value"]["end"]] for r in regs)


def test_agreement():
    a = [ent("Lan", 4), ent("X", 20)]
    b = [{"start": 4, "end": 7, "label": "PER_NAME"}, {"start": 30, "end": 31, "label": "LOC"}]
    assert pm.agreement(a, b) == {"model": 2, "existing": 2, "agree": 1, "f1": 0.5}
    assert pm.agreement([], [])["f1"] == 0.0


def test_run_skips_human_and_orders_by_disagreement(tmp_path):
    docs, hum = tmp_path / "docs", tmp_path / "human"
    for tid, text, gold in (("1", "Ông Lan", [{"start": 4, "end": 7, "label": "PER_NAME", "text": "Lan"}]),
                            ("2", "Ông Mai", []), ("3", "Ông Hoa", [])):
        (docs / tid).mkdir(parents=True)
        (docs / tid / "gold.training.json").write_text(json.dumps(doc(text, gold), ensure_ascii=False), encoding="utf-8")
    (hum / "3").mkdir(parents=True)
    fake = lambda text: [ent(text[4:], 4)]
    s = pm.run(tmp_path, docs, hum, tmp_path / "out", None, extract=fake, progress=lambda *_: None)
    assert s["trees"] == 2 and s["excluded_human"] == 1
    rows = (tmp_path / "out" / "priority.csv").read_text(encoding="utf-8").splitlines()
    assert rows[1].startswith("2,")  # cây 2 lệch (f1=0) lên trước cây 1 (khớp hoàn toàn)
    assert len(json.loads((tmp_path / "out" / "tasks.json").read_text(encoding="utf-8"))) == 2
