import json

from label_studio_pipeline import build_han_pilot as b

HAN = "家譜始祖清閑公" * 30  # 210 chữ Hán


def page(scan, n, text=HAN, sim=None):
    meta = {"engines": {"a": {"text": "x", "similarity_to_others": sim}}} if sim is not None else None
    return {"scan_id": scan, "page_number": n, "text": text, "meta": meta}


def test_agreement_score_averages_and_handles_missing():
    assert b.agreement_score({"engines": {"a": {"similarity_to_others": 0.4}, "b": {"similarity_to_others": 0.6}}}) == 0.5
    assert b.agreement_score({"engines": {"a": {"text": "x"}}}) is None
    assert b.agreement_score(None) is None


def test_utf16_offsets_round_trip_with_non_bmp_chars():
    text = "公𠁅清𭘾閑"  # 2 chữ ngoài BMP
    assert b.codepoint_to_utf16(text, 5) == 7  # 5 code point = 7 đơn vị UTF-16
    assert b.utf16_to_codepoint(text, 7) == 5
    assert b.utf16_to_codepoint(text, 3) == 2  # sau 公(1)+𠁅(2)
    for cp in range(len(text) + 1):
        assert b.utf16_to_codepoint(text, b.codepoint_to_utf16(text, cp)) == cp
    assert b.has_non_bmp(text) and not b.has_non_bmp("公氏")


def test_select_prefers_high_agreement_spreads_across_docs_and_skips_short_pages():
    pages = [page(1, n, sim=0.1 * n) for n in range(1, 9)] + [page(2, 1, sim=0.9), page(3, 1, text="短", sim=1.0)]
    chosen = b.select_pages(pages, per_doc=3, target_chars=10**6)
    ids = [(p["scan_id"], p["page_number"]) for p in chosen]
    assert (3, 1) not in ids  # quá ngắn
    assert [n for s, n in ids if s == 1] == [6, 7, 8]  # 3 trang đồng thuận cao nhất
    assert (2, 1) in ids


def test_select_stops_at_target_and_round_robins():
    pages = [page(s, n, sim=0.5) for s in (1, 2, 3) for n in range(1, 6)]
    chosen = b.select_pages(pages, per_doc=5, target_chars=400)  # mỗi trang 210 → dừng sau 2 trang
    assert len(chosen) == 2 and len({p["scan_id"] for p in chosen}) == 2


def test_read_pages_and_build_write_outputs(tmp_path):
    line = "7\t3\t" + "家譜\\n始祖" * 60 + "\t" + json.dumps({"engines": {"a": {"similarity_to_others": 0.7}}})
    pages = b.read_pages([line, "bad line"])
    assert pages[0]["text"].count("\n") == 60 and pages[0]["scan_id"] == 7
    report = b.build(pages, tmp_path, min_han=10)
    assert report["pages_selected"] == 1 and report["mean_agreement"] == 0.7
    task = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))[0]["data"]
    assert task["lang"] == "han" and task["doc_id"] == "han-7-p003"
    assert (tmp_path / "manifest.csv").read_text().splitlines()[0].startswith("scan_id,page_number")


def test_exclude_docs_removes_them_from_the_sample():
    pages = [page(1, 1, sim=0.5), page(2, 1, sim=0.9)]
    assert [p["scan_id"] for p in b.select_pages(pages, exclude_docs=[2])] == [1]
