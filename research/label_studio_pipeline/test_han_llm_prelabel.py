import json

import httpx
import pytest

from label_studio_pipeline import han_llm_prelabel as h

TEXT = "始祖清閑公配陳氏生子敏達公，六月初十日葬青池縣姜亭社。"


def test_parse_response_tolerates_fences_and_drops_invalid_items():
    raw = '```json\n{"entities":[{"text":"清閑公","label":"PER_NAME"},{"text":"","label":"LOC"},{"text":"x","label":"BAD"}],"relations":[{"type":"SPOUSE","head":"a","tail":"b"},{"type":"UNCLE","head":"a","tail":"b"}]}\n```'
    parsed = h.parse_response(raw)
    assert parsed["entities"] == [{"text": "清閑公", "label": "PER_NAME"}]
    assert [r["type"] for r in parsed["relations"]] == ["SPOUSE"]
    assert h.parse_response("không có json") == {"entities": [], "relations": []}
    assert h.parse_response("{hỏng")["entities"] == []


def test_locate_uses_string_match_in_order_and_counts_unmatched():
    ents = [{"text": "清閑公", "label": "PER_NAME"}, {"text": "陳氏", "label": "PER_NAME"}, {"text": "沒有", "label": "LOC"}]
    placed, missing = h.locate_entities(TEXT, ents)
    assert missing == 1
    for e in placed:
        assert TEXT[e["start"] : e["end"]] == e["text"]
    assert [e["text"] for e in placed] == ["清閑公", "陳氏"]


def test_locate_handles_repeated_names_without_overlap():
    text = "公生子公，公"
    placed, missing = h.locate_entities(text, [{"text": "公", "label": "PER_NAME"}] * 3)
    assert missing == 0 and [e["start"] for e in placed] == [0, 3, 5]
    placed, missing = h.locate_entities(text, [{"text": "公", "label": "PER_NAME"}] * 4)  # chỉ có 3 chỗ
    assert missing == 1 and len(placed) == 3


def test_relations_map_by_text_drop_self_and_duplicates():
    ents = [
        {"start": 2, "end": 5, "label": "PER_NAME", "text": "清閑公"},
        {"start": 6, "end": 8, "label": "PER_NAME", "text": "陳氏"},
        {"start": 11, "end": 14, "label": "PER_NAME", "text": "敏達公"},
        {"start": 20, "end": 23, "label": "LOC", "text": "姜亭社"},
    ]
    rels = [
        {"type": "FATHER_OF", "head": "清閑公", "tail": "敏達公"},
        {"type": "SPOUSE", "head": "清閑公", "tail": "陳氏"},
        {"type": "SPOUSE", "head": "陳氏", "tail": "清閑公"},  # trùng (không phân biệt chiều)
        {"type": "FATHER_OF", "head": "清閑公", "tail": "清閑公"},  # tự quan hệ
        {"type": "FATHER_OF", "head": "清閑公", "tail": "姜亭社"},  # không phải PER_NAME
    ]
    assert h.map_relations(ents, rels) == [{"type": "FATHER_OF", "head": 0, "tail": 2}, {"type": "SPOUSE", "head": 0, "tail": 1}]


def test_label_page_and_ls_task_use_utf16_offsets_for_non_bmp(tmp_path):
    text = "𠁅公生子清閑公"
    answer = json.dumps({"entities": [{"text": "清閑公", "label": "PER_NAME"}], "relations": []})
    doc = h.label_page({"text": text, "doc_id": "han-1-p001", "provenance": {"scan_id": 1}}, ask=lambda t: (answer, {"prompt_tokens": 5}), model="m")
    e = doc["entities"][0]
    assert (e["start"], e["end"]) == (4, 7) and doc["source"] == "llm-silver" and doc["lang"] == "han"
    value = h.to_ls_task(doc)["predictions"][0]["result"][0]["value"]
    assert (value["start"], value["end"]) == (5, 8)  # 𠁅 chiếm 2 đơn vị UTF-16


def test_call_llm_retries_transient_then_succeeds(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "sk-test")
    monkeypatch.setattr(h.time, "sleep", lambda *_: None)
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, text="no channel")
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}], "usage": {"prompt_tokens": 1}})

    raw, usage = h.call_llm("x", "m", transport=httpx.MockTransport(handler), retries=5, wait=0)
    assert raw == "{}" and calls["n"] == 3


def test_call_llm_requires_key(monkeypatch):
    monkeypatch.delenv("RAMCLOUD_KEY", raising=False)
    with pytest.raises(RuntimeError, match="RAMCLOUD_KEY"):
        h.call_llm("x", "m", provider="ramcloud")


def test_run_skips_done_pages_and_writes_report(tmp_path):
    tasks = [{"data": {"text": TEXT, "doc_id": f"han-1-p00{i}"}} for i in (1, 2)]
    path = tmp_path / "tasks.json"
    path.write_text(json.dumps(tasks), encoding="utf-8")
    answer = json.dumps({"entities": [{"text": "清閑公", "label": "PER_NAME"}, {"text": "不在", "label": "LOC"}], "relations": []})
    calls = []

    def ask(t):
        calls.append(t)
        return answer, {"prompt_tokens": 10, "completion_tokens": 3}

    out = tmp_path / "out"
    report = h.run(path, out, ask=ask, progress=lambda *_: None)
    assert report["pages_labeled"] == 2 and report["entities"] == 2 and report["unmatched_entities"] == 2
    assert report["unmatched_rate"] == 0.5 and report["tokens_this_run"] == {"prompt": 20, "completion": 6}
    h.run(path, out, ask=ask, progress=lambda *_: None)  # chạy lại: không gọi thêm
    assert len(calls) == 2
    assert len(json.loads((out / "tasks.json").read_text(encoding="utf-8"))) == 2
