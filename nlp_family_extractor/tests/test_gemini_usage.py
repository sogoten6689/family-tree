import contextlib
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import gemini_client
from app.database import Base
from app.gemini_usage import GeminiUsage, record_usage, summarize, usage_from_response


def fake_response(text="ok", **usage):
    meta = SimpleNamespace(
        prompt_token_count=usage.get("p", 10),
        candidates_token_count=usage.get("o", 5),
        thoughts_token_count=usage.get("t", 20),
        cached_content_token_count=0,
        total_token_count=usage.get("total", 35),
    )
    return SimpleNamespace(text=text, usage_metadata=meta, candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))])


class FakeGenai:
    def __init__(self, response=None, error=None):
        self.calls = []
        outer = self

        class Models:
            def generate_content(self, **kwargs):
                outer.calls.append(kwargs)
                if error:
                    raise error
                return response

        self.models = Models()


def make_client(fake):
    with mock.patch.object(gemini_client, "get_google_api_key", return_value="k"), mock.patch.object(
        gemini_client.genai, "Client", return_value=fake
    ):
        return gemini_client.GeminiClient()


class GeminiClientTest(unittest.TestCase):
    def test_records_usage_per_task(self) -> None:
        fake = FakeGenai(fake_response("xin chào", p=100, o=7, t=40, total=147))
        client = make_client(fake)
        with mock.patch.object(gemini_client, "record_usage") as rec:
            self.assertEqual(client.generate("p", task="translate"), "xin chào")
        kwargs = rec.call_args.kwargs
        self.assertEqual((kwargs["task"], kwargs["ok"]), ("translate", True))
        self.assertEqual((kwargs["prompt_tokens"], kwargs["output_tokens"], kwargs["thinking_tokens"]), (100, 7, 40))
        self.assertEqual(kwargs["finish_reason"], "STOP")
        self.assertIsNone(fake.calls[0]["config"])  # không cấu hình thêm khi không yêu cầu

    def test_json_and_max_tokens_are_passed(self) -> None:
        fake = FakeGenai(fake_response("{}"))
        with mock.patch.object(gemini_client, "record_usage"):
            make_client(fake).generate("p", task="ma_dinh_danh", json_output=True, max_output_tokens=2048)
        config = fake.calls[0]["config"]
        self.assertEqual((config.response_mime_type, config.max_output_tokens), ("application/json", 2048))

    def test_error_is_recorded_and_reraised(self) -> None:
        client = make_client(FakeGenai(error=RuntimeError("quota")))
        with mock.patch.object(gemini_client, "record_usage") as rec:
            with self.assertRaises(RuntimeError):
                client.generate("p", task="translate")
        self.assertEqual((rec.call_args.kwargs["ok"], rec.call_args.kwargs["error"]), (False, "RuntimeError: quota"))

    def test_vision_default_task(self) -> None:
        with mock.patch.object(gemini_client, "record_usage") as rec:
            make_client(FakeGenai(fake_response("漢"))).generate_vision("p", b"img")
        self.assertEqual(rec.call_args.kwargs["task"], "ocr_vision")

    def test_ma_dinh_danh_generate_uses_json_and_cap(self) -> None:
        from app.workspace import ma_dinh_danh_auto

        fake_client = mock.Mock()
        fake_client.generate.return_value = "{}"
        with mock.patch("app.gemini_client.GeminiClient", return_value=fake_client):
            ma_dinh_danh_auto.default_generate()("prompt")
        fake_client.generate.assert_called_once_with(
            "prompt", task="ma_dinh_danh", json_output=True, max_output_tokens=ma_dinh_danh_auto.MAX_OUTPUT_TOKENS
        )


class UsageFromResponseTest(unittest.TestCase):
    def test_missing_fields_become_zero(self) -> None:
        usage = usage_from_response(SimpleNamespace(usage_metadata=None, candidates=[]))
        self.assertEqual((usage["prompt_tokens"], usage["thinking_tokens"], usage["finish_reason"]), (0, 0, None))


class _Db:
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine, tables=[GeminiUsage.__table__])

    @contextlib.contextmanager
    def session(self):
        db = Session(self.engine)
        try:
            yield db
            db.commit()
        finally:
            db.close()


class RecordAndSummarizeTest(_Db, unittest.TestCase):
    def _record(self, **kw):
        with mock.patch("app.database.database_enabled", return_value=True), mock.patch(
            "app.database.session_scope", self.session
        ):
            record_usage(model="m", duration_ms=10, **kw)

    def test_record_and_summarize_by_task(self) -> None:
        self._record(task="translate", ok=True, prompt_tokens=100, output_tokens=10, thinking_tokens=50, total_tokens=160)
        self._record(task="translate", ok=False, error="x")
        self._record(task="ocr_vision", ok=True, prompt_tokens=300, output_tokens=20, total_tokens=320)
        self._record(task="weird-task", ok=True, total_tokens=1)  # tên lạ → generic
        with self.session() as db:
            old = GeminiUsage(task="translate", model="m", total_tokens=999, created_at=datetime.now(timezone.utc) - timedelta(days=60))
            db.add(old)
        with self.session() as db:
            result = summarize(db, days=30)
        by_task = {t["task"]: t for t in result["tasks"]}
        self.assertEqual(by_task["translate"]["calls"], 2)
        self.assertEqual(by_task["translate"]["errors"], 1)
        self.assertEqual(by_task["translate"]["thinking_tokens"], 50)
        self.assertEqual(by_task["translate"]["total_tokens"], 160)  # bản ghi 60 ngày trước bị loại
        self.assertEqual(result["tasks"][0]["task"], "ocr_vision")  # xếp theo tổng token giảm dần
        self.assertIn("generic", by_task)
        self.assertEqual(result["total_calls"], 4)

    def test_db_failure_never_raises(self) -> None:
        with mock.patch("app.database.database_enabled", return_value=True), mock.patch(
            "app.database.session_scope", side_effect=RuntimeError("db down")
        ):
            record_usage(task="translate", model="m", duration_ms=1, ok=True)  # không văng lỗi


class EndpointTest(_Db, unittest.TestCase):
    def test_admin_summary_endpoint(self) -> None:
        from fastapi.testclient import TestClient

        import api
        from app.auth.dependencies import require_admin
        from app.database import get_db

        db = Session(self.engine)
        db.add(GeminiUsage(task="translate", model="m", total_tokens=42))
        db.commit()
        api.app.dependency_overrides[require_admin] = lambda: object()
        api.app.dependency_overrides[get_db] = lambda: db
        try:
            with mock.patch("app.settings.router.database_enabled", return_value=True):
                client = TestClient(api.app)
                body = client.get("/api/admin/gemini-usage?days=7").json()
                self.assertEqual(body["tasks"][0]["total_tokens"], 42)
                self.assertEqual(client.get("/api/admin/gemini-usage?days=0").status_code, 400)
        finally:
            api.app.dependency_overrides.clear()
            db.close()


if __name__ == "__main__":
    unittest.main()
