import tempfile
import unittest
from pathlib import Path

from tools import tao_tu_dien_han_viet as T


class TuDienHanVietTest(unittest.TestCase):
    def test_reads_thieu_chuu_heads_and_orders_by_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "tc.txt"
            src.write_text("生=sanh, sinh [sheng1]\\n\\t1. Sống.\n丁=Ðinh [ding1]\\n\\t1. Can.\n", encoding="utf-8")
            base = T.read_thieu_chuu(src)
        self.assertEqual(base, {"生": ["sanh", "sinh"], "丁": ["đinh"]})
        table = T.build(base, {"乙": ["ất"]}, {"甡": ["生"]}, [("生於", "sinh năm"), ("生", "Sinh ra")])
        self.assertEqual(table["生"], ["sinh", "sanh"])
        self.assertEqual(table["甡"], ["sinh", "sanh"])  # dị thể không có trong kho: theo thứ tự đã xếp của chữ gốc
        self.assertEqual(table["乙"], ["ất"])
