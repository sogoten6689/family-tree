import json
import unittest

from app.hannom.vote_char import (
    build_vote_meta,
    choose_backbone,
    find_order_mismatch,
    find_outliers,
    vote_page,
    vote_page_chars,
)


def statuses(result):
    return {s.index: s.status for s in result.slots if s.kind == "char"}


class VoteRuleTest(unittest.TestCase):
    # nom-147 tr.4: Paddle 王, ba engine kia 三 → tự sửa (≥3 phiếu).
    def test_three_votes_auto_fix(self) -> None:
        r = vote_page_chars(
            {"paddle_v6": ["先祖考朱公字王品"], "kim": ["先祖考未公字三品"], "deepseek": ["先祖考朱公字三品"], "gv": ["先祖专来公字三品"]},
            "paddle_v6",
        )
        self.assertEqual(r.lines, ["先祖考朱公字三品"])
        self.assertEqual(statuses(r)[6], "auto_fixed")

    def test_two_votes_only_suggest(self) -> None:
        r = vote_page_chars({"a": ["光祖姚朱"], "b": ["光祖妣朱"], "c": ["先祖妣朱"], "d": ["光柱姊朱"]}, "a")
        slot = next(s for s in r.slots if s.kind == "char" and s.index == 2)
        self.assertEqual((r.lines, slot.status, slot.proposal), (["光祖姚朱"], "suggested", "妣"))

    def test_three_of_five_auto_fix(self) -> None:  # Lâm chốt: ngưỡng ≥3 phiếu tuyệt đối
        r = vote_page_chars({"a": ["王"], "b": ["王"], "c": ["三"], "d": ["三"], "e": ["三"]}, "a")
        self.assertEqual((r.lines, statuses(r)[0]), (["三"], "auto_fixed"))

    def test_three_engines_never_auto_fix(self) -> None:  # 2/3 chỉ đề xuất
        r = vote_page_chars({"a": ["王"], "b": ["三"], "c": ["三"]}, "a")
        self.assertEqual((r.lines, statuses(r)[0]), (["王"], "suggested"))

    def test_tie_keeps_backbone(self) -> None:
        r = vote_page_chars({"a": ["甲"], "b": ["甲"], "c": ["乙"], "d": ["乙"]}, "a")
        self.assertEqual((r.lines, statuses(r)[0]), (["甲"], "tie"))

    def test_insert_delete_only_suggested(self) -> None:
        r = vote_page_chars({"a": ["先考公"], "b": ["先考諱公"], "c": ["先考諱公"], "d": ["先考諱公"]}, "a")
        ins = next(s for s in r.slots if s.kind == "insert")
        self.assertEqual((r.lines, ins.status, ins.proposal), (["先考公"], "suggested", "諱"))
        r2 = vote_page_chars({"a": ["先朱考"], "b": ["先考"], "c": ["先考"], "d": ["先考"]}, "a")
        self.assertEqual(r2.lines, ["先朱考"])

    def test_line_breaks_ignored_backbone_lines_kept(self) -> None:
        r = vote_page_chars({"a": ["天地", "玄王"], "b": ["天地玄黃"], "c": ["天", "地玄黃"], "d": ["天地玄", "黃"]}, "a")
        self.assertEqual(r.lines, ["天地", "玄黃"])

    def test_non_bmp_counts_as_one_char(self) -> None:
        r = vote_page_chars({"a": ["𠀀家"], "b": ["𠀀家"], "c": ["𠀀家"]}, "a")
        self.assertEqual(r.counts()["unanimous"], 2)


class ScreeningAndBackboneTest(unittest.TestCase):
    def test_runaway_engine_outlier(self) -> None:
        texts = {"a": "天地玄黃宇宙洪荒" * 3, "b": "天地玄黃宇宙洪荒" * 3, "c": "日月盈昃辰宿列張" * 40}
        self.assertEqual(set(find_outliers(texts)), {"c"})

    def test_order_mismatch(self) -> None:
        bb = "天地玄黃宇宙洪荒日月盈昃辰宿列張"
        self.assertIn("c", find_order_mismatch({"a": bb, "b": bb, "c": "辰宿列張日月盈昃宇宙洪荒天地玄黃"}, "a"))

    # Phan gia tr.76: 2 engine luôn hoà điểm → trước đây priority chọn Google Vision (21 chữ rác).
    def test_tie_prefers_engine_with_more_han(self) -> None:
        texts = {"google_vision": "美長春", "gemini": "美川伯尚書宰尉公通判公"}
        self.assertEqual(choose_backbone(texts, ["google_vision", "gemini"]), "gemini")

    def test_runaway_never_backbone(self) -> None:
        texts = {"a": "天地玄黃宇宙洪荒", "b": "天地玄黃宇宙洪黃", "c": "日月盈昃" * 50}
        self.assertNotEqual(choose_backbone(texts, ["c", "a", "b"]), "c")

    def test_vote_page_end_to_end_and_unaligned(self) -> None:
        v = vote_page({"gemini": ["美川伯", "尚書公"], "google_vision": ["146"]}, ["google_vision", "gemini"])
        self.assertEqual((v.backbone, v.page_status, v.lines), ("gemini", "unaligned", ["美川伯", "尚書公"]))
        self.assertEqual(v.review_rate(), 1.0)


class VoteMetaV2Test(unittest.TestCase):
    def test_meta_shape_and_json_serialisable(self) -> None:
        lines = {"a": ["先祖考王品"], "b": ["先祖考三品"], "c": ["先祖考三品"], "d": ["先祖考三品"], "e": ["日月盈昃" * 30]}
        v = vote_page(lines, ["a"])
        meta = build_vote_meta(v, lines)
        json.dumps(meta, ensure_ascii=False)
        self.assertEqual((meta["schema_version"], meta["vote_method"], meta["page_status"]), (2, "char_majority", "partial"))
        self.assertEqual(meta["thresholds"], {"auto_min": 3, "suggest_min": 2})
        self.assertIn("lạc đề", meta["engines"]["e"]["excluded"])
        self.assertFalse(meta["engines"]["e"]["voted"])
        self.assertEqual(meta["uncertain_rate"], meta["review_rate"])
        self.assertTrue(all(s["status"] != "unanimous" for s in meta["slots"]))
        self.assertEqual(meta["stats"]["chars"], 5)
        self.assertEqual(meta["lines"], v.lines)


if __name__ == "__main__":
    unittest.main()
