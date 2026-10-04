"""Test adapter gpt_vision (giả lập HTTP — không gọi OpenAI thật, không tốn tiền).

Chạy từ research/hannom-bilingual-dataset/:  python -m pytest scripts/test_gpt_vision.py -q
"""

import base64
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ocr_adapters import gpt_vision  # noqa: E402


class FakeResp:
    def __init__(self, status=200, content="", text=""):
        self.status_code, self._content, self.text = status, content, text

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


class GptVisionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "book" / "pages").mkdir(parents=True)
        (self.root / "book" / "pages" / "001.jpg").write_bytes(b"\xff\xd8img")
        self.book = {"paths": {"root": "book"}}
        self.env = mock.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test", "OPENAI_OCR_MODEL": "gpt-test"})
        self.env.start()
        gpt_vision._ENV_LOADED = True  # không đọc .env thật

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def _load(self, resp):
        with mock.patch("requests.post", return_value=resp) as post:
            out = gpt_vision.load(self.book, "001", self.root)
        return out, post

    def test_reads_lines_and_sends_image_with_model(self) -> None:
        out, post = self._load(FakeResp(content="先祖考朱公\n字三品\n"))
        self.assertEqual((out.engine, out.lines), ("gpt_vision", ["先祖考朱公", "字三品"]))
        body = post.call_args.kwargs["json"]
        self.assertEqual(body["model"], "gpt-test")
        url = body["messages"][0]["content"][1]["image_url"]["url"]
        self.assertEqual(url, "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8img").decode())
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer sk-test")

    def test_no_key_makes_no_call(self) -> None:
        with mock.patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            with mock.patch("requests.post") as post:
                self.assertIsNone(gpt_vision.load(self.book, "001", self.root))
        post.assert_not_called()

    def test_http_error_is_printed_not_swallowed(self) -> None:
        with mock.patch("sys.stderr") as err:
            out, _ = self._load(FakeResp(status=429, text="rate limit"))
        self.assertIsNone(out)
        self.assertIn("HTTP 429", "".join(str(c.args[0]) for c in err.write.call_args_list))

    def test_no_text_answers_are_dropped(self) -> None:
        # hxh-129 (04/10/2026): Gemini trả tiếng Việt, DeepSeek trả tiếng Trung/Anh cho trang trắng.
        for answer in (
            "Nhà bạn không có chữ nào cả, chỉ là một tờ giấy trơn.",
            "The image contains no ancient Chinese characters.",
            "这张图片是一页空白的老式纸张，上面没有任何手写或印刷的汉字。",
            "",
        ):
            out, _ = self._load(FakeResp(content=answer))
            self.assertIsNone(out, answer)

    def test_real_text_mentioning_blank_kept_when_long(self) -> None:
        long_text = "空白" + "天地玄黃宇宙洪荒" * 12
        out, _ = self._load(FakeResp(content=long_text))
        self.assertIsNotNone(out)

    def test_registered_in_vote_pipeline(self) -> None:
        import vote_ocr

        self.assertIs(vote_ocr.ADAPTERS["gpt_vision"], gpt_vision)
        self.assertIn("gpt_vision", vote_ocr.DEFAULT_PRIORITY)


if __name__ == "__main__":
    unittest.main()
