"""Chạy từ research/:  python -m pytest label_studio_pipeline/test_analyze_data_quality.py"""
import json
import tempfile
import unittest
from pathlib import Path

from label_studio_pipeline import analyze_data_quality as q


def ent(start, end, label, text="x"):
    return {"start": start, "end": end, "label": label, "text": text}


class MetricTest(unittest.TestCase):
    def test_prf(self) -> None:
        self.assertEqual(q.prf(8, 2, 8)["precision"], 0.8)
        self.assertEqual(q.prf(8, 2, 8)["recall"], 0.5)
        self.assertEqual(q.prf(0, 0, 0)["f1"], 0.0)  # không chia cho 0

    def test_strict_and_lenient_counts(self) -> None:
        ref = [ent(0, 5, "PER_NAME"), ent(10, 14, "DATE"), ent(20, 26, "LOC")]
        pred = [ent(0, 5, "PER_NAME"), ent(10, 13, "DATE"), ent(30, 33, "LOC")]  # khớp đúng / lệch 1 ký tự / thừa
        out = q.compare_entities(ref, pred)
        strict, lenient = out["strict"], out["lenient"]
        self.assertEqual((strict["PER_NAME:tp"], strict["DATE:tp"], strict["DATE:fp"], strict["DATE:fn"]), (1, 0, 1, 1))
        self.assertEqual((lenient["DATE:tp"], lenient["DATE:fp"], lenient["DATE:fn"]), (1, 0, 0))  # IoU 3/4 ≥ 0.5
        self.assertEqual((lenient["LOC:tp"], lenient["LOC:fp"], lenient["LOC:fn"]), (0, 1, 1))

    def test_wrong_label_is_both_fp_and_fn(self) -> None:
        out = q.compare_entities([ent(0, 5, "PER_NAME")], [ent(0, 5, "LOC")])
        self.assertEqual((out["strict"]["PER_NAME:fn"], out["strict"]["LOC:fp"], out["strict"]["PER_NAME:tp"]), (1, 1, 0))

    def test_lenient_matches_each_reference_only_once(self) -> None:
        out = q.compare_entities([ent(0, 10, "LOC")], [ent(0, 6, "LOC"), ent(2, 10, "LOC")])
        self.assertEqual((out["lenient"]["LOC:tp"], out["lenient"]["LOC:fp"]), (1, 1))

    def test_summarize_micro(self) -> None:
        from collections import Counter

        c = Counter({"PER_NAME:tp": 3, "PER_NAME:fp": 1, "PER_NAME:fn": 1, "LOC:tp": 1})
        s = q.summarize(c)
        self.assertEqual((s["micro"]["tp"], s["micro"]["fp"], s["micro"]["fn"]), (4, 1, 1))
        self.assertEqual(s["PER_NAME"]["precision"], 0.75)


class DocTest(unittest.TestCase):
    def test_norm_name(self) -> None:
        self.assertEqual(q.norm_name("  Nguyễn  Văn An. "), "nguyễn văn an")

    def test_relation_triples_direction_and_symmetry(self) -> None:
        doc = {"entities": [ent(0, 1, "PER_NAME", "A"), ent(2, 3, "PER_NAME", "B"), ent(4, 5, "PER_NAME", "C")],
               "relations": [{"type": "FATHER_OF", "head": 0, "tail": 1}, {"type": "SPOUSE", "head": 2, "tail": 0}]}
        self.assertEqual(q._relation_triples(doc), {("parent_of", "a", "b"), ("spouse_of", "a", "c")})

    def test_silver_vs_human_skips_when_text_differs(self) -> None:
        human = {1: {"text": "abc", "entities": [ent(0, 1, "LOC")]}, 2: {"text": "abc", "entities": [ent(0, 1, "LOC")]}}
        silver = {1: {"text": "abc", "entities": [ent(0, 1, "LOC")]}, 2: {"text": "abd", "entities": []}}
        out = q.silver_vs_human(human, silver)
        self.assertEqual((out["docs_compared"], out["docs_text_differs_skipped"]), (1, 1))
        self.assertEqual(out["strict"]["micro"]["f1"], 1.0)

    def test_regex_baseline_with_a_fake_extractor(self) -> None:
        class Fake:
            def parse(self, text):
                return {"people": [{"id": "P1", "full_name": "Nguyễn Văn An"}, {"id": "P2", "full_name": "Trần Thị Hạnh"}],
                        "relationships": [{"from_id": "P1", "to_id": "P2", "type": "spouse_of"}]}

        doc = {"text": "t", "entities": [ent(0, 1, "PER_NAME", "Nguyễn Văn An"), ent(2, 3, "PER_NAME", "Trần Thị Hạnh"),
                                         ent(4, 5, "PER_NAME", "Lê Văn Bình")],
               "relations": [{"type": "SPOUSE", "head": 1, "tail": 0}]}
        out = q.regex_baseline({1: doc}, Fake)
        self.assertEqual((out["person_names"]["tp"], out["person_names"]["fn"], out["person_names"]["fp"]), (2, 1, 0))
        self.assertEqual((out["relations"]["tp"], out["relations"]["fp"], out["relations"]["fn"]), (1, 0, 0))  # spouse không phân hướng


class CleanChecksTest(unittest.TestCase):
    def test_detects_dirty_text_and_labels(self) -> None:
        dirty = "Ông​ Nguyễn  Văn An\r\nsinh năm 1945."
        docs = {1: {"text": dirty, "entities": [
            ent(4, 8, "PER_NAME", " Nguyễn"),  # khoảng trắng đầu
            ent(0, 3, "PER_NAME", "An"),  # một từ
            ent(0, 3, "DATE", "sinh"),  # DATE không có số
            ent(0, 3, "LOC", "Hà.")  # dấu chấm cuối
        ]}, 2: {"text": dirty, "entities": []}}
        out = q.clean_checks(docs)
        issues = out["issues"]
        self.assertEqual(issues["zero_width_chars"], 2)  # 1 mỗi tài liệu
        self.assertEqual(issues["crlf_lines"], 2)
        self.assertEqual(issues["entity_edge_whitespace"], 1)
        self.assertEqual(issues["per_name_single_word"], 2)
        self.assertEqual(issues["date_without_digit"], 1)
        self.assertEqual(issues["entity_trailing_punct"], 1)
        self.assertEqual(out["duplicate_documents"]["groups"], 1)  # hai tài liệu trùng văn bản

    def test_clean_docs_have_no_issues(self) -> None:
        out = q.clean_checks({1: {"text": "Nguyễn Văn An sinh năm 1945.", "entities": [ent(0, 13, "PER_NAME", "Nguyễn Văn An")]}})
        self.assertEqual(out["issues"], {})


class HanProfileTest(unittest.TestCase):
    def test_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data" / "track1_hannom_only"
            root.mkdir(parents=True)
            pages = [
                {"l1_ocr": {"voted_text": "始祖清閑公\n配陳氏", "uncertain_rate": 0.0}},
                {"l1_ocr": {"voted_text": "阮□□abc\n", "uncertain_rate": 0.25}},
                {"l1_ocr": {"voted_text": "  ", "uncertain_rate": 0.0}},
            ]
            (root / "x.json").write_text(json.dumps({"doc_id": "x", "pages": pages}), encoding="utf-8")
            out = q.han_ocr_profile(Path(tmp))
        book = out["books"][0]
        self.assertEqual((book["pages"], book["pages_empty"], book["pages_uncertain_ge_10pct"]), (3, 1, 1))
        self.assertEqual(book["placeholder_chars"], 2)
        self.assertEqual(book["ascii_alnum_chars"], 3)
        self.assertLess(book["cjk_ratio"], 1.0)


if __name__ == "__main__":
    unittest.main()
