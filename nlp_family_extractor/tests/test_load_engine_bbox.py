import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from app.workspace.repository import GiaPhaPageRepository, GiaPhaVersionRepository
from tests.test_corpus_identifiers import RECORD, _Db, import_corpus

_TOOLS = Path(__file__).resolve().parents[1] / "tools"
_spec = importlib.util.spec_from_file_location("load_engine_bbox", _TOOLS / "load_engine_bbox.py")
load_engine_bbox = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(load_engine_bbox)

ENGINE = "kim_hannom_lab"
KIM = [{"order": 1, "bbox_xyxy": [10, 20, 60, 400], "han": "乾坤", "confidence": 0.9}]
PADDLE = [{"order": 1, "bbox_xyxy": [900, 10, 960, 800], "han": "乾坤", "confidence": 0.98}]
OTHER = [{"order": 1, "bbox_xyxy": [1, 2, 3, 4], "han": "x", "confidence": 0.5}]


class LoadEngineBboxTest(_Db, unittest.TestCase):
    def _setup(self):
        scan = self.new_scan()
        pages_repo, versions_repo = GiaPhaPageRepository(self.db), GiaPhaVersionRepository(self.db)
        import_corpus.backfill_structure(
            scan=scan, record=RECORD, scans=self.scans, pages_repo=pages_repo, versions_repo=versions_repo,
            owner_id=self.owner.id, dry_run=False,
        )
        v1 = versions_repo.get_current(scan.id)
        v2 = versions_repo.clone_version(v1.id, created_by=self.owner.id)
        self.scan, self.pages_repo, self.versions_repo, self.versions = scan, pages_repo, versions_repo, [v1, v2]
        self.page1, self.page2 = pages_repo.list_by_scan(scan.id)[:2]

    def _apply(self, write, pages=None, engine=ENGINE):
        pages = pages if pages is not None else {"1": {"boxes": KIM}, "9": {"boxes": KIM}}
        return load_engine_bbox.apply_book_engine_bbox(
            scan_id=self.scan.id, engine=engine, pages=pages,
            pages_repo=self.pages_repo, versions_repo=self.versions_repo, write=write,
        )

    def _content(self, version, page):
        return next(c for c in self.pages_repo.list_content_for_version(version.id) if c.page_id == page.id)

    def test_dry_run_writes_nothing(self) -> None:
        self._setup()
        self.assertEqual(self._apply(write=False), {"pages": 1, "rows_changed": 2, "missing_pages": 1})
        self.db.commit()
        for v in self.versions:
            self.assertIsNone(self._content(v, self.page1).ocr_bbox_engines)

    def test_writes_under_engine_key_in_every_version_and_is_idempotent(self) -> None:
        self._setup()
        self.assertEqual(self._apply(write=True), {"pages": 1, "rows_changed": 2, "missing_pages": 1})
        for v in self.versions:
            c = self._content(v, self.page1)
            self.assertEqual(c.ocr_bbox_engines, {ENGINE: KIM})
            self.assertEqual(c.hannom_text, "乾坤")  # chữ không đổi
            self.assertIsNone(self._content(v, self.page2).ocr_bbox_engines)  # trang không có khung
        self.assertEqual(len(self.versions_repo.list_by_scan(self.scan.id)), 2)  # không tạo version mới
        self.assertEqual(self._apply(write=True)["rows_changed"], 0)

    def test_keeps_existing_ocr_bbox_and_other_engines(self) -> None:
        self._setup()
        for v in self.versions:
            self.pages_repo.upsert_content(
                version_id=v.id, page_id=self.page1.id, ocr_bbox=PADDLE, ocr_bbox_engine=("other_engine", OTHER)
            )
        self._apply(write=True)
        for v in self.versions:
            c = self._content(v, self.page1)
            self.assertEqual(c.ocr_bbox, PADDLE)
            self.assertEqual(c.ocr_bbox_engines, {"other_engine": OTHER, ENGINE: KIM})

    def test_rerun_with_changed_boxes_updates_only_that_engine(self) -> None:
        self._setup()
        self._apply(write=True)
        new = [{**KIM[0], "bbox_xyxy": [11, 21, 61, 401]}]
        self.assertEqual(self._apply(write=True, pages={"1": {"boxes": new}})["rows_changed"], 2)
        self.assertEqual(self._content(self.versions[0], self.page1).ocr_bbox_engines, {ENGINE: new})

    def test_skips_pages_without_boxes(self) -> None:
        self._setup()
        stats = self._apply(write=True, pages={"1": {"boxes": []}, "2": {}})
        self.assertEqual((stats["pages"], stats["rows_changed"]), (0, 0))
        for v in self.versions:
            self.assertIsNone(self._content(v, self.page1).ocr_bbox_engines)
            self.assertIsNone(self._content(v, self.page2).ocr_bbox_engines)


class ExportEngineBboxTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        scripts = Path(__file__).resolve().parents[2] / "research" / "hannom-bilingual-dataset" / "scripts"
        try:
            spec = importlib.util.spec_from_file_location("export_engine_bbox", scripts / "export_engine_bbox.py")
            cls.exporter = importlib.util.module_from_spec(spec)
            import sys

            sys.path.insert(0, str(scripts))
            spec.loader.exec_module(cls.exporter)
        except Exception as exc:  # thiếu phụ thuộc của research/ (vd. rapidfuzz) → bỏ qua
            raise unittest.SkipTest(f"không nạp được export_engine_bbox: {exc}")

    def _quad(self, x0, y0, x1, y1):
        return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

    def test_maps_page_number_by_record_order_reads_right_to_left_and_skips_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pages_dir = Path(tmp)
            result = [
                [self._quad(10, 10, 40, 300), ["左", 0.8]],
                [self._quad(100, 10, 130, 300), ["右", 0.95]],
            ]
            (pages_dir / "007-boundingbox.json").write_text(json.dumps({"result_bbox": result}), encoding="utf-8")
            (pages_dir / "008-boundingbox.json").write_text(json.dumps({"result_bbox": []}), encoding="utf-8")
            record = {"pages": [{"l0_image": "a/009.jpg"}, {"l0_image": "a/007.jpg"}, {"l0_image": "a/008.jpg"}]}
            pages, warnings, stats = self.exporter.export_book(record, pages_dir)
        self.assertEqual(list(pages), ["2"])  # trang thứ 2 trong record (stem 007)
        self.assertEqual([b["han"] for b in pages["2"]["boxes"]], ["右", "左"])
        self.assertEqual(pages["2"]["boxes"][0]["bbox_xyxy"], [100, 10, 130, 300])
        self.assertEqual((stats["no_file"], stats["no_boxes"], stats["boxes"]), (1, 1, 2))
        self.assertEqual(len(warnings), 1)  # không có ảnh để kiểm cỡ


if __name__ == "__main__":
    unittest.main()
