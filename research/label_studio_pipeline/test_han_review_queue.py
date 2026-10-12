import csv
import json

from label_studio_pipeline import han_review_queue as q


def doc(doc_id, scan, page, n_ent=5, text="家譜始祖清閑公" * 10, unmatched=0):
    ents = [{"start": 0, "end": 1, "label": "PER_NAME", "text": "家"}] * n_ent
    return {"doc_id": doc_id, "text": text, "entities": ents, "relations": [], "model_version": "m",
            "provenance": {"scan_id": scan, "page_number": page}, "stats": {"unmatched": unmatched}}


def test_flags_cover_each_warning_sign():
    assert q.flags_for(doc("a", 1, 1), 0.6, False) == []
    assert "khong_thuc_the" in q.flags_for(doc("a", 1, 1, n_ent=0), 0.6, False)
    assert "khong_khop_chuoi" in q.flags_for(doc("a", 1, 1, unmatched=2), 0.6, False)
    assert "ocr_kem_dong_thuan" in q.flags_for(doc("a", 1, 1), 0.2, False)
    assert "ocr_kem_dong_thuan" not in q.flags_for(doc("a", 1, 1), None, False)  # thiếu dữ liệu ≠ kém
    assert "ngoai_bmp" in q.flags_for(doc("a", 1, 1, text="𠁅公" * 20), 0.6, False)
    assert "qua_nhieu_thuc_the" in q.flags_for(doc("a", 1, 1, n_ent=60, text="家譜" * 20), 0.6, False)
    assert q.flags_for(doc("a", 1, 1), 0.6, True) == ["tap_test"]


def test_build_puts_flagged_first_batches_them_and_keeps_test_pages_out(tmp_path):
    gold = tmp_path / "gold"
    gold.mkdir()
    pages = [doc("han-1-p001", 1, 1), doc("han-1-p002", 1, 2, n_ent=0), doc("han-1-p003", 1, 3), doc("han-1-p004", 1, 4, unmatched=1), doc("han-1-p005", 1, 5)]
    for d in pages:
        (gold / f"{d['doc_id']}.json").write_text(json.dumps(d), encoding="utf-8")
    manifest = tmp_path / "manifest.csv"
    manifest.write_text("scan_id,page_number,han_chars,agreement,non_bmp\n" + "\n".join(f"1,{i},70,0.6,0" for i in range(1, 6)), encoding="utf-8")
    held = tmp_path / "held.json"
    held.write_text(json.dumps(["han-1-p005"]), encoding="utf-8")
    summary = q.build(gold, manifest, held, tmp_path / "out", batch_size=2)
    assert summary == {"pages_total": 5, "test_pages": 1, "to_review": 4, "flagged": 2, "clean": 2, "batches": 2, "batch_size": 2}
    rows = list(csv.DictReader((tmp_path / "out/queue.csv").open(encoding="utf-8")))
    assert {r["doc_id"] for r in rows if r["batch"] == "1"} == {"han-1-p002", "han-1-p004"}  # nghi ngờ trước
    assert [r["batch"] for r in rows if r["doc_id"] == "han-1-p005"] == ["TEST"]
    assert len(json.loads((tmp_path / "out/batches/batch_001.json").read_text(encoding="utf-8"))) == 2
    assert all("han-1-p005" not in f.read_text(encoding="utf-8") for f in (tmp_path / "out/batches").glob("*.json"))
