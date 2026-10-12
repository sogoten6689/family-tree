import unittest

from app.auth.models import User
from tests.test_page_images import _PagesApi


class DocumentNeighborsTest(_PagesApi, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.first = self.scan  # từ fixture _Pages
        self.second = self.new_scan()
        self.third = self.new_scan()

    def get(self, scan_id: int):
        return self.client.get(f"/api/user/documents/{scan_id}/neighbors")

    def test_middle_has_both_neighbors_with_position(self) -> None:
        body = self.get(self.second.id).json()
        self.assertEqual((body["prev"]["id"], body["next"]["id"]), (self.first.id, self.third.id))
        self.assertEqual((body["position"], body["total"]), (2, 3))
        self.assertEqual(body["prev"]["title"], "GP")

    def test_ends_have_a_single_neighbor(self) -> None:
        first = self.get(self.first.id).json()
        self.assertIsNone(first["prev"])
        self.assertEqual(first["next"]["id"], self.second.id)
        last = self.get(self.third.id).json()
        self.assertIsNone(last["next"])
        self.assertEqual(last["prev"]["id"], self.second.id)

    def test_soft_deleted_documents_are_skipped(self) -> None:
        self.scans.soft_delete(self.second, user_id=self.owner.id)
        body = self.get(self.first.id).json()
        self.assertEqual(body["next"]["id"], self.third.id)
        self.assertEqual(body["total"], 2)

    def test_normal_user_only_navigates_their_own_documents(self) -> None:
        other = self.db.query(User).filter_by(email="o@x.l").one()
        mine = self.scans.create(user_id=other.id, title="Của tôi", file_name="x", file_type="hannom-corpus")
        mine2 = self.scans.create(user_id=other.id, title="Của tôi 2", file_name="x", file_type="hannom-corpus")
        self.user = other
        body = self.get(mine.id).json()
        self.assertIsNone(body["prev"])  # bộ của admin không lộ
        self.assertEqual(body["next"]["id"], mine2.id)
        self.assertEqual(body["total"], 2)
        self.assertEqual(self.get(self.first.id).status_code, 404)

    def test_unknown_document_is_404(self) -> None:
        self.assertEqual(self.get(99999).status_code, 404)


if __name__ == "__main__":
    unittest.main()
