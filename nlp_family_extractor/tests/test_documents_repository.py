import unittest

from app.documents.repository import DocumentRepository, DocumentValidationError


class DocumentReorderValidationTest(unittest.TestCase):
    def test_reorder_requires_all_files(self) -> None:
        class FakeSession:
            pass

        repo = DocumentRepository(FakeSession())  # type: ignore[arg-type]

        class FakeDocument:
            files = [type("F", (), {"id": 1, "position": 0})()]

        repo.get = lambda document_id: FakeDocument()  # type: ignore[method-assign]

        with self.assertRaises(DocumentValidationError):
            repo.reorder_files(1, [(999, 0)])


if __name__ == "__main__":
    unittest.main()
