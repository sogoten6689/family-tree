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
| nginx    | **88**    | 80            | Reverse proxy chính |
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

## Production (Docker Compose)

### Build & chạy toàn bộ stack

```bash
docker compose -p family-tree up -d --build
```

### Chỉ rebuild một service

```bash
# Rebuild frontend
docker compose -p family-tree up -d --build frontend

# Rebuild backend
docker compose -p family-tree up -d --build backend
```

### Xem trạng thái containers

```bash
docker compose -p family-tree ps -a
```

### Xem logs

```bash
# Toàn bộ
docker compose -p family-tree logs -f

# Riêng từng service
docker compose -p family-tree logs -f backend
docker compose -p family-tree logs -f frontend
docker compose -p family-tree logs -f nginx
```

### Dừng stack

```bash
docker compose -p family-tree down
```

### Dừng và xoá volume (reset DB)

```bash
docker compose -p family-tree down -v
```

---

## Nginx Reverse Proxy

Config: `nginx/conf.d/giapha.kimtudien.com.vn.conf`

| Pattern URL | Route đến |
|-------------|-----------|
| `/api/*`, `/docs`, `/redoc`, `/health` | `backend:8000` |
| `/` (mọi route còn lại) | `frontend:80` (SPA) |

Domain: **giapha.kimtudien.com.vn** → port `88`

---

## Kiểm tra nhanh sau deploy

```bash
# Health check backend
curl http://localhost:8002/health

# Qua nginx
curl http://giapha.kimtudien.com.vn/health
```

