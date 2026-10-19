import json

from label_studio_pipeline import build_han_ner_dataset as b


def doc(doc_id, scan, text="始祖清閑公配陳氏。生子敏達公。", ents=((2, 5, "PER_NAME"), (6, 8, "PER_NAME"))):
    return {"doc_id": doc_id, "text": text, "entities": [{"start": s, "end": e, "label": l, "text": text[s:e]} for s, e, l in ents],
            "relations": [], "provenance": {"scan_id": scan, "page_number": 1}}


def write_gold(tmp_path, books=10, pages=2):
    gold = tmp_path / "gold"
    gold.mkdir()
    for s in range(1, books + 1):
        for p in range(1, pages + 1):
            d = doc(f"han-{s}-p{p:03d}", s)
            (gold / f"{d['doc_id']}.json").write_text(json.dumps(d), encoding="utf-8")
    return gold


def test_cv_folds_split_by_book_and_never_leak_books(tmp_path):
    gold = write_gold(tmp_path)
    held = tmp_path / "held.json"
    held.write_text(json.dumps(["han-1-p001"]), encoding="utf-8")
    summary = b.build(gold, held, tmp_path / "out", folds=5)
    assert summary["pages_pool"] == 19 and summary["pages_test"] == 1  # trang test bị loại khỏi kiểm chéo
    tests_seen = set()
    for fold in summary["cv"]:
        books = fold["books"]
        assert not set(books["train"]) & set(books["test"]) and not set(books["dev"]) & set(books["test"])
        assert not set(books["train"]) & set(books["dev"])
        tests_seen |= set(books["test"])
    assert tests_seen == {str(i) for i in range(1, 11)}  # mỗi sách làm test đúng một lượt


def test_conll_is_character_level_with_bio_tags(tmp_path):
    gold = write_gold(tmp_path)
    b.build(gold, None, tmp_path / "out", folds=5)
    text = (tmp_path / "out/han_final/train.conll").read_text(encoding="utf-8").splitlines()
    rows = [l.split("\t") for l in text if l]
    assert all(len(r[0]) == 1 for r in rows)  # mỗi dòng 1 ký tự
    assert ("清", "B-PER_NAME") in {(r[0], r[1]) for r in rows} and ("閑", "I-PER_NAME") in {(r[0], r[1]) for r in rows}


def test_final_split_has_two_dev_books_and_test_pages(tmp_path):
    gold = write_gold(tmp_path)
    held = tmp_path / "held.json"
    held.write_text(json.dumps(["han-3-p001", "han-4-p002"]), encoding="utf-8")
    summary = b.build(gold, held, tmp_path / "out", folds=5)
    final = summary["final"]
    assert len(final["dev_books"]) == 2 and final["test"]["docs"] == 2
    assert final["train"]["docs"] + final["dev"]["docs"] == summary["pages_pool"]
    assert (tmp_path / "out/dataset_summary.json").is_file()
