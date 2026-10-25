# Harness tích hợp (API qua HTTP thật)

Code: `nlp_family_extractor/tests/integration/` · chạy: `scripts/harness.sh`.

| Tầng | Lệnh | Cần | Phủ |
|------|------|-----|-----|
| Không DB | `scripts/harness.sh` | Python deps | khởi động uvicorn thật; `/health`, `/openapi.json`, `/docs`, CORS, từ chối ẩn danh, `/api/genealogy/extract` |
| Có MySQL | `scripts/harness.sh db` | Docker daemon | MySQL **tạm** (container `harness-mysql`, cổng 3319, không volume, không đụng `family-tree-mysql`); thêm: đăng nhập admin, CRUD cây/nút/liên kết, export, xoá |

Nhắm vào stack đã chạy: `HARNESS_API_URL=http://host:port scripts/harness.sh`.
Tầng không DB cũng nằm trong lệnh pytest của CI (~7 giây); test `requires_db` tự skip khi không có DB.

## Đã kiểm chứng (25/10/2026)
- Tầng không DB: 8 pass, 2 skip. Tầng `db`: 10 pass; container tạm được xoá sau khi chạy.
- Harness hộp đen theo nhân vật (repo riêng `family-tree-harness`) chạy trên cùng API: 42 test pass với MySQL.

## Phát hiện từ harness
- Không có MySQL, `GET /api/family-trees` từng trả **500** (do `get_db()` ném `RuntimeError`). Đã sửa 25/10/2026: `get_db()` ném `DatabaseUnavailable` (lớp con `RuntimeError`) và `api.py` trả 503. Test: `tests/test_database_unavailable.py`.
