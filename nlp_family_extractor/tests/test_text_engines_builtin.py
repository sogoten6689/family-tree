import json
import unittest
from unittest import mock

from app.hannom import text_engines
from app.hannom.text_engines_builtin import build_line_translation_prompt, kim_gemini_engine
from app.workspace.llm_import import parse_import


def fake_translate(n_lines_out=None, raw=None):
    calls = []

    def translate(prompt: str) -> str:
        calls.append(prompt)
        if raw is not None:
            return raw
        n = n_lines_out if n_lines_out is not None else prompt.count("[Hán]")
        return json.dumps({"vi": [f"dịch {i}" for i in range(1, n + 1)]}, ensure_ascii=False)

    translate.calls = calls
    return translate


class KimGeminiEngineTest(unittest.TestCase):
    def test_one_record_per_line_when_counts_match(self) -> None:
        tr = fake_translate()
        out = kim_gemini_engine(
            "先祖考\n朱公字三品\n",
            page_number=4,
            transliterate=lambda text: ["Tiên tổ khảo", "Chu công tự tam phẩm"],
            translate=tr,
        )
        self.assertEqual(
            out,
            [{"cn": "先祖考", "sv": "Tiên tổ khảo", "vi": "dịch 1"}, {"cn": "朱公字三品", "sv": "Chu công tự tam phẩm", "vi": "dịch 2"}],
        )
        self.assertEqual(len(tr.calls), 1)  # đúng 1 lần gọi Gemini / trang
        self.assertIn("đúng 2 chuỗi", tr.calls[0])

    def test_kim_line_mismatch_merges_page(self) -> None:
        out = kim_gemini_engine(
            "先祖考\n朱公", page_number=1, transliterate=lambda t: ["Tiên tổ khảo Chu công"], translate=fake_translate()
        )
        self.assertEqual(out, [{"cn": "先祖考 朱公", "sv": "Tiên tổ khảo Chu công", "vi": "dịch 1"}])

    def test_gemini_wrong_count_merges_real_translation(self) -> None:
        out = kim_gemini_engine(
            "甲\n乙\n丙", page_number=1, transliterate=lambda t: ["giáp", "ất", "bính"], translate=fake_translate(n_lines_out=2)
        )
        self.assertEqual(out, [{"cn": "甲 乙 丙", "sv": "giáp ất bính", "vi": "dịch 1 dịch 2"}])

    def test_gemini_not_json_fails_without_placeholder(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "không trả JSON"):
            kim_gemini_engine("甲", page_number=7, transliterate=lambda t: ["giáp"], translate=fake_translate(raw="xin lỗi"))

    def test_empty_transliteration_fails(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "không trả về phiên âm"):
            kim_gemini_engine("甲", page_number=1, transliterate=lambda t: [], translate=fake_translate())

    def test_empty_page_calls_nothing(self) -> None:
        tr = fake_translate()
        self.assertEqual(kim_gemini_engine("  \n", page_number=1, transliterate=lambda t: 1 / 0, translate=tr), [])
        self.assertEqual(tr.calls, [])

    def test_missing_google_key_is_clear_error(self) -> None:
        with mock.patch("app.config.get_google_api_key", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "GOOGLE_API_KEY"):
                kim_gemini_engine("甲", page_number=1, transliterate=lambda t: ["giáp"])

    def test_output_passes_import_validation(self) -> None:
        out = kim_gemini_engine("甲\n乙", page_number=3, transliterate=lambda t: ["giáp", "ất"], translate=fake_translate())
        parsed = parse_import({"source": "engine-kim_gemini", "records": [{**r, "page": 3} for r in out]}, {3})
        self.assertEqual((parsed.errors, parsed.record_count), ([], 2))

    def test_prompt_numbers_lines(self) -> None:
        p = build_line_translation_prompt([("甲", "giáp"), ("乙", "ất")])
        self.assertIn("1. [Hán] 甲", p)
        self.assertIn("2. [Hán] 乙", p)


class RegistryTest(unittest.TestCase):
    def test_builtin_registered_and_echo_gone(self) -> None:
        text_engines.load_local_engines()
        self.assertIn("kim_gemini", text_engines.registered_engines())
        self.assertNotIn("echo", text_engines.registered_engines())


if __name__ == "__main__":
    unittest.main()
