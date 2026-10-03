"""Test thứ tự cột của adapter paddle_v6 (offline, không gọi API).

Chạy từ research/hannom-bilingual-dataset/:  python -m pytest scripts/test_paddle_column_order.py -q
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ocr_adapters import paddle_v6  # noqa: E402
from ocr_adapters.paddle_v6 import column_order, column_order_indices  # noqa: E402


def box(x0, x1, y0, y1, text, score=0.9):
    return ([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], text, score)


# Toạ độ thật của nom-1255 tr.1 (PaddleOCR trả theo mép trên, cột bị xáo trộn).
NOM_1255_P1 = [
    box(101, 182, 93, 955, "子朱子之後衣畜也理學之傳有自來矣遭"),
    box(179, 256, 95, 610, "先師姓朱氏中國大明人"),
    box(474, 548, 90, 952, "先師駕陽面傳修譜美德府貞節總"),
    box(251, 323, 101, 380, "國之有史我"),
    box(546, 621, 100, 887, "皇朝維新五年歲次辛亥六月初六日"),
    box(32, 104, 147, 950, "清莅位希伯夷風一心忠孝隨父南"),
    box(325, 406, 162, 969, "咨問會員黎文饒窃念夫嬴之有譜猶"),
    box(398, 472, 164, 964, "農溪社首正總賞受九品百戶領本省為"),
]


class ColumnOrderTest(unittest.TestCase):
    def test_real_page_reads_right_to_left_like_other_engines(self) -> None:
        texts = [t for t, _ in column_order(NOM_1255_P1)]
        # Thứ tự Kim Hán Nôm / DeepSeek / Google Vision / Gemini cùng đọc, khớp ảnh gốc.
        self.assertEqual(
            [t[:4] for t in texts],
            ["皇朝維新", "先師駕陽", "農溪社首", "咨問會員", "國之有史", "先師姓朱", "子朱子之", "清莅位希"],
        )

    def test_split_column_stays_together_top_to_bottom(self) -> None:
        boxes = [box(0, 50, 0, 100, "左"), box(100, 150, 300, 400, "右下"), box(102, 148, 0, 200, "右上")]
        self.assertEqual([t for t, _ in column_order(boxes)], ["右上", "右下", "左"])

    def test_empty_boxes_dropped(self) -> None:
        self.assertEqual(column_order([box(0, 10, 0, 10, "  "), box(20, 30, 0, 10, "字")]), [("字", 0.9)])

    # A1 — chú thích chữ nhỏ 2 hàng dưới cột chữ lớn (toạ độ thật nom-1158 tr.5):
    # khung trái có mép trên cao hơn 2px nhưng vẫn phải đọc SAU khung phải.
    def test_small_double_notes_read_right_then_left(self) -> None:
        boxes = [
            box(554, 587, 132, 280, "六世甲支祖妣忌辰"),
            box(573, 592, 275, 351, "十月初六日"),
            box(554, 579, 273, 400, "塟在東床社同枚處"),
        ]
        self.assertEqual(
            [t for t, _ in column_order(boxes)], ["六世甲支祖妣忌辰", "十月初六日", "塟在東床社同枚處"]
        )

    def test_notes_do_not_interleave_with_text_below(self) -> None:
        boxes = [
            box(100, 150, 0, 200, "大字"),
            box(126, 150, 210, 300, "右注"),
            box(100, 124, 205, 290, "左注"),
            box(100, 150, 320, 500, "下文"),
        ]
        self.assertEqual([t for t, _ in column_order(boxes)], ["大字", "右注", "左注", "下文"])

    # A2 — cột nghiêng: các khung lệch dần theo x vẫn là 1 cột.
    def test_skewed_column_stays_one_column(self) -> None:
        boxes = [box(100, 140, 0, 100, "一"), box(108, 148, 110, 210, "二"), box(116, 156, 220, 320, "三"),
                 box(40, 80, 0, 320, "左")]
        self.assertEqual([t for t, _ in column_order(boxes)], ["一", "二", "三", "左"])

    # A3 — khung 1 chữ nằm lệch giữa 2 cột chỉ vào 1 cột, không làm lẫn thứ tự 2 cột.
    def test_single_char_between_columns_joins_one(self) -> None:
        boxes = [box(100, 140, 0, 300, "右"), box(40, 80, 0, 300, "左"), box(78, 104, 310, 340, "字")]
        order = [t for t, _ in column_order(boxes)]
        self.assertLess(order.index("右"), order.index("左"))
        self.assertEqual(len(order), 3)

    # A4 — trang đôi (2 trang in cạnh nhau): hết trang phải rồi mới sang trang trái.
    def test_spread_reads_right_page_first(self) -> None:
        boxes = [box(x, x + 40, 0, 500, f"左{i}") for i, x in enumerate((300, 200, 100))]
        boxes += [box(x, x + 40, 0, 500, f"右{i}") for i, x in enumerate((900, 800, 700))]
        self.assertEqual([t for t, _ in column_order(boxes)], ["右0", "右1", "右2", "左0", "左1", "左2"])

    # A5 — chữ ngang (số trang, chữ Latin): KHÔNG xử lý riêng, xếp theo vị trí x
    # như 1 khung thường (hành vi được ghi lại, không phải "đúng" tuyệt đối).
    def test_horizontal_box_is_placed_by_x(self) -> None:
        boxes = [box(100, 140, 0, 300, "右"), box(40, 80, 0, 300, "左"), box(60, 120, 320, 340, "47")]
        self.assertEqual([t for t, _ in column_order(boxes)], ["右", "47", "左"])

    # A6 — dữ liệu bẩn.
    def test_dirty_inputs(self) -> None:
        octagon = [[10, 0], [20, 0], [30, 5], [30, 95], [20, 100], [10, 100], [0, 95], [0, 5]]
        out = column_order([(octagon, "八", None), box(50, 60, 0, 100, "右", None), box(50, 60, 0, 100, "\n")])
        self.assertEqual(out, [("右", None), ("八", None)])
        self.assertEqual(column_order([]), [])

    def test_indices_distinguish_boxes_with_same_text(self) -> None:
        # nom-147 tr.35: 2 khung cùng chữ 掃墓節祭文 ở 2 trang — chỉ số phải trỏ đúng khung.
        boxes = [box(0, 10, 0, 10, "掃墓"), box(100, 110, 0, 10, "掃墓"), box(50, 60, 0, 10, "中")]
        self.assertEqual(column_order_indices(boxes), [1, 2, 0])

    def test_identical_boxes_keep_both(self) -> None:
        self.assertEqual(len(column_order([box(0, 10, 0, 10, "同"), box(0, 10, 0, 10, "同")])), 2)

    # A7 — tất định: cùng input (kể cả thứ tự khác) → cùng output.
    def test_deterministic_regardless_of_input_order(self) -> None:
        expected = column_order(NOM_1255_P1)
        self.assertEqual(column_order(list(reversed(NOM_1255_P1))), expected)
        self.assertEqual(column_order(sorted(NOM_1255_P1, key=lambda b: b[1])), expected)

    def test_deterministic_with_tied_positions(self) -> None:
        tied = [box(0, 10, 0, 10, "甲"), box(0, 10, 0, 10, "乙"), box(20, 30, 0, 10, "丙")]
        self.assertEqual(column_order(tied), column_order(list(reversed(tied))))


class LoadTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "book" / "paddleocr").mkdir(parents=True)
        self.book = {"paths": {"root": "book"}}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, name: str, content: str) -> None:
        (self.root / "book" / "paddleocr" / name).write_text(content, encoding="utf-8")

    def test_prefers_json_and_sorts_columns(self) -> None:
        self.write("001-paddleocr.txt", "左\n右\n")
        bbox = [[b[0], [b[1], b[2]]] for b in (box(0, 50, 0, 100, "左", 0.5), box(100, 150, 0, 100, "右", 0.8))]
        self.write("001-paddleocr.json", json.dumps({"result_bbox": bbox}))
        result = paddle_v6.load(self.book, "001", self.root)
        self.assertEqual(result.lines, ["右", "左"])
        self.assertEqual(result.scores, {"右": 0.8, "左": 0.5})

    def test_falls_back_to_txt_without_json(self) -> None:
        self.write("001-paddleocr.txt", "甲\n\n乙\n")
        self.assertEqual(paddle_v6.load(self.book, "001", self.root).lines, ["甲", "乙"])

    def test_missing_returns_none(self) -> None:
        self.assertIsNone(paddle_v6.load(self.book, "002", self.root))


if __name__ == "__main__":
    unittest.main()
