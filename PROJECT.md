# HCMUS Family Tree — Tài liệu dự án

> **Mô hình xây dựng tự động cây gia phả từ văn bản gia phả Hán-Nôm**

Hệ thống số hóa, quản lý và trực quan hóa gia phả dòng họ: tiếp nhận tư liệu gốc (ảnh scan, Word), OCR Hán-Nôm, trích xuất quan hệ, lưu trữ cây gia phả và chia sẻ công khai.

---

## Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Công nghệ](#2-công-nghệ)
3. [Kiến trúc hệ thống](#3-kiến-trúc-hệ-thống)
4. [Cấu trúc thư mục](#4-cấu-trúc-thư-mục)
5. [Chức năng chính](#5-chức-năng-chính)
6. [Định tuyến Frontend](#6-định-tuyến-frontend)
7. [API Backend](#7-api-backend)
8. [Cơ sở dữ liệu](#8-cơ-sở-dữ-liệu)
9. [Tích hợp bên ngoài](#9-tích-hợp-bên-ngoài)
10. [Phân quyền](#10-phân-quyền)
11. [Chạy dự án](#11-chạy-dự-án)
12. [Tài liệu liên quan](#12-tài-liệu-liên-quan)

> Chi tiết tính năng theo vai trò Guest / User / Admin: xem [FEATURES.md](./FEATURES.md)

---

## 1. Tổng quan

| Hạng mục | Mô tả |
|----------|--------|
| **Tên dự án** | HCMUS Family Tree / Gia Phả Việt |
| **Domain production** | [giapha.kimtudien.com.vn](https://giapha.kimtudien.com.vn) |
| **Đối tượng** | Gia phả Hán-Nôm, tư liệu scan, văn bản phiên âm |
| **Người dùng** | Công khai, User (đã đăng nhập), Admin |

### Luồng nghiệp vụ chính

```
Tư liệu gốc (ảnh / Word)
    → OCR Kim Hán Nôm (tuỳ chọn)
    → Phiên âm Quốc ngữ
    → Trích xuất thành viên & quan hệ (Gemini / NLP)
    → Lưu cây gia phả (BALKAN nodes)
    → Hiển thị sơ đồ tương tác + Kho tư liệu
```

---

## 2. Công nghệ

### Frontend — `family-saga-io/`

| Thành phần | Công nghệ |
|------------|-----------|
| Framework | React 18 + Vite |
| Ngôn ngữ | TypeScript |
| UI | Ant Design v6, Tailwind CSS, shadcn/ui |
| Routing | React Router v6 |
| State / API | TanStack Query, fetch API |
| Sơ đồ gia phả | Balkan FamilyTree.js |
| i18n | react-i18next (vi / en) |
| Theme | next-themes (light / dark) |

### Backend — `nlp_family_extractor/`

| Thành phần | Công nghệ |
|------------|-----------|
| Framework | FastAPI + Uvicorn |
| Ngôn ngữ | Python 3.10+ |
| ORM | SQLAlchemy |
| Auth | JWT (Bearer) |
| File storage | MinIO (S3-compatible) via boto3 |
| Gia phả store | MySQL + JSON mirror |
| OCR Hán-Nôm | Kim Hán Nôm API (fit.hcmus.edu.vn) |
| NLP / AI | Gemini (trích xuất quan hệ) |

### Hạ tầng

| Service | Công nghệ |
|---------|-----------|
| Reverse proxy | Nginx |
| Database | MySQL 8.4 |
| Object storage | MinIO |
| Container | Docker Compose |

---

## 3. Kiến trúc hệ thống

```
                    ┌─────────────┐
                    │   Browser   │
                    └──────┬──────┘
                           │ :87
                    ┌──────▼──────┐
                    │    Nginx    │
                    └──┬───────┬──┘
           /api/*     │       │  /*
              ┌───────▼──┐ ┌──▼────────┐
              │ Backend  │ │ Frontend  │
              │ FastAPI  │ │ React SPA │
              │  :8002   │ │   :5174   │
              └──┬───┬───┘ └───────────┘
                 │   │
        ┌────────┘   └────────┐
   ┌────▼────┐          ┌─────▼─────┐
   │  MySQL  │          │   MinIO   │
   │  :3309  │          │ :9002/9003│
   └─────────┘          └───────────┘
                              │
                    ┌─────────▼──────────┐
                    │ Kim Hán Nôm API    │
                    │ (OCR + phiên âm)   │
                    └────────────────────┘
```

---

## 4. Cấu trúc thư mục

```
family-tree/
├── family-saga-io/          # Frontend React (Vite)
│   ├── src/
│   │   ├── pages/           # Trang ứng dụng
│   │   ├── layouts/         # Public / User / Admin layout
│   │   ├── components/      # UI components
│   │   ├── lib/             # API client, utils, theme
│   │   ├── i18n/            # Bản dịch vi / en
│   │   └── config/          # Routes, developer config
│   └── Dockerfile
│
├── nlp_family_extractor/    # Backend FastAPI
│   ├── api.py               # Entry point, routes chính
│   ├── app/
│   │   ├── auth/            # JWT, users, roles
│   │   ├── documents/       # MinIO, CRUD tài liệu
│   │   ├── hannom/          # OCR & phiên âm Kim Hán Nôm
│   │   └── family_tree_store.py  # CRUD cây gia phả
│   ├── data/                # JSON gia phả, vietnamgiapha crawl
│   └── tools/               # Script crawl / sync DB
│
├── nginx/                   # Reverse proxy config
├── scripts/                 # Build Docker scripts
├── docker-compose.yml
├── readme.md                # Hướng dẫn build & deploy
├── business.md              # Phân tích nghiệp vụ đề tài
└── PROJECT.md               # Tài liệu dự án (file này)
```

---

## 5. Chức năng chính

### 5.1. Trang công khai

- Landing page giới thiệu dự án
- Hướng dẫn sử dụng
- Đăng nhập / Đăng ký
- Xem gia phả công khai: `/gia-pha/:treeId`

### 5.2. Khu vực User

- Bảng điều khiển
- **Phòng đọc tư liệu**: upload Word / ảnh scan, phân tích cây gia phả
- **Xem gia phả**: sơ đồ trực quan Balkan, chi tiết thành viên

### 5.3. Khu vực Admin

- **Quản lý gia phả** (`/admin/gia-pha`):
  - Danh sách cây: mô tả, đường link, tài liệu gốc, văn bản Hán-Nôm, thành viên
  - Chi tiết cây: sơ đồ, hồ sơ thành viên, kho tư liệu, quản lý quan hệ
  - Crawl + đồng bộ từ vietnamgiapha.com
- **Quản lý tài liệu**: upload MinIO, OCR Hán-Nôm, lưu kết quả phiên âm
- **Quản lý người dùng**: phân role user / admin
- **Developer**: cấu hình Kim Hán Nôm, storage, logs, API docs

---

## 6. Định tuyến Frontend

### Public

| Route | Trang | Mô tả |
|-------|-------|--------|
| `/` | HomePage | Trang chủ |
| `/huong-dan` | GuidePage | Hướng dẫn |
| `/gia-pha/:treeId` | PublicFamilyTreePage | Xem gia phả công khai |
| `/login` | LoginPage | Đăng nhập |
| `/register` | RegisterPage | Đăng ký |

### User (yêu cầu đăng nhập)

| Route | Trang |
|-------|-------|
| `/user/dashboard` | DashboardPage |
| `/user/document-reader` | DocumentReaderPage |
| `/user/family-tree` | FamilyTreePage |

### Admin (yêu cầu role admin)

| Route | Trang |
|-------|-------|
| `/admin/gia-pha` | FamilyTreeManagerPage — Danh sách |
| `/admin/gia-pha/:treeId` | FamilyTreeDetailPage — Chi tiết |
| `/admin/documents/:documentId/edit` | EditDocumentPage — Sửa tài liệu + OCR |
| `/admin/users` | AdminUsersPage |
| `/admin/developer/hannom-config` | HannomConfigPage |
| `/admin/developer/storage` | StoragePage |
| `/admin/developer/logs` | LogsPage |
| `/admin/developer/docs` | DocsPage |

---

## 7. API Backend

Base URL: `http://localhost:8002` (dev) hoặc `/api` qua Nginx (production).

### Auth

| Method | Route | Mô tả |
|--------|-------|--------|
| POST | `/api/register` | Đăng ký |
| POST | `/api/login` | Đăng nhập → JWT |
| GET | `/api/me` | Thông tin user hiện tại |

### Gia phả (Admin)

| Method | Route | Mô tả |
|--------|-------|--------|
| GET | `/api/family-trees` | Danh sách cây |
| POST | `/api/family-trees` | Tạo cây mới |
| GET | `/api/family-trees/{id}` | Chi tiết cây + nodes |
| PUT | `/api/family-trees/{id}` | Cập nhật metadata |
| DELETE | `/api/family-trees/{id}` | Xóa cây |
| POST | `/api/family-trees/{id}/nodes` | Thêm thành viên |
| PUT | `/api/family-trees/{id}/nodes/{nodeId}` | Sửa thành viên |
| POST | `/api/family-trees/{id}/links` | Tạo quan hệ |
| POST | `/api/vietnamgiapha/crawl-sync` | Crawl + sync DB |

### Tài liệu (Admin)

| Method | Route | Mô tả |
|--------|-------|--------|
| GET | `/api/family-trees/{id}/documents` | Danh sách tài liệu |
| POST | `/api/family-trees/{id}/documents` | Tạo tài liệu |
| PUT | `/api/documents/{id}` | Cập nhật tài liệu |
| POST | `/api/documents/{id}/upload-files` | Upload file lên MinIO |
| POST | `/api/documents/{id}/ocr-transliterate` | OCR + phiên âm + lưu `.txt` |

### Phân tích (User)

| Method | Route | Mô tả |
|--------|-------|--------|
| POST | `/api/family-tree/analyze` | Phân tích văn bản → cây gia phả |
| GET | `/api/family-tree/history` | Lịch sử truy vấn |

### Developer (Admin)

| Method | Route | Mô tả |
|--------|-------|--------|
| POST | `/api/developer/hannom/fetch-token` | Lấy token Kim Hán Nôm |
| GET | `/health` | Health check |

> Chi tiết API Documents và OCR: xem [readme.md](./readme.md).

---

## 8. Cơ sở dữ liệu

### Bảng `family_tree`

| Cột | Kiểu | Mô tả |
|-----|------|--------|
| `id` | VARCHAR(64) PK | Mã cây (vd. `vpg-101`, `tree-abc123`) |
| `name` | VARCHAR(255) | Tên dòng họ |
| `description` | TEXT | Mô tả / lịch sử |
| `nodes_json` | JSON | Danh sách node BALKAN |
| `node_count` | INT | Số thành viên |
| `external_url` | VARCHAR(512) | Đường link nguồn (vd. vietnamgiapha.com) |
| `has_source_document` | TINYINT(1) | Có tài liệu gốc |
| `has_hannom_text` | TINYINT(1) | Có văn bản Hán-Nôm |
| `created_at` / `updated_at` | VARCHAR(64) | ISO timestamp |

### Bảng tài liệu (`source_documents`, `document_files`)

- Liên kết `family_tree_id`
- Loại: `han_nom`, `van_ban`, `hinh_anh`, `ket_qua_van_ban`, `ket_qua_hinh_anh`
- File lưu trên MinIO, metadata trong MySQL

### Bảng users

- Email, password hash, role (`user` / `admin`)

---

## 9. Tích hợp bên ngoài

### Kim Hán Nôm API

- **URL**: https://kimhannom.fit.hcmus.edu.vn
- **Pipeline**: upload ảnh → OCR → phiên âm Quốc ngữ
- **Cấu hình**: `HANNOM_API_TOKEN`, `HANNOM_EMAIL`, `HANNOM_PASSWORD`
- **UI cấu hình**: Admin → Developer → Hán-Nôm Config

### VietnamGiaPha

- Crawl dữ liệu từ vietnamgiapha.com
- Sync vào bảng `family_tree` (ID dạng `vpg-*`)
- Tự sinh `external_url`: `https://vietnamgiapha.com/{id}`

### MinIO

- Bucket: `family-tree-docs`
- Presigned URL cho download
- Console: http://localhost:9003

---

## 10. Phân quyền

| Role | Quyền |
|------|--------|
| **Public** | Xem trang chủ, hướng dẫn, gia phả công khai |
| **user** | Dashboard, đọc tư liệu, xem gia phả mẫu |
| **admin** | Toàn bộ CRUD gia phả, tài liệu, users, developer tools |

JWT gửi qua header: `Authorization: Bearer <token>`

---

## 11. Chạy dự án

### Yêu cầu

- Docker 24+ & Docker Compose v2 (production)
- Node.js 20+ (dev frontend)
- Python 3.10+ (dev backend)

### Production (Docker)

```bash
docker compose up -d --build
```

| Service | URL |
|---------|-----|
| Nginx (chính) | http://localhost:87 |
| Frontend trực tiếp | http://localhost:5174 |
| Backend API | http://localhost:8002 |
| MinIO Console | http://localhost:9003 |

### Development (local)

```bash
# Frontend
cd family-saga-io && npm install && npm run dev

# Backend
cd nlp_family_extractor
pip install -r requirements.txt
uvicorn api:app --reload --port 8002
```

### Build nhanh

```bash
./scripts/build-all.sh --up
```

> Hướng dẫn deploy chi tiết, biến môi trường, troubleshooting: [readme.md](./readme.md)

---

## 12. Tài liệu liên quan

| File | Nội dung |
|------|----------|
| [FEATURES.md](./FEATURES.md) | Tính năng theo vai trò Guest / User / Admin, ma trận spec vs hiện trạng |
| [readme.md](./readme.md) | Build, deploy, Docker, MinIO, OCR env vars |
| [business.md](./business.md) | Phân tích nghiệp vụ & kiến trúc đề tài |
| [nlp_family_extractor/readme.md](./nlp_family_extractor/readme.md) | Backend chi tiết |
| Admin → Developer → Docs | CURL mẫu, schema JSON API |

---

## Liên hệ & bản quyền

© 2026 HCMUS Family Tree — Gìn giữ truyền thống, kết nối thế hệ.

*Cập nhật lần cuối: 07/2026*
