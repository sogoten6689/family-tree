"""Test export_page_bbox (không đọc dữ liệu thật).

Chạy từ research/hannom-bilingual-dataset/:  python -m pytest scripts/test_export_page_bbox.py -q
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from export_page_bbox import fits_image, ordered_boxes  # noqa: E402


def box(x0, y0, x1, y1, text, score=0.9):
    return ([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], text, score)


class ExportPageBboxTest(unittest.TestCase):
    def test_reading_order_right_to_left_and_xyxy(self) -> None:
        out = ordered_boxes([box(10, 0, 50, 500, "左"), box(100, 0, 140.6, 500, "右"), box(60, 0, 90, 10, " ")])
        self.assertEqual([(b["order"], b["han"]) for b in out], [(1, "右"), (2, "左")])
        self.assertEqual(out[0]["bbox_xyxy"], [100, 0, 141, 500])
        self.assertEqual(out[0]["confidence"], 0.9)

    def test_fits_image_with_tolerance(self) -> None:
        boxes = ordered_boxes([box(0, 0, 1005, 800, "甲")])
        self.assertTrue(fits_image(boxes, (1000, 800)))
        self.assertFalse(fits_image(boxes, (500, 400)))  # ảnh đã bị thu nhỏ → khung lệch
        self.assertTrue(fits_image(boxes, None))


if __name__ == "__main__":
    unittest.main()
