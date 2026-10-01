import unittest

from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.auth.models import User, UserRole
from app.database import Base
from app.workspace.models import UserScan
from app.workspace.repository import UserScanRepository


@compiles(LONGTEXT, "sqlite")
def _longtext_as_sqlite_text(_type, _compiler, **_kw) -> str:
    # Model dùng LONGTEXT (MySQL) — SQLite in-memory chỉ cần TEXT.
    return "TEXT"


class UserScanAccessTest(unittest.TestCase):
    """`get_accessible`: Admin mở được bản ghi của user khác (khớp phạm vi
    `GET /api/gia-pha` của Admin), User thường thì không."""

    def setUp(self) -> None:
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine, tables=[User.__table__, UserScan.__table__])
        self.db = Session(engine)
        self.owner = User(email="owner@test.local", full_name="Owner", password_hash="x", role=UserRole.USER)
        self.other = User(email="other@test.local", full_name="Other", password_hash="x", role=UserRole.USER)
        self.admin = User(email="admin@test.local", full_name="Admin", password_hash="x", role=UserRole.ADMIN)
        self.db.add_all([self.owner, self.other, self.admin])
        self.db.commit()
        self.repo = UserScanRepository(self.db)
        self.scan = self.repo.create(
            user_id=self.owner.id, title="Gia phả họ Phan", file_name="a.pdf", file_type="pdf"
        )

    def tearDown(self) -> None:
        self.db.close()

    def test_owner_can_open_own_scan(self) -> None:
        self.assertEqual(self.repo.get_accessible(self.owner, self.scan.id).id, self.scan.id)

    def test_admin_can_open_other_users_scan(self) -> None:
        self.assertEqual(self.repo.get_accessible(self.admin, self.scan.id).id, self.scan.id)

    def test_other_user_cannot_open_scan(self) -> None:
        self.assertIsNone(self.repo.get_accessible(self.other, self.scan.id))

    def test_missing_scan_returns_none_for_admin(self) -> None:
        self.assertIsNone(self.repo.get_accessible(self.admin, self.scan.id + 999))


if __name__ == "__main__":
    unittest.main()
