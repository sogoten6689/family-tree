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

