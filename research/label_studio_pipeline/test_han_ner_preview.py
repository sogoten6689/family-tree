import json

from label_studio_pipeline import han_ner_preview as v


def doc(doc_id="han-1-p001"):
    text = "始祖清閑公配陳氏<tag>" + "。" * 60
    ents = [{"start": 0, "end": 2, "label": "GENERATION", "text": "始祖"}, {"start": 2, "end": 5, "label": "PER_NAME", "text": "清閑公"},
            {"start": 6, "end": 8, "label": "PER_NAME", "text": "陳氏"}]
    return {"doc_id": doc_id, "text": text, "entities": ents, "relations": [{"type": "SPOUSE", "head": 1, "tail": 2}],
            "provenance": {"scan_id": 1, "page_number": 1}, "stats": {"unmatched": 0}}


def test_render_marks_entities_and_escapes_html():
    out = v.render_text(doc())
    assert out.count('class="e"') == 3 and "&lt;tag&gt;" in out and "<tag>" not in out
    assert "Đời" in out and "Tên người" in out


def test_card_shows_relations_and_flags():
    card = v.render_card(doc(), ["khong_khop_chuoi"])
    assert "là vợ/chồng của" in card and "khong_khop_chuoi" in card and "tài liệu #1" in card


def test_build_writes_html_with_test_flagged_and_clean(tmp_path):
    gold = tmp_path / "gold"
    gold.mkdir()
    for i in range(1, 9):
        d = doc(f"han-1-p{i:03d}")
        if i == 2:
            d["entities"] = []
            d["relations"] = []
        (gold / f"{d['doc_id']}.json").write_text(json.dumps(d), encoding="utf-8")
    held = tmp_path / "held.json"
    held.write_text(json.dumps(["han-1-p001"]), encoding="utf-8")
    n = v.build(gold, tmp_path / "p.html", held, n=6)
    html_text = (tmp_path / "p.html").read_text(encoding="utf-8")
    assert n == 6 and "tap_test" in html_text and "khong_thuc_the" in html_text and "Cách xem" in html_text


def test_card_ignores_relations_pointing_outside_entities():
    d = doc()
    d["relations"].append({"type": "FATHER_OF", "head": 0, "tail": 99})
    assert v.render_card(d, []).count("<li>") == 1
