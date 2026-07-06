# Family Tree — Hướng dẫn Build & Deploy

## Yêu cầu

| Công cụ | Phiên bản tối thiểu |
|---------|-------------------|
| Docker  | 24+               |
| Docker Compose | v2+        |
| Node.js | 20+ (chỉ cần khi dev local) |

---

## Cấu trúc cổng

| Service  | Host port | Container port | Ghi chú |
|----------|-----------|---------------|---------|
| nginx    | **87**    | 80            | Reverse proxy chính |
| frontend | 5174      | 80            | Direct (bypass nginx) |
| backend  | **8002**  | 8000          | FastAPI / uvicorn |
| mysql    | 3309      | 3306          | MySQL 8.4 |
| minio    | **9002**  | 9000          | S3 API (file storage) |
| minio UI | **9003**  | 9001          | MinIO Console |

---

## MinIO / Documents (tài liệu gia phả)

Backend lưu file tài liệu trên MinIO (tương thích S3) qua `boto3`.

| Biến môi trường | Mô tả |
|-----------------|--------|
| `MINIO_ENDPOINT` | URL nội bộ, vd. `http://minio:9000` (Docker) |
| `MINIO_PUBLIC_ENDPOINT` | URL public cho presigned URL, vd. `http://localhost:9002` |
| `MINIO_ACCESS_KEY` | Access key |
| `MINIO_SECRET_KEY` | Secret key |
| `MINIO_BUCKET` | Tên bucket, vd. `family-tree-docs` |
| `MINIO_USE_SSL` | `true` / `false` |
| `MINIO_AUTO_CREATE_BUCKET` | Tự tạo bucket nếu chưa có (`true` mặc định) |
| `MINIO_PRESIGN_EXPIRES` | Thời hạn presigned URL (giây), mặc định `3600` |
| `MINIO_MAX_UPLOAD_BYTES` | Giới hạn upload (bytes), mặc định `52428800` (50MB) |

### API Documents (Admin JWT)

| Method | Route | Mô tả |
|--------|-------|--------|
| GET | `/api/family-trees/{id}/documents` | Danh sách tài liệu + files (sắp xếp theo `position`) |
| POST | `/api/family-trees/{id}/documents` | Tạo tài liệu mới |
| PUT | `/api/documents/{id}` | Cập nhật title/description/type |
| DELETE | `/api/documents/{id}/files/{file_id}` | Xóa file (DB + MinIO) |
| POST | `/api/documents/{id}/upload-files` | Upload nhiều file (`multipart/form-data`, field `files`) |
| PUT | `/api/documents/{id}/reorder-files` | Cập nhật thứ tự file |

| POST | `/api/documents/{id}/ocr-transliterate` | OCR Hán-Nôm + phiên âm Quốc ngữ (Kim Hán Nôm API), lưu `.txt` vào tài liệu `ket_qua_van_ban` |

Loại tài liệu (`type`): `han_nom`, `van_ban`, `hinh_anh`, `ket_qua_van_ban`, `ket_qua_hinh_anh`.

### Kim Hán Nôm OCR / Phiên âm

Tích hợp API [Kim Hán Nôm](https://kimhannom.fit.hcmus.edu.vn) qua module `app/hannom/`.

| Biến môi trường | Mô tả |
|-----------------|--------|
| `HANNOM_API_TOKEN` | **Bắt buộc** (hoặc lấy runtime). Bearer token OCR |
| `HANNOM_EMAIL` / `HANNOM_PASSWORD` | Tài khoản Kim Hán Nôm (dùng cho fetch-token server-side) |
| `POST /api/developer/hannom/fetch-token` | Admin: đăng nhập & lấy token tự động |
| `HANNOM_API_BASE_URL` | Mặc định `https://kimhannom.fit.hcmus.edu.vn` |
| `HANNOM_RATE_LIMIT_PER_MINUTE` | Giới hạn request (mặc định `40`/phút) |
| `HANNOM_OCR_ID` | `1` = dọc thông thường |
| `HANNOM_OCR_LANG_TYPE` | `0` chưa biết, `1` Hán, `2` Nôm |
| `HANNOM_FONT_TYPE` / `HANNOM_TRANSLITERATION_LANG_TYPE` | Tham số phiên âm |

Pipeline: upload ảnh → OCR → sinonom-transliteration → lưu file `.txt` vào document `ket_qua_van_ban` liên kết (`source_document_id=<id>`).

MinIO Console: http://localhost:9003 (user/pass: `minioadmin` / `minioadmin123` khi chạy docker-compose mặc định).

---

## Biến môi trường Frontend

File | Mục đích
-----|--------
`family-saga-io/.env` | Dev local (`VITE_BACKEND_URL=http://localhost:8002`)
`family-saga-io/.env.production` | Production Docker (để trống — nginx proxy xử lý `/api`)

> **Lưu ý:** Vite yêu cầu prefix `VITE_` để expose biến ra client-side code.

---

## Development (local)

```bash
# 1. Cài dependencies
cd family-saga-io
npm install

# 2. Chạy frontend dev server (port 8080)
npm run dev
```

Backend chạy riêng (nếu cần):
```bash
cd nlp_family_extractor
pip install -r requirements.txt
uvicorn api:app --reload --port 8002
```

---

## Build scripts (khuyến nghị)

Các script trong thư mục `scripts/` giúp build Docker image nhanh, tự dùng `DOCKER_BUILDKIT=0` để tránh lỗi `buildx permission denied` trên một số máy macOS.

| Script | Mô tả |
|--------|--------|
| `scripts/build-backend.sh` | Build image backend (`nlp_family_extractor`) |
| `scripts/build-frontend.sh` | Build image frontend (`family-saga-io`) |
| `scripts/build-all.sh` | Build cả backend và frontend |

Chạy từ thư mục gốc repo:

```bash
# Chỉ build image
./scripts/build-backend.sh
./scripts/build-frontend.sh

# Build xong và restart container tương ứng
./scripts/build-backend.sh --up
./scripts/build-frontend.sh --up

# Build cả hai + restart backend & frontend
./scripts/build-all.sh --up
```

Xem thêm tùy chọn:

```bash
./scripts/build-backend.sh --help
./scripts/build-frontend.sh --help
./scripts/build-all.sh --help
```

Nếu Docker báo lỗi quyền, thử chạy với `sudo`:

```bash
sudo ./scripts/build-frontend.sh --up
```

> **Lưu ý:** Flag `--up` (hoặc `-u`) sẽ chạy `docker compose up -d --force-recreate` cho service tương ứng sau khi build xong.

---

## Production (Docker Compose)

### Build & chạy toàn bộ stack

```bash
docker compose up -d --build
```

### Chỉ rebuild một service

**Cách 1 — dùng script (khuyến nghị):**

```bash
./scripts/build-backend.sh --up
./scripts/build-frontend.sh --up
```

**Cách 2 — docker compose trực tiếp:**

```bash
# Rebuild frontend
docker compose up -d --build frontend

# Rebuild backend
docker compose up -d --build backend
```

Nếu gặp lỗi buildx, thêm biến môi trường:

```bash
DOCKER_BUILDKIT=0 docker compose build frontend
DOCKER_BUILDKIT=0 docker compose up -d --force-recreate frontend
```

### Xem trạng thái containers

```bash
docker compose ps -a
```

### Xem logs

```bash
# Toàn bộ
docker compose logs -f

# Riêng từng service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f nginx
```

### Dừng stack

```bash
docker compose down
```

### Dừng và xoá volume (reset DB)

```bash
docker compose down -v
```

---

## Nginx Reverse Proxy

Config: `nginx/conf.d/giapha.kimtudien.com.vn.conf`

| Pattern URL | Route đến |
|-------------|-----------|
| `/api/*`, `/docs`, `/redoc`, `/health` | `backend:8000` |
| `/` (mọi route còn lại) | `frontend:80` (SPA) |

Domain: **giapha.kimtudien.com.vn** → port `87`

---

## Kiểm tra nhanh sau deploy

```bash
# Health check backend
curl http://localhost:8002/health

# Frontend (direct)
open http://localhost:5174

# Admin quản lý gia phả
open http://localhost:5174/admin/gia-pha

# Qua nginx
curl http://localhost:87/health
```

