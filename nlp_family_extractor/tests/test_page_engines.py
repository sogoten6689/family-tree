import os
import unittest
from unittest import mock

from app.hannom import engines as hannom_engines
from app.hannom.engines import EngineResult
from app.workspace import page_engines as pe
from app.workspace.repository import GiaPhaPageRepository, GiaPhaVersionRepository
from tests.test_page_images import _PagesApi


class PureLogicTest(unittest.TestCase):
    def test_present_engines_ignores_empty_text(self) -> None:
        meta = {"engines": {"paddle_v6": {"text": "漢"}, "deepseek": {"text": "  "}, "gemini": "bad"}}
        self.assertEqual(pe.present_engines(meta), {"paddle_v6"})
        self.assertEqual(pe.present_engines(None), set())
        self.assertEqual(pe.present_engines({"engines": None}), set())

    def test_merge_keeps_existing_and_does_not_mutate_input(self) -> None:
        old = {"vote_method": "x", "engines": {"paddle_v6": {"text": "甲", "score": None, "similarity_to_others": 0.5}}}
        merged = pe.merge_engine_text(old, "google_vision", "乙乙")
        self.assertEqual(set(merged["engines"]), {"paddle_v6", "google_vision"})
        self.assertEqual(merged["vote_method"], "x")
        self.assertNotIn("google_vision", old["engines"])
        self.assertEqual(merged["engines"]["google_vision"]["text"], "乙乙")

    def test_merge_into_v2_meta_marks_engine_as_not_voted(self) -> None:
        merged = pe.merge_engine_text({"schema_version": 2, "engines": {}}, "gemini", "家譜ab")
        self.assertEqual(merged["engines"]["gemini"], {"text": "家譜ab", "han_chars": 2, "voted": False, "excluded": "added-after-vote"})
        self.assertEqual(pe.merge_engine_text(None, "gemini", "字")["engines"]["gemini"]["text"], "字")

    def test_readiness_google_vision_needs_key_and_unrunnable_engines_say_why(self) -> None:
        with mock.patch.dict(os.environ, {"GOOGLE_VISION_API_KEY": ""}):
            self.assertFalse(pe.readiness(pe.BY_NAME["google_vision"])[0])
        with mock.patch.dict(os.environ, {"GOOGLE_VISION_API_KEY": "k"}):
            self.assertTrue(pe.readiness(pe.BY_NAME["google_vision"])[0])
        ok, reason = pe.readiness(pe.BY_NAME["deepseek"])
        self.assertFalse(ok)
        self.assertIn("DeepSeek", reason)

    def test_google_vision_adapter_returns_lines_or_none(self) -> None:
        response = mock.Mock(status_code=200)
        response.json.return_value = {"responses": [{"fullTextAnnotation": {"text": "甲乙\n\n丙丁\n"}}]}
        with mock.patch.dict(os.environ, {"GOOGLE_VISION_API_KEY": "k"}), mock.patch.object(hannom_engines.httpx, "post", return_value=response):
            result = hannom_engines.run_google_vision(b"img", "p.jpg")
        self.assertEqual(result.lines, ["甲乙", "丙丁"])
        with mock.patch.dict(os.environ, {"GOOGLE_VISION_API_KEY": ""}):
            self.assertIsNone(hannom_engines.run_google_vision(b"img", "p.jpg"))
        with mock.patch.dict(os.environ, {"GOOGLE_VISION_API_KEY": "k"}), mock.patch.object(hannom_engines.httpx, "post", side_effect=RuntimeError("boom")):
            self.assertIsNone(hannom_engines.run_google_vision(b"img", "p.jpg"))


class PageEnginesEndpointTest(_PagesApi, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.patch.stop()
        self.storage = mock.Mock()
        self.storage.config.enabled = True
        self.storage.read_file_bytes.return_value = b"\xff\xd8\xffIMG"
        self.patch = mock.patch("app.documents.storage.ObjectStorage.from_env", return_value=self.storage)
        self.patch.start()
        pages = GiaPhaPageRepository(self.db)
        for p in pages.list_by_scan(self.scan.id):
            pages.set_image_key(p, f"gia-pha/{self.scan.id}/pages/{p.page_number:03d}.jpg")
        # Trang 1 của version gốc đã có kết quả paddle_v6.
        page1 = pages.list_by_scan(self.scan.id)[0]
        pages.upsert_content(
            version_id=self.version.id,
            page_id=page1.id,
            ocr_vote_meta={"vote_method": "x", "engines": {"paddle_v6": {"text": "甲", "score": None, "similarity_to_others": 0.5}}},
        )
        self.fake = mock.Mock(return_value=EngineResult(engine="gemini_vision", lines=["新", "字"]))
        self.reg = mock.patch.dict(hannom_engines.ENGINE_REGISTRY, {"gemini_vision": self.fake})
        self.reg.start()
        self.ready = mock.patch.object(pe, "readiness", return_value=(True, ""))
        self.ready.start()

    def tearDown(self) -> None:
        self.ready.stop()
        self.reg.stop()
        super().tearDown()

    def url(self, n: int = 1, tail: str = "engines") -> str:
        return f"/api/user/documents/{self.scan.id}/pages/{n}/{tail}"

    def test_lists_every_engine_with_presence_and_runnability(self) -> None:
        body = {e["name"]: e for e in self.client.get(self.url()).json()}
        self.assertEqual(list(body), ["kim_hannom_lab", "gemini", "google_vision", "paddle_v6", "deepseek"])
        self.assertTrue(body["paddle_v6"]["present"])
        self.assertFalse(body["gemini"]["present"])
        self.assertTrue(body["gemini"]["runnable"])
        self.assertFalse(body["paddle_v6"]["runnable"])  # chưa có adapter trên server
        self.assertFalse(body["deepseek"]["runnable"])
        self.assertTrue(body["gemini"]["paid"])

    def test_run_requires_confirmation_and_known_runnable_engine(self) -> None:
        post = lambda body: self.client.post(self.url(tail="ocr-engine"), json=body)  # noqa: E731
        self.assertEqual(post({"engine": "gemini"}).status_code, 400)  # chưa xác nhận tốn tiền
        self.assertEqual(post({"engine": "nope", "confirm_paid": True}).status_code, 400)
        self.assertEqual(post({"engine": "deepseek", "confirm_paid": True}).status_code, 409)  # chưa chạy được
        self.fake.assert_not_called()

    def test_run_adds_engine_to_forked_version_and_keeps_text_and_original(self) -> None:
        res = self.client.post(self.url(tail="ocr-engine"), json={"engine": "gemini", "confirm_paid": True})
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertTrue(body["forked"])
        self.assertEqual((body["engine"], body["text"]), ("gemini", "新\n字"))
        self.assertFalse(body["version"]["is_current"])
        pages = GiaPhaPageRepository(self.db)
        page1 = pages.list_by_scan(self.scan.id)[0]
        new = next(c for c in pages.list_content_for_version(body["version"]["version_id"]) if c.page_id == page1.id)
        self.assertEqual(set(new.ocr_vote_meta["engines"]), {"paddle_v6", "gemini"})
        self.assertEqual(new.hannom_text, "漢1")  # chữ chính không đổi
        old = next(c for c in pages.list_content_for_version(self.version.id) if c.page_id == page1.id)
        self.assertEqual(set(old.ocr_vote_meta["engines"]), {"paddle_v6"})  # bản gốc không đổi
        # Xem lại trên version sửa tay: engine vừa thêm hiện là "đã có".
        again = {e["name"]: e for e in self.client.get(self.url() + f"?version_id={body['version']['version_id']}").json()}
        self.assertTrue(again["gemini"]["present"])

    def test_engine_failure_creates_no_version(self) -> None:
        self.fake.return_value = None
        res = self.client.post(self.url(tail="ocr-engine"), json={"engine": "gemini", "confirm_paid": True})
        self.assertEqual(res.status_code, 502)
        self.assertEqual(len(GiaPhaVersionRepository(self.db).list_by_scan(self.scan.id)), 1)

    def test_not_ready_engine_is_refused_before_any_call(self) -> None:
        with mock.patch.object(pe, "readiness", return_value=(False, "Chưa có token")):
            res = self.client.post(self.url(tail="ocr-engine"), json={"engine": "gemini", "confirm_paid": True})
        self.assertEqual(res.status_code, 409)
        self.fake.assert_not_called()


if __name__ == "__main__":
    unittest.main()


BOX = {"bbox_xyxy": [1, 2, 30, 40], "han": "新", "confidence": 0.9, "order": 1}


class PageEngineBoxesTest(PageEnginesEndpointTest):
    """Engine có trả khung chữ (Kim Hán Nôm Lab) không được làm mất khung."""

    def setUp(self) -> None:
        super().setUp()
        self.kim = mock.Mock(return_value=EngineResult(engine="kimhannom", lines=["新", "字"], bbox=[BOX]))
        self.kim_reg = mock.patch.dict(hannom_engines.ENGINE_REGISTRY, {"kimhannom": self.kim})
        self.kim_reg.start()
        self.pages = GiaPhaPageRepository(self.db)

    def tearDown(self) -> None:
        self.kim_reg.stop()
        super().tearDown()

    def run_kim(self, n: int = 1, **extra):
        res = self.client.post(self.url(n, "ocr-engine"), json={"engine": "kim_hannom_lab", "confirm_paid": True, **extra})
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()

    def content(self, version_id: int, n: int):
        pid = self.pages.list_by_scan(self.scan.id)[n - 1].id
        return next(c for c in self.pages.list_content_for_version(version_id) if c.page_id == pid)

    def test_page_with_text_but_no_boxes_gets_boxes_and_keeps_text(self) -> None:
        body = self.run_kim(1)
        self.assertEqual((body["adopted_text"], body["box_count"]), (False, 1))
        new = self.content(body["version"]["version_id"], 1)
        self.assertEqual(new.ocr_bbox, [BOX])
        self.assertEqual(new.hannom_text, "漢1")  # chữ chính giữ nguyên
        self.assertIn("kim_hannom_lab", new.ocr_vote_meta["engines"])

    def test_image_only_page_adopts_text_and_boxes(self) -> None:
        # Giống sách mới chỉ nhập ảnh: trang chưa có chữ, chưa có khung.
        page = self.pages.list_by_scan(self.scan.id)[1]
        content = next(c for c in self.pages.list_content_for_version(self.version.id) if c.page_id == page.id)
        content.hannom_text = None
        self.db.add(content)
        self.db.commit()
        body = self.run_kim(2)
        self.assertEqual((body["adopted_text"], body["box_count"]), (True, 1))
        new = self.content(body["version"]["version_id"], 2)
        self.assertEqual((new.hannom_text, new.ocr_bbox), ("新\n字", [BOX]))

    def test_existing_boxes_are_not_replaced(self) -> None:
        first = self.run_kim(1)
        vid = first["version"]["version_id"]
        content = self.content(vid, 1)
        content.ocr_bbox = [{"bbox_xyxy": [9, 9, 9, 9], "han": "舊", "order": 1}]
        self.db.add(content)
        self.db.commit()
        again = self.run_kim(1, version_id=vid)
        self.assertEqual(again["box_count"], 0)
        self.assertEqual(self.content(vid, 1).ocr_bbox[0]["han"], "舊")  # khung cũ giữ nguyên

    def test_engine_without_boxes_leaves_boxes_untouched(self) -> None:
        body = self.client.post(self.url(1, "ocr-engine"), json={"engine": "gemini", "confirm_paid": True}).json()
        self.assertEqual((body["adopted_text"], body["box_count"]), (False, 0))
        self.assertIsNone(self.content(body["version"]["version_id"], 1).ocr_bbox)
