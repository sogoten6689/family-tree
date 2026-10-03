import unittest

from app.hannom.vote_diff import annotate_vote_diffs, char_diff_segments, voted_line_segments


def _rebuild_other(segments):
    return "".join(s.get("text", "") for s in segments)


class CharDiffSegmentsTest(unittest.TestCase):
    def test_equal_lines_single_equal_segment(self) -> None:
        self.assertEqual(char_diff_segments("家譜", "家譜"), [{"op": "equal", "text": "家譜"}])

    def test_replace_insert_delete(self) -> None:
        segs = char_diff_segments("阮族家譜", "阮氏族譜")
        ops = [s["op"] for s in segs]
        self.assertIn("insert", ops)  # 氏 thừa
        self.assertIn("delete", ops)  # 家 thiếu
        self.assertEqual(_rebuild_other(segs), "阮氏族譜")

    def test_non_bmp_counted_as_one_char(self) -> None:
        # 𠀀 (U+20000) là 2 đơn vị UTF-16 ở JS nhưng 1 code point ở Python.
        segs = char_diff_segments("𠀀家譜", "家譜")
        self.assertEqual(segs[0], {"op": "delete", "missing": 1})
        self.assertEqual(_rebuild_other(segs), "家譜")

    def test_other_text_always_reconstructable(self) -> None:
        for voted, other in [("", "家"), ("家", ""), ("𠀀𠀁家", "𠀁家𠀂"), ("abc", "xyz")]:
            self.assertEqual(_rebuild_other(char_diff_segments(voted, other)), other)


class VotedLineSegmentsTest(unittest.TestCase):
    def test_contested_marks_replaced_and_missing_chars(self) -> None:
        segs = voted_line_segments("阮族家譜", [{"text": "阮氏族譜"}])
        self.assertEqual("".join(s["text"] for s in segs), "阮族家譜")
        contested = "".join(s["text"] for s in segs if s["contested"])
        self.assertEqual(contested, "家")

    def test_no_disagreeing_means_nothing_contested(self) -> None:
        self.assertEqual(voted_line_segments("家譜", []), [{"text": "家譜", "contested": False}])

    def test_empty_voted(self) -> None:
        self.assertEqual(voted_line_segments("", [{"text": "家"}]), [])

    def test_non_bmp_contested(self) -> None:
        segs = voted_line_segments("𠀀家", [{"text": "𠀁家"}])
        self.assertEqual(segs, [{"text": "𠀀", "contested": True}, {"text": "家", "contested": False}])


class AnnotateVoteDiffsTest(unittest.TestCase):
    def test_adds_fields_without_touching_existing(self) -> None:
        meta = {
            "vote_method": "x",
            "uncertain_spans": [
                {"line": 0, "voted_line": "家譜", "disagreeing": [{"engine": "e2", "text": "家諸", "similarity": 0.5}]}
            ],
        }
        out = annotate_vote_diffs(meta)
        span = out["uncertain_spans"][0]
        self.assertEqual(span["line"], 0)
        self.assertEqual(span["disagreeing"][0]["engine"], "e2")
        self.assertIn("voted_segments", span)
        self.assertIn("diff", span["disagreeing"][0])

    def test_idempotent(self) -> None:
        meta = {"uncertain_spans": [{"voted_line": "家譜", "disagreeing": [{"text": "家"}]}]}
        first = annotate_vote_diffs(meta)["uncertain_spans"][0]["voted_segments"]
        second = annotate_vote_diffs(meta)["uncertain_spans"][0]["voted_segments"]
        self.assertEqual(first, second)

    def test_none_passthrough(self) -> None:
        self.assertIsNone(annotate_vote_diffs(None))


class SchemaV2PassThroughTest(unittest.TestCase):
    def test_v2_meta_returned_unchanged(self) -> None:
        meta = {"schema_version": 2, "vote_method": "char_majority", "slots": [], "uncertain_spans": [{"voted_line": "家", "disagreeing": []}]}
        before = repr(meta)
        self.assertIs(annotate_vote_diffs(meta), meta)
        self.assertEqual(repr(meta), before)


if __name__ == "__main__":
    unittest.main()
