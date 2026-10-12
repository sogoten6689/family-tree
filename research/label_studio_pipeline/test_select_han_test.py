import json

from label_studio_pipeline import select_han_test as s


def doc(doc_id, scan, n_ent, text="家譜公", per=True):
    ents = [{"start": 0, "end": 1, "label": "PER_NAME" if per else "LOC", "text": "家"}] * n_ent
    return {"doc_id": doc_id, "text": text, "entities": ents, "relations": [], "model_version": "m", "provenance": {"scan_id": scan, "page_number": 1}}


def test_eligible_rules():
    assert s.eligible(doc("a", 1, 10))
    assert not s.eligible(doc("a", 1, 3))  # quá ít thực thể
    assert not s.eligible(doc("a", 1, 10, per=False))  # không có tên người
    assert not s.eligible(doc("a", 1, 10, text="𠁅公"))  # ký tự ngoài BMP


def test_select_one_page_per_book_closest_to_median_and_limited_to_n():
    docs = [doc("a1", 1, 9), doc("a2", 1, 20), doc("b1", 2, 11), doc("c1", 3, 40), doc("d1", 4, 10)]
    chosen = s.select(docs, n=3)
    assert len({d["provenance"]["scan_id"] for d in chosen}) == len(chosen) == 3  # mỗi sách một trang
    assert "c1" not in {d["doc_id"] for d in chosen}  # trang quá dài xa trung vị bị loại khi dư sách


def test_run_writes_all_outputs_and_held_out(tmp_path):
    gold = tmp_path / "gold"
    gold.mkdir()
    for i in range(4):
        (gold / f"d{i}.json").write_text(json.dumps(doc(f"han-{i}-p001", i, 10)), encoding="utf-8")
    out = tmp_path / "out"
    report = s.run(gold, out, n=3)
    assert report["pages"] == 3 and report["docs"] == 3
    assert len(json.loads((out / "held_out.json").read_text(encoding="utf-8"))) == 3
    assert len(json.loads((out / "tasks.json").read_text(encoding="utf-8"))) == 3
    assert "scan_id" in (out / "manifest.csv").read_text().splitlines()[0]
    assert "huấn luyện" in (out / "HUONG_DAN_SOAT.md").read_text(encoding="utf-8")
