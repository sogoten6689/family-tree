"""Test vote theo từng chữ (offline). Chạy: python -m pytest scripts/test_vote_char_majority.py -q"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vote_char_majority import find_order_mismatch, find_outliers, vote_page_chars  # noqa: E402


def statuses(result):
    return {s.index: s.status for s in result.slots if s.kind == "char"}


class VoteCharMajorityTest(unittest.TestCase):
    # Ví dụ thật nom-147 tr.4 dòng 3: Paddle 王, ba engine kia 三 → tự sửa (3/4).
    def test_three_of_four_auto_fixes(self) -> None:
        r = vote_page_chars(
            {
                "paddle_v6": ["先祖考朱公字王品"],
                "kim_hannom_lab": ["先祖考未公字三品"],
                "deepseek": ["先祖考朱公字三品"],
                "google_vision": ["先祖专来公字三品"],
            },
            "paddle_v6",
        )
        self.assertEqual(r.lines, ["先祖考朱公字三品"])
        self.assertEqual(statuses(r)[6], "auto_fixed")
        self.assertEqual(statuses(r)[3], "kept_weak")  # 朱 2 phiếu, 未/来 mỗi chữ 1

    # nom-147 tr.4 dòng 2: nền 姚, Kim + DeepSeek 妣, Google 姊 → 2/4 chỉ đề xuất.
    def test_two_of_four_only_suggests(self) -> None:
        r = vote_page_chars(
            {"paddle_v6": ["光祖姚朱"], "kim_hannom_lab": ["光祖妣朱"], "deepseek": ["先祖妣朱"], "google_vision": ["光柱姊朱"]},
            "paddle_v6",
        )
        self.assertEqual(r.lines, ["光祖姚朱"])
        slot = next(s for s in r.slots if s.kind == "char" and s.index == 2)
        self.assertEqual((slot.status, slot.proposal), ("suggested", "妣"))

    def test_tie_keeps_backbone(self) -> None:
        r = vote_page_chars({"a": ["甲"], "b": ["甲"], "c": ["乙"], "d": ["乙"]}, "a")
        self.assertEqual((r.lines, statuses(r)[0]), (["甲"], "tie"))

    def test_all_different_is_tie(self) -> None:
        r = vote_page_chars({"a": ["舉"], "b": ["肆"], "c": ["輝"], "d": ["福"]}, "a")
        self.assertEqual((r.lines, statuses(r)[0]), (["舉"], "tie"))

    def test_insert_and_delete_are_never_automatic(self) -> None:
        # 3 engine có thêm 諱, nền không có → chỉ đề xuất chèn; 3 engine thiếu 朱 → chỉ đề xuất xoá.
        r = vote_page_chars({"a": ["先考公"], "b": ["先考諱公"], "c": ["先考諱公"], "d": ["先考諱公"]}, "a")
        self.assertEqual(r.lines, ["先考公"])
        ins = next(s for s in r.slots if s.kind == "insert")
        self.assertEqual((ins.status, ins.proposal), ("suggested", "諱"))
        r2 = vote_page_chars({"a": ["先朱考"], "b": ["先考"], "c": ["先考"], "d": ["先考"]}, "a")
        self.assertEqual(r2.lines, ["先朱考"])
        slot = next(s for s in r2.slots if s.kind == "char" and s.index == 1)
        self.assertEqual((slot.status, slot.proposal), ("suggested", ""))

    def test_line_breaks_do_not_matter_and_backbone_lines_kept(self) -> None:
        r = vote_page_chars(
            {"a": ["天地", "玄王"], "b": ["天地玄黃"], "c": ["天", "地玄黃"], "d": ["天地玄", "黃"]}, "a"
        )
        self.assertEqual(r.lines, ["天地", "玄黃"])

    def test_punctuation_and_latin_ignored(self) -> None:
        r = vote_page_chars({"a": ["孺人"], "b": ["孺人。"], "c": ["孺 人"], "d": ["孺人 abc"]}, "a")
        self.assertEqual(set(statuses(r).values()), {"unanimous"})

    def test_review_rate(self) -> None:
        r = vote_page_chars({"a": ["甲乙丙丁"], "b": ["甲乙丙戊"], "c": ["甲乙丙己"], "d": ["甲乙丙庚"]}, "a")
        self.assertAlmostEqual(r.review_rate(), 0.25)


class ScreeningTest(unittest.TestCase):
    # DeepSeek đọc lặp không dừng (nom-557 tr.49: 52.232 chữ) → không cho bỏ phiếu.
    def test_runaway_engine_is_outlier(self) -> None:
        texts = {"a": "天地玄黃宇宙洪荒" * 3, "b": "天地玄黃宇宙洪荒" * 3, "c": "日月盈昃辰宿列張" * 40}
        self.assertEqual(set(find_outliers(texts)), {"c"})

    def test_short_or_two_engine_pages_never_outlier(self) -> None:
        self.assertEqual(find_outliers({"a": "甲", "b": "乙", "c": "丙"}), {})
        self.assertEqual(find_outliers({"a": "天地玄黃" * 10, "b": "日月盈昃" * 40}), {})

    def test_reordered_engine_excluded_from_vote(self) -> None:
        bb = "天地玄黃宇宙洪荒日月盈昃辰宿列張"
        moved = "辰宿列張日月盈昃宇宙洪荒天地玄黃"  # cùng chữ, đảo thứ tự 4 đoạn
        self.assertIn("c", find_order_mismatch({"a": bb, "b": bb, "c": moved}, "a"))
        r = vote_page_chars({"a": [bb], "b": [bb], "c": [moved], "d": [bb]}, "a")
        self.assertEqual((r.page_status, set(r.excluded), r.lines), ("partial", {"c"}, [bb]))

    def test_page_unaligned_when_fewer_than_two_voters(self) -> None:
        bb = "天地玄黃宇宙洪荒日月盈昃辰宿列張"
        moved = "辰宿列張日月盈昃宇宙洪荒天地玄黃"
        r = vote_page_chars({"a": [bb], "b": [moved]}, "a")
        self.assertEqual(r.page_status, "unaligned")
        self.assertEqual(r.review_rate(), 1.0)
        self.assertEqual(r.lines, [bb])

    def test_screen_off_keeps_all_engines(self) -> None:
        bb = "天地玄黃宇宙洪荒日月盈昃辰宿列張"
        r = vote_page_chars({"a": [bb], "b": ["辰宿列張日月盈昃宇宙洪荒天地玄黃"]}, "a", screen=False)
        self.assertEqual(r.page_status, "ok")


if __name__ == "__main__":
    unittest.main()
