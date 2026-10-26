import json

from label_studio_pipeline import giapha_export as g
from label_studio_pipeline import text_encoding as te

CLEAN = "Gia phả họ Hoàng là của dòng họ. Lời nói đầu: trước hết chúng tôi ghi lại nguồn gốc. " * 3
VOCAB = te.build_vocab([CLEAN], min_count=1)


def test_conversions():
    assert te.tcvn3_to_unicode("Gia ph¶ hä Hoµng") == "Gia phả họ Hoàng"
    assert te.vni_to_unicode("LÔØI NOÙI ÑAÀU") == "LỜI NÓI ĐẦU"
    assert te.vni_to_unicode("Tröôùc heát") == "Trước hết"


def test_fix_text_is_line_level_and_reports():
    text = "Gia phả họ Hoàng\nLôøi noùi ñaàu\nGia ph¶ hä Hoµng"
    fixed, rep = te.fix_text(text, VOCAB)
    assert fixed.split("\n") == ["Gia phả họ Hoàng", "Lời nói đầu", "Gia phả họ Hoàng"]
    assert rep["detected"] == "legacy" and rep["fixed_lines"] == {"vni": 1, "tcvn3": 1}
    assert rep["vocab_coverage_after"] > rep["vocab_coverage_before"] and rep["length_changed"]


def test_clean_text_untouched():
    assert te.fix_text(CLEAN, VOCAB) == (CLEAN, {"detected": "unicode"})


def _source(tmp_path, tree_id, text):
    src = tmp_path / "src" / str(tree_id)
    src.mkdir(parents=True)
    (src / "pha_ky.txt").write_text(text, encoding="utf-8")
    (src / "meta.json").write_text("{}", encoding="utf-8")
    return tmp_path / "src"


def test_export_fixes_tcvn3_and_keeps_raw(tmp_path):
    src = _source(tmp_path, 1, "Gia ph¶ hä Hoµng lµ cña dßng hä.")
    out = tmp_path / "out"
    r = g.export_tree(1, source_dir=src, export_dir=out, labels_dir=None, include_labels=False, vocab=VOCAB)
    assert (out / "1" / "pha_ky.txt").read_text(encoding="utf-8") == "Gia phả họ Hoàng là của dòng họ."
    assert (out / "1" / "pha_ky.raw.txt").read_text(encoding="utf-8") == "Gia ph¶ hä Hoµng lµ cña dßng hä."
    meta = json.loads((out / "1" / "metadata.json").read_text(encoding="utf-8"))
    assert meta["text_encoding"]["applied"] is True and r["text_encoding"]["applied"] is True


def test_export_skips_vni_fix_when_labels_exist(tmp_path):
    src = _source(tmp_path, 2, "Lôøi noùi ñaàu cuûa gia phaû hoï Hoaøng")
    labels = tmp_path / "labels"
    (labels / "2").mkdir(parents=True)
    out = tmp_path / "out"
    r = g.export_tree(2, source_dir=src, export_dir=out, labels_dir=labels, include_labels=True, vocab=VOCAB)
    assert (out / "2" / "pha_ky.txt").read_text(encoding="utf-8").startswith("Lôøi")   # giữ nguyên, nhãn không lệch offset
    assert not (out / "2" / "pha_ky.raw.txt").exists()
    assert r["text_encoding"]["applied"] is False and "offset" in r["text_encoding"]["reason"]


def test_export_tcvn3_with_labels_rewrites_label_strings(tmp_path):
    raw = "Gia ph¶ hä Hoµng lµ cña dßng hä."
    src = _source(tmp_path, 4, raw)
    labels = tmp_path / "labels" / "4"
    labels.mkdir(parents=True)
    s = raw.index("hä Hoµng")
    (labels / "pha_ky.ls_task.json").write_text(json.dumps({"data": {"text": raw}, "predictions": [{"result": [
        {"value": {"start": s, "end": s + 8, "text": "hä Hoµng", "labels": ["PER_NAME"]}}]}]}, ensure_ascii=False), encoding="utf-8")
    (labels / "pha_ky.entities.json").write_text(json.dumps({"entities": [{"text": "hä Hoµng", "label": "PER_NAME"}, {"text": "không có", "label": "LOC"}],
                                                             "relations": []}, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "out"
    r = g.export_tree(4, source_dir=src, export_dir=out, labels_dir=tmp_path / "labels", include_labels=True, vocab=VOCAB)
    task = json.loads((out / "4" / "labels" / "ls_task.json").read_text(encoding="utf-8"))
    v = task["predictions"][0]["result"][0]["value"]
    assert task["data"]["text"] == "Gia phả họ Hoàng là của dòng họ." and v["text"] == "họ Hoàng" == task["data"]["text"][v["start"]:v["end"]]
    ents = json.loads((out / "4" / "labels" / "entities.json").read_text(encoding="utf-8"))["entities"]
    assert ents[0]["text"] == "họ Hoàng" and ents[1]["text"] == "không có"
    assert r["text_encoding"]["labels"] == {"ls_task_regions": 1, "entities_fixed": 1, "entities_not_found": 1}


def test_export_clean_tree_no_raw_and_rerun_removes_stale_raw(tmp_path):
    src = _source(tmp_path, 3, CLEAN)
    out = tmp_path / "out"
    (out / "3").mkdir(parents=True)
    (out / "3" / "pha_ky.raw.txt").write_text("cũ", encoding="utf-8")
    r = g.export_tree(3, source_dir=src, export_dir=out, labels_dir=None, include_labels=False, vocab=VOCAB)
    assert not (out / "3" / "pha_ky.raw.txt").exists() and r["text_encoding"] is None
    assert (out / "3" / "pha_ky.txt").read_text(encoding="utf-8") == CLEAN
