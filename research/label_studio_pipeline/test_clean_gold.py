import json
from collections import Counter

from label_studio_pipeline import clean_gold as cg


def ent(text, s, label="PER_NAME"):
    return {"start": s, "end": s + len(text), "label": label, "text": text}


def doc(text, entities, relations=None):
    return {"text": text, "entities": entities, "relations": relations or []}


def test_zero_width_removed_and_offsets_shift():
    text = "A​ Nguyễn Văn B"
    start = text.index("Nguyễn")
    cleaned, c = cg.clean_document(doc(text, [ent("Nguyễn Văn", start)]))
    assert "​" not in cleaned["text"]
    e = cleaned["entities"][0]
    assert cleaned["text"][e["start"]:e["end"]] == "Nguyễn Văn" == e["text"]
    assert c["c1_zero_width_removed"] == 1


def test_crlf_nbsp_and_nfc():
    text = "x\r\ny Nguyễn"  # ê + dấu ngã tổ hợp
    s = text.index("Nguye")
    cleaned, c = cg.clean_document(doc(text, [ent("Nguyễn", s)]))
    assert "\r" not in cleaned["text"] and " " not in cleaned["text"]
    assert cleaned["entities"][0]["text"] == "Nguyễn"
    assert c["c1_crlf_replaced"] == 1 and c["c1_nbsp_replaced"] == 1


def test_trim_edges_and_drop_empty():
    text = "ông Hà. rồi ."
    d = doc(text, [ent(" Hà.", 3), ent(".", 12)])
    cleaned, c = cg.clean_document(d)
    assert [e["text"] for e in cleaned["entities"]] == ["Hà"]
    assert c["c2_entity_trimmed"] == 1 and c["c2_entity_empty_dropped"] == 1


def test_overlap_dropped_and_relations_remapped():
    text = "Nguyễn Văn An sinh Bình"
    ents = [ent("Nguyễn Văn", 0), ent("Nguyễn Văn An", 0), ent("Bình", 19)]
    rels = [{"type": "FATHER_OF", "head": 1, "tail": 2}, {"type": "FATHER_OF", "head": 0, "tail": 2}]
    cleaned, c = cg.clean_document(doc(text, ents, rels))
    assert [e["text"] for e in cleaned["entities"]] == ["Nguyễn Văn An", "Bình"]
    assert cleaned["relations"] == [{"type": "FATHER_OF", "head": 0, "tail": 1}]
    assert c["c3_overlap_or_duplicate_dropped"] == 1
    assert c["c3_relation_dropped_missing_entity"] == 1


def test_clean_doc_unchanged_and_verified():
    text = "Nguyễn Văn An sinh năm 1900"
    d = doc(text, [ent("Nguyễn Văn An", 0), ent("1900", 23, "DATE")])
    cleaned, c = cg.clean_document(d)
    assert cleaned["text"] == text and cleaned["entities"] == d["entities"]
    assert "verify_failed_docs" not in c and cg.verify(cleaned) == []


def test_newline_entity_is_flagged_not_changed():
    text = "Nguyễn\nVăn"
    cleaned, c = cg.clean_document(doc(text, [ent("Nguyễn\nVăn", 0)]))
    assert cleaned["entities"][0]["text"] == "Nguyễn\nVăn"
    assert c["flag_entity_contains_newline"] == 1


def test_out_of_range_input_reported_as_hard_error():
    cleaned, c = cg.clean_document(doc("abc", [{"start": 0, "end": 99, "label": "LOC", "text": "abc"}]))
    assert c["input_entity_out_of_range"] == 1
    assert c["verify_failed_docs"] == 1 and cleaned["entities"] == []
    assert "verify_problems" in cleaned["cleaning"]


def test_find_duplicates():
    long = "Nguyễn Văn An sinh ra tại làng Bình Hòa huyện Hoài Đức"
    docs = {1: {"text": long}, 2: {"text": long}, 3: {"text": "khác hẳn"}}
    r = cg.find_duplicates(docs)
    assert r["duplicate_of"] == {"2": 1}
    assert r["doc_pairs_sharing_paragraphs"][0]["docs"] == [1, 2]


def test_directory_roundtrip_does_not_touch_input(tmp_path):
    src, out = tmp_path / "in", tmp_path / "out"
    (src / "7").mkdir(parents=True)
    original = json.dumps(doc("A​B Hà", [ent("Hà", 4)]), ensure_ascii=False)
    (src / "7" / "gold.training.json").write_text(original, encoding="utf-8")
    report = cg.clean_directory(src, out, progress=lambda *_: None)
    assert (src / "7" / "gold.training.json").read_text(encoding="utf-8") == original
    assert report["docs"] == 1 and report["totals"]["c1_zero_width_removed"] == 1
    assert (out / "clean_report.json").exists()
    assert cg.main(["--input-dir", str(out), "--output-dir", str(out / "x")]) == 0
