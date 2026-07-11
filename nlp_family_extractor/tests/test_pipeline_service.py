from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.documents.models import DocumentType
from app.pipeline.service import PipelineService, _enum_value


class PipelineServiceHelpersTest(unittest.TestCase):
    def test_enum_value_from_enum(self) -> None:
        self.assertEqual(_enum_value(DocumentType.VAN_BAN), "van_ban")

    def test_enum_value_from_string(self) -> None:
        self.assertEqual(_enum_value("van_ban"), "van_ban")

    @patch("app.pipeline.service.ObjectStorage")
    def test_artifact_from_document_handles_string_type(self, storage_cls: MagicMock) -> None:
        storage_cls.from_env.return_value.config.enabled = False

        document = MagicMock()
        document.id = 9
        document.title = "Test doc"
        document.type = "van_ban"
        document.files = []

        db = MagicMock()
        db.get.return_value = document

        service = PipelineService(db, get_tree=lambda _tree_id: {"nodes": []})
        artifact = service._artifact_from_document(9)

        self.assertEqual(artifact.kind, "document")
        self.assertEqual(artifact.type, "van_ban")


if __name__ == "__main__":
    unittest.main()
