import json

import pytest

from label_studio_pipeline import gemini_relation_labels as g


def doc():
    text = "Ông Nguyễn Văn An sinh Nguyễn Văn Bình. Bà Trần Thị Hoa vợ ông An."
    def span(s):
        i = text.index(s)
        return {"start": i, "end": i + len(s), "label": "PER_NAME", "text": s}
    return {"text": text, "entities": [span("Nguyễn Văn An"), span("Nguyễn Văn Bình"), span("Trần Thị Hoa")], "relations": [{"type": "FATHER_OF", "head": 0, "tail": 1}]}


def test_annotate_inserts_ids_in_order():
    t, persons = g.annotate(doc())
    assert "Nguyễn Văn An[#0]" in t and "Nguyễn Văn Bình[#1]" in t and "Trần Thị Hoa[#2]" in t and set(persons) == {0, 1, 2}


def test_parse_response_filters_invalid_and_dedupes():
    raw = '```json\n{"relations":[{"head":0,"tail":1,"type":"father_of","evidence":"x"},{"head":0,"tail":1,"type":"FATHER_OF"},{"head":0,"tail":9,"type":"FATHER_OF"},{"head":2,"tail":0,"type":"SPOUSE"},{"head":0,"tail":2,"type":"SPOUSE"},{"head":0,"tail":0,"type":"SPOUSE"},{"head":1,"tail":0,"type":"SIBLING"}]}\n```'
    rels = g.parse_response(raw, {0, 1, 2})
    assert [(r["head"], r["tail"], r["type"]) for r in rels] == [(0, 1, "FATHER_OF"), (2, 0, "SPOUSE")]


def test_label_tree_and_evaluate(tmp_path):
    ask = lambda text: ('{"relations":[{"head":0,"tail":1,"type":"FATHER_OF","evidence":"sinh"},{"head":2,"tail":0,"type":"SPOUSE","evidence":"vợ"}]}', {"prompt_tokens": 10, "completion_tokens": 5})
    docs, out = tmp_path / "d", tmp_path / "o"
    (docs / "7").mkdir(parents=True)
    (docs / "7" / "gold.training.json").write_text(json.dumps(doc(), ensure_ascii=False), encoding="utf-8")
    totals = g.run_label(docs, out, ["7"], ask=ask, progress=lambda *_: None)
    assert totals["trees"] == 1 and totals["prompt_tokens"] == 10
    ev = g.evaluate(out, docs)  # gold chỉ có FATHER_OF → SPOUSE là dự đoán thừa
    assert ev["tp"] == 1 and ev["fp"] == 1 and ev["fn"] == 0
    assert g.run_label(docs, out, ["7"], ask=ask, progress=lambda *_: None)["skipped"] == 1  # chạy lại bỏ qua


def test_missing_key_exits(monkeypatch):
    monkeypatch.delenv("RAMCLOUD_KEY", raising=False)
    with pytest.raises(SystemExit):
        g.call_llm("x")


def test_call_llm_retries_on_429(monkeypatch):
    import httpx

    monkeypatch.setenv("RAMCLOUD_KEY", "sk-test")
    monkeypatch.setattr(g.time, "sleep", lambda *_: None)
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, text="cooling down")
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}], "usage": {"prompt_tokens": 1}})

    raw, usage = g.call_llm("x", transport=httpx.MockTransport(handler), retries=5, wait=0)
    assert raw == "{}" and calls["n"] == 3
