import base64
import json
import unittest
from unittest import mock

import httpx

from app import config, gemini_client
from app.ramcloud_client import RamCloudClient, RamCloudError

OK_BODY = {
    "choices": [{"message": {"content": "Xin chào"}, "finish_reason": "stop"}],
    "usage": {
        "prompt_tokens": 12,
        "completion_tokens": 5,
        "total_tokens": 17,
        "completion_tokens_details": {"reasoning_tokens": 2},
        "prompt_tokens_details": {"cached_tokens": 3},
    },
}


def _client(handler, key="sk-test-secret"):
    env = {"RAMCLOUD_KEY": key, "RAMCLOUD_MODEL": "m-test", "RAMCLOUD_BASE_URL": "https://rc.example/v1/"}
    with mock.patch.dict("os.environ", env), mock.patch.object(config, "_get_setting", return_value=None):
        return RamCloudClient(transport=httpx.MockTransport(handler))


class RamCloudClientTest(unittest.TestCase):
    def test_generate_sends_openai_payload_and_records_usage(self) -> None:
        seen: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["auth"] = request.headers["authorization"]
            seen["ua"] = request.headers["user-agent"]
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json=OK_BODY)

        with mock.patch("app.ramcloud_client.record_usage") as rec:
            text = _client(handler).generate("Chào", task="translate", json_output=True, max_output_tokens=256)
        self.assertEqual(text, "Xin chào")
        self.assertEqual(seen["url"], "https://rc.example/v1/chat/completions")  # base_url được cắt dấu "/" cuối
        self.assertEqual(seen["auth"], "Bearer sk-test-secret")
        self.assertTrue(seen["ua"].startswith("Mozilla/5.0"))  # tránh Cloudflare 1010
        self.assertEqual(seen["body"]["model"], "m-test")
        self.assertEqual(seen["body"]["messages"], [{"role": "user", "content": "Chào"}])
        self.assertEqual(seen["body"]["response_format"], {"type": "json_object"})
        self.assertEqual(seen["body"]["max_tokens"], 256)
        kwargs = rec.call_args.kwargs
        self.assertEqual((kwargs["task"], kwargs["model"], kwargs["ok"]), ("translate", "m-test", True))
        self.assertEqual(
            (kwargs["prompt_tokens"], kwargs["output_tokens"], kwargs["thinking_tokens"], kwargs["cached_tokens"], kwargs["total_tokens"], kwargs["finish_reason"]),
            (12, 5, 2, 3, 17, "stop"),
        )

    def test_plain_call_omits_optional_fields(self) -> None:
        seen: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json=OK_BODY)

        with mock.patch("app.ramcloud_client.record_usage"):
            _client(handler).generate("x")
        self.assertNotIn("response_format", seen["body"])
        self.assertNotIn("max_tokens", seen["body"])

    def test_vision_sends_image_as_data_url(self) -> None:
        seen: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json=OK_BODY)

        with mock.patch("app.ramcloud_client.record_usage"):
            _client(handler).generate_vision("Đọc chữ", b"\xff\xd8IMG", "image/jpeg")
        parts = seen["body"]["messages"][0]["content"]
        self.assertEqual(parts[0], {"type": "text", "text": "Đọc chữ"})
        self.assertEqual(parts[1]["image_url"]["url"], "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8IMG").decode())

    def test_http_error_raises_without_leaking_key_and_records_failure(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, text="error code: 1010")

        with mock.patch("app.ramcloud_client.record_usage") as rec:
            with self.assertRaises(RamCloudError) as ctx:
                _client(handler).generate("x", task="translate")
        self.assertIn("403", str(ctx.exception))
        self.assertNotIn("sk-test-secret", str(ctx.exception))
        self.assertFalse(rec.call_args.kwargs["ok"])
        self.assertNotIn("sk-test-secret", rec.call_args.kwargs["error"])

    def test_empty_content_returns_empty_string(self) -> None:
        body = {"choices": [{"message": {"content": None}, "finish_reason": "length"}], "usage": {}}
        with mock.patch("app.ramcloud_client.record_usage"):
            self.assertEqual(_client(lambda r: httpx.Response(200, json=body)).generate("x"), "")

    def test_missing_key_raises_clear_error(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True), mock.patch.object(config, "_get_setting", return_value=None):
            with self.assertRaises(ValueError) as ctx:
                RamCloudClient()
        self.assertIn("RAMCLOUD_KEY", str(ctx.exception))


class ProviderSelectionTest(unittest.TestCase):
    def test_default_is_google_and_unknown_falls_back(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True), mock.patch.object(config, "_get_setting", return_value=None):
            self.assertEqual(config.get_llm_provider(), "google")
        for value, expected in [("ramcloud", "ramcloud"), (" RamCloud ", "ramcloud"), ("openai", "google")]:
            with mock.patch.dict("os.environ", {"LLM_PROVIDER": value}), mock.patch.object(config, "_get_setting", return_value=None):
                self.assertEqual(config.get_llm_provider(), expected, value)

    def test_setting_beats_environment(self) -> None:
        with mock.patch.dict("os.environ", {"LLM_PROVIDER": "google"}), \
                mock.patch.object(config, "_get_setting", side_effect=lambda k: "ramcloud" if k == "LLM_PROVIDER" else None):
            self.assertEqual(config.get_llm_provider(), "ramcloud")

    def test_api_key_follows_provider(self) -> None:
        with mock.patch.object(config, "get_llm_provider", return_value="ramcloud"), \
                mock.patch.object(config, "get_ramcloud_key", return_value="rc"), \
                mock.patch.object(config, "get_google_api_key", return_value="g"):
            self.assertEqual(config.get_llm_api_key(), "rc")
        with mock.patch.object(config, "get_llm_provider", return_value="google"), \
                mock.patch.object(config, "get_ramcloud_key", return_value="rc"), \
                mock.patch.object(config, "get_google_api_key", return_value="g"):
            self.assertEqual(config.get_llm_api_key(), "g")

    def test_gemini_client_delegates_to_ramcloud_when_selected(self) -> None:
        fake = mock.Mock()
        fake.generate.return_value = "RC"
        fake.generate_vision.return_value = "RCV"
        with mock.patch.object(gemini_client, "get_llm_provider", return_value="ramcloud"), \
                mock.patch("app.ramcloud_client.RamCloudClient", return_value=fake):
            client = gemini_client.GeminiClient()  # không cần GOOGLE_API_KEY
            self.assertEqual(client.generate("p", task="translate", json_output=True, max_output_tokens=9), "RC")
            self.assertEqual(client.generate_vision("p", b"img", "image/png", task="ocr_vision"), "RCV")
        fake.generate.assert_called_once_with("p", task="translate", json_output=True, max_output_tokens=9)
        fake.generate_vision.assert_called_once_with("p", b"img", "image/png", task="ocr_vision")

    def test_gemini_client_still_requires_google_key_by_default(self) -> None:
        with mock.patch.object(gemini_client, "get_llm_provider", return_value="google"), \
                mock.patch.object(gemini_client, "get_google_api_key", return_value=None):
            with self.assertRaises(ValueError):
                gemini_client.GeminiClient()


if __name__ == "__main__":
    unittest.main()
