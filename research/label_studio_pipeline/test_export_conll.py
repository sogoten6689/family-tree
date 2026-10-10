"""Test xuất CoNLL. Chạy từ thư mục research/:  python -m pytest label_studio_pipeline/test_export_conll.py"""
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from label_studio_pipeline import export_conll as ec

# Ví dụ Hán thật (nom-855, trang 9) — cùng văn bản và nhãn với docs/schemas/NER_RE_LABEL_SCHEMA_AND_PIPELINE.md §4.1
HAN_DOC = {
    "lang": "han",
    "text": "始祖清閑公 前誥授光進韓國上將軍定勳衛長\n公乃正善公之子 顯有封爵是我\n配陳氏號慈懿 六月初十日忌 合葬青池縣姜亭社\n賜碑處生子字敏達",
    "entities": [
        {"start": 2, "end": 5, "label": "PER_NAME", "text": "清閑公"},
        {"start": 23, "end": 26, "label": "PER_NAME", "text": "正善公"},
        {"start": 21, "end": 22, "label": "PER_NAME", "text": "公"},
        {"start": 37, "end": 39, "label": "PER_NAME", "text": "陳氏"},
        {"start": 40, "end": 42, "label": "PER_NAME", "text": "慈懿"},
        {"start": 43, "end": 48, "label": "DATE", "text": "六月初十日"},
        {"start": 52, "end": 58, "label": "LOC", "text": "青池縣姜亭社"},
        {"start": 65, "end": 67, "label": "PER_NAME", "text": "敏達"},
    ],
}


def flat(sentences):
    return [pair for sentence in sentences for pair in sentence]


class OffsetTest(unittest.TestCase):
    def test_code_point_offsets_pass_through(self) -> None:
        c = Counter()
        spans = ec.resolve_offsets("阮文成娶陳氏", [{"start": 0, "end": 3, "label": "PER_NAME", "text": "阮文成"}], c)
        self.assertEqual(spans, [ec.Span(0, 3, "PER_NAME")])
        self.assertEqual((c["offset_ok"], c["offset_utf16_converted"], c["offset_mismatch_dropped"]), (1, 0, 0))

    def test_utf16_offsets_after_astral_chars_are_converted(self) -> None:
        text = "𠊚𠊚 阮文成娶陳氏"  # 2 chữ Nôm ngoài BMP: mỗi chữ = 1 code point nhưng 2 đơn vị UTF-16
        cp_start = text.index("阮文成")
        utf16_start = cp_start + 2  # lệch đúng số chữ ngoài BMP đứng trước
        c = Counter()
        spans = ec.resolve_offsets(text, [{"start": utf16_start, "end": utf16_start + 3, "label": "PER_NAME", "text": "阮文成"}], c)
        self.assertEqual(spans, [ec.Span(cp_start, cp_start + 3, "PER_NAME")])
        self.assertEqual((c["offset_utf16_converted"], c["offset_mismatch_dropped"]), (1, 0))
        self.assertEqual(text[spans[0].start:spans[0].end], "阮文成")

    def test_astral_char_inside_the_entity_itself(self) -> None:
        text = "生子𠊚達"
        c = Counter()
        spans = ec.resolve_offsets(text, [{"start": 2, "end": 5, "label": "PER_NAME", "text": "𠊚達"}], c)  # UTF-16: 𠊚=2 đơn vị
        self.assertEqual(spans, [ec.Span(2, 4, "PER_NAME")])
        self.assertEqual(c["offset_utf16_converted"], 1)

    def test_wrong_offsets_are_dropped_and_counted(self) -> None:
        c = Counter()
        spans = ec.resolve_offsets("阮文成娶陳氏", [{"start": 1, "end": 4, "label": "PER_NAME", "text": "阮文成"}], c)
        self.assertEqual(spans, [])
        self.assertEqual(c["offset_mismatch_dropped"], 1)

    def test_malformed_entities_are_counted(self) -> None:
        c = Counter()
        self.assertEqual(ec.resolve_offsets("abc", [{"label": "PER_NAME"}, {"start": "0", "end": 1, "label": "X", "text": "a"}], c), [])
        self.assertEqual(c["entity_malformed"], 2)

    def test_overlapping_entities_keep_the_earlier_longer_one(self) -> None:
        text = "阮文成娶陳氏"
        ents = [
            {"start": 0, "end": 3, "label": "PER_NAME", "text": "阮文成"},
            {"start": 1, "end": 3, "label": "LOC", "text": "文成"},
            {"start": 4, "end": 6, "label": "PER_NAME", "text": "陳氏"},
        ]
        c = Counter()
        spans = ec.resolve_offsets(text, ents, c)
        self.assertEqual([(s.start, s.end) for s in spans], [(0, 3), (4, 6)])
        self.assertEqual(c["overlap_dropped"], 1)


class TokenizeTest(unittest.TestCase):
    def test_char_unit_skips_whitespace(self) -> None:
        self.assertEqual([t.text for t in ec.tokenize("阮文\n成 娶", "char")], ["阮", "文", "成", "娶"])

    def test_word_unit_splits_punctuation(self) -> None:
        self.assertEqual([t.text for t in ec.tokenize("Huỳnh Tư, sinh 1928.", "word")], ["Huỳnh", "Tư", ",", "sinh", "1928", "."])

    def test_word_unit_keeps_decomposed_vietnamese_in_one_token(self) -> None:
        import unicodedata

        nfd = unicodedata.normalize("NFD", "Nguyễn Văn")
        self.assertEqual([t.text for t in ec.tokenize(nfd, "word")], [unicodedata.normalize("NFD", "Nguyễn"), unicodedata.normalize("NFD", "Văn")])

    def test_unknown_unit(self) -> None:
        with self.assertRaises(ValueError):
            ec.tokenize("x", "sentence")


class ConvertTest(unittest.TestCase):
    def test_han_example_char_level_bio(self) -> None:
        c = Counter()
        pairs = flat(ec.convert_document(HAN_DOC, unit="char", max_tokens=500, counters=c))
        tokens = [t for t, _ in pairs]
        tags = [g for _, g in pairs]
        self.assertEqual("".join(tokens), HAN_DOC["text"].replace("\n", "").replace(" ", ""))  # không mất/thêm ký tự
        i = tokens.index("清")
        self.assertEqual(tags[i:i + 3], ["B-PER_NAME", "I-PER_NAME", "I-PER_NAME"])  # 清閑公
        j = "".join(tokens).index("六月初十日")
        self.assertEqual(tags[j:j + 5], ["B-DATE", "I-DATE", "I-DATE", "I-DATE", "I-DATE"])
        k = "".join(tokens).index("青池縣姜亭社")
        self.assertEqual(tags[k:k + 6], ["B-LOC"] + ["I-LOC"] * 5)
        self.assertEqual(sum(1 for g in tags if g.startswith("B-")), 8)
        self.assertEqual((c["entities_in"], c["entities_out"], c["offset_ok"]), (8, 8, 8))

    def test_han_newline_is_ignored_so_a_name_can_wrap_across_columns(self) -> None:
        doc = {"text": "始祖阮文\n成配陳氏", "entities": [{"start": 2, "end": 6, "label": "PER_NAME", "text": "阮文\n成"}]}
        pairs = flat(ec.convert_document(doc, unit="char", max_tokens=100))
        self.assertEqual([t for t, _ in pairs], list("始祖阮文成配陳氏"))
        self.assertEqual([g for _, g in pairs][2:5], ["B-PER_NAME", "I-PER_NAME", "I-PER_NAME"])

    def test_han_sentences_split_on_fullwidth_enders_and_length(self) -> None:
        doc = {"text": "阮文成娶陳氏。生子敏達。", "entities": []}
        sentences = ec.convert_document(doc, unit="char", max_tokens=100)
        self.assertEqual(["".join(t for t, _ in s) for s in sentences], ["阮文成娶陳氏。", "生子敏達。"])
        long_doc = {"text": "甲" * 25, "entities": []}
        sizes = [len(s) for s in ec.convert_document(long_doc, unit="char", max_tokens=10)]
        self.assertEqual(sizes, [10, 10, 5])

    def test_length_cut_never_splits_an_entity(self) -> None:
        text = "甲" * 8 + "阮文成娶" + "乙" * 8  # entity 阮文成 (token 9–11) nằm ngang vị trí cắt ở token 10
        doc = {"text": text, "entities": [{"start": 8, "end": 11, "label": "PER_NAME", "text": "阮文成"}]}
        sentences = ec.convert_document(doc, unit="char", max_tokens=10)
        self.assertGreater(len(sentences), 1)  # thật sự đã cắt
        for sentence in sentences:  # mỗi câu là chuỗi BIO hợp lệ: I-X chỉ đi sau B-X/I-X cùng nhãn, ngay trong câu đó
            previous = "O"
            for _, tag in sentence:
                if tag.startswith("I-"):
                    self.assertIn(previous, (f"B-{tag[2:]}", tag))
                previous = tag
        self.assertEqual(sum(1 for _, tag in flat(sentences) if tag.startswith("B-")), 1)  # entity vẫn còn đúng 1
        self.assertEqual("".join(t for t, _ in flat(sentences)), text)

    def test_entity_longer_than_max_tokens_is_kept_whole_and_counted(self) -> None:
        doc = {"text": "阮文成娶陳氏", "entities": [{"start": 0, "end": 3, "label": "PER_NAME", "text": "阮文成"}]}
        c = Counter()
        sentences = ec.convert_document(doc, unit="char", max_tokens=2, counters=c)
        self.assertEqual(sentences[0][:3], [("阮", "B-PER_NAME"), ("文", "I-PER_NAME"), ("成", "I-PER_NAME")])
        self.assertEqual(c["entity_longer_than_max_tokens"], 1)

    def test_vi_word_level_with_punctuation_and_line_split(self) -> None:
        text = "Ông Huỳnh Tư sinh năm 1928, kết hôn với bà Nguyễn Thị Đáo.\nCon thứ nhất là Huỳnh Phổ."
        ents = []
        for s, lab in (("Huỳnh Tư", "PER_NAME"), ("1928", "DATE"), ("Nguyễn Thị Đáo", "PER_NAME"), ("Huỳnh Phổ", "PER_NAME")):
            a = text.index(s)
            ents.append({"start": a, "end": a + len(s), "label": lab, "text": s})
        sentences = ec.convert_document({"text": text, "entities": ents}, unit="word")
        self.assertEqual(len(sentences), 2)  # xuống dòng = hết câu với quốc ngữ
        toks = [t for t, _ in sentences[0]]
        tags = [g for _, g in sentences[0]]
        self.assertEqual(tags[toks.index("Huỳnh"):toks.index("Huỳnh") + 2], ["B-PER_NAME", "I-PER_NAME"])
        self.assertEqual(tags[toks.index("1928")], "B-DATE")
        self.assertEqual(tags[toks.index(",")], "O")  # dấu câu không nằm trong entity
        self.assertEqual(toks[-1], ".")

    def test_misaligned_entity_snaps_or_drops(self) -> None:
        doc = {"text": "Ông Nguyễn Văn An sinh", "entities": [{"start": 4, "end": 10, "label": "PER_NAME", "text": "Nguyễn"}]}
        # span trùng đúng token → không lệch
        c = Counter()
        ec.convert_document(doc, unit="word", counters=c)
        self.assertEqual(c["misaligned_snapped"], 0)
        bad = {"text": "Ông Nguyễn Văn An sinh", "entities": [{"start": 4, "end": 7, "label": "PER_NAME", "text": "Ngu"}]}
        c1, c2 = Counter(), Counter()
        snapped = flat(ec.convert_document(bad, unit="word", misaligned="snap", counters=c1))
        dropped = flat(ec.convert_document(bad, unit="word", misaligned="drop", counters=c2))
        self.assertEqual(dict(snapped)["Nguyễn"], "B-PER_NAME")
        self.assertEqual((c1["misaligned_snapped"], c2["misaligned_dropped"]), (1, 1))
        self.assertTrue(all(g == "O" for _, g in dropped))

    def test_two_entities_in_one_token_after_snap_drop_the_second(self) -> None:
        doc = {"text": "Nguyễn", "entities": [{"start": 0, "end": 2, "label": "PER_NAME", "text": "Ng"}, {"start": 3, "end": 6, "label": "LOC", "text": "yễn"}]}
        c = Counter()
        tags = [g for _, g in flat(ec.convert_document(doc, unit="word", misaligned="snap", counters=c))]
        self.assertEqual(tags, ["B-PER_NAME"])
        self.assertEqual(c["overlap_after_snap_dropped"], 1)

    def test_empty_text_gives_no_sentences(self) -> None:
        self.assertEqual(ec.convert_document({"text": "  \n ", "entities": []}, unit="char"), [])


class WriteTest(unittest.TestCase):
    def test_tab_separated_and_parsable_like_the_documented_parser(self) -> None:
        sentences = [[("阮", "B-PER_NAME"), ("成", "I-PER_NAME"), ("娶", "O")], [("陳", "B-PER_NAME"), ("氏", "I-PER_NAME")]]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.conll"
            self.assertEqual(ec.write_conll(path, sentences), 2)
            raw = path.read_text(encoding="utf-8")
            # đúng logic parse_conll_file trong docs/training/FINETUNE_DATA_PREPARATION.md (line.split('\t'))
            parsed, tokens, tags = [], [], []
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    if tokens:
                        parsed.append((tokens, tags)); tokens, tags = [], []
                    continue
                parts = line.split("\t")
                self.assertEqual(len(parts), 2)
                tokens.append(parts[0]); tags.append(parts[1])
            self.assertEqual(parsed, [(["阮", "成", "娶"], ["B-PER_NAME", "I-PER_NAME", "O"]), (["陳", "氏"], ["B-PER_NAME", "I-PER_NAME"])])
            ec.write_conll(path, sentences, sep=" ")
            self.assertIn("阮 B-PER_NAME", path.read_text(encoding="utf-8"))


class DatasetTest(unittest.TestCase):
    def _make(self, root: Path) -> dict:
        gold, human = root / "silver", root / "human"
        for base in (gold, human):
            base.mkdir()
        trees = {}
        for tree_id in range(1, 11):
            text = f"Ông Nguyễn {tree_id} sinh năm 19{tree_id:02d}."
            ent = [{"start": 4, "end": 10, "label": "PER_NAME", "text": "Nguyễn"}]
            for base in (gold, human) if tree_id <= 3 else (gold,):
                (base / str(tree_id)).mkdir()
                (base / str(tree_id) / "gold.training.json").write_text(
                    json.dumps({"doc_id": tree_id, "tree_id": tree_id, "text": text, "entities": ent, "relations": [], "source": "t"}), encoding="utf-8")
            trees[tree_id] = text
        strat = root / "stratified.json"
        strat.write_text(json.dumps({"documents": [{"tree_id": 9, "split": "test"}, {"tree_id": 10, "split": "test"}, {"tree_id": 1, "split": "train"}]}), encoding="utf-8")
        return {"gold_dir": gold, "human_dir": human, "stratified_path": strat}

    def test_vi_splits_by_tree_match_the_sft_plan_and_never_leak(self) -> None:
        from label_studio_pipeline.build_llm_sft_dataset import plan_splits

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._make(root)
            out = root / "out"
            summary = ec.export_vi_dataset(
                output_dir=out, val_ratio=0.25, seed=7, prefer_human=True, max_tokens=64, misaligned="snap", sep="\t", **paths
            )
            plan = plan_splits(val_ratio=0.25, seed=7, prefer_human=True, **paths)
            for split, items in plan.items():
                self.assertEqual(summary["splits"][split]["tree_ids"], [t for t, _ in items])  # cùng cách chia với bộ SFT
            train = {t for t, _ in plan["train"]}
            val = {t for t, _ in plan["val"]}
            test = {t for t, _ in plan["test_human"]}
            self.assertEqual(test, {9, 10})
            self.assertFalse(train & val or train & test or val & test)  # không rò rỉ giữa các tập
            for name in ("train", "val", "test_human", "test_silver"):
                self.assertTrue((out / f"{name}.conll").exists())
            self.assertTrue((out / "stats.json").exists())
            self.assertGreater(summary["splits"]["train"]["entities_out"], 0)

    def test_non_vi_docs_are_skipped_in_the_vi_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._make(root)
            doc_path = paths["gold_dir"] / "2" / "gold.training.json"
            doc = json.loads(doc_path.read_text(encoding="utf-8")); doc["lang"] = "han"
            doc_path.write_text(json.dumps(doc), encoding="utf-8")
            summary = ec.export_vi_dataset(output_dir=root / "o", val_ratio=0.25, seed=7, prefer_human=False, max_tokens=64, misaligned="snap", sep="\t", **paths)
            self.assertEqual(sum(s.get("skipped_non_vi", 0) for s in summary["splits"].values()), 1)

    def test_files_mode_han_char_level(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "han.json"
            src.write_text(json.dumps(HAN_DOC, ensure_ascii=False), encoding="utf-8")
            out = root / "han.conll"
            summary = ec.export_files([src], output=out, unit="char", line_breaks="auto", misaligned="snap", max_tokens=500, sep="\t")
            self.assertEqual((summary["docs"], summary["entities_out"], summary["offset_ok"]), (1, 8, 8))
            self.assertTrue(out.with_suffix(".stats.json").exists())
            self.assertIn("清\tB-PER_NAME", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
