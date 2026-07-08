# HCMUS Family Tree — Tài liệu tính năng theo vai trò

> Phân tích quyền truy cập và chức năng theo ba nhóm: **Guest**, **User**, **Admin**.  
> Mỗi mục ghi rõ **yêu cầu nghiệp vụ**, **trạng thái triển khai**, **route / file / API** tương ứng.

**Chú thích trạng thái**

| Ký hiệu | Ý nghĩa |
|---------|---------|
| ✅ | Đã triển khai, dùng được |
| ⚠️ | Triển khai một phần / cần bổ sung |
| ❌ | Chưa có hoặc chưa đúng spec |

---

## Mục lục

1. [Tổng quan phân quyền](#1-tổng-quan-phân-quyền)
2. [Guest — Khách truy cập](#2-guest--khách-truy-cập)
3. [User — Người dùng đã đăng nhập](#3-user--người-dùng-đã-đăng-nhập)
4. [Admin — Quản trị hệ thống](#4-admin--quản-trị-hệ-thống)
5. [Ma trận so sánh spec vs hiện trạng](#5-ma-trận-so-sánh-spec-vs-hiện-trạng)
6. [Hướng phát triển đề xuất](#6-hướng-phát-triển-đề-xuất)

---

## 1. Tổng quan phân quyền

```
┌─────────────────────────────────────────────────────────────────┐
│                         GUEST (công khai)                        │
│  Trang chủ · Đăng nhập · Đăng ký · Hướng dẫn                    │
│  Xem gia phả mẫu (công khai) · Xem tài liệu Hán-Nôm mẫu         │
└───────────────────────────────┬─────────────────────────────────┘
                                │ đăng nhập
┌───────────────────────────────▼─────────────────────────────────┐
│                         USER (đã đăng nhập)                      │
│  Dashboard · Upload/scan · OCR/AI · Tạo gia phả                 │
│  Danh sách tài liệu · Danh sách gia phả · Lịch sử · Hồ sơ       │
└───────────────────────────────┬─────────────────────────────────┘
                                │ role = admin
┌───────────────────────────────▼─────────────────────────────────┐
│                         ADMIN (quản trị)                         │
│  Quản lý toàn bộ gia phả · tài liệu · user · lịch sử · cấu hình │
└─────────────────────────────────────────────────────────────────┘
```

| Vai trò | Mục tiêu | Guard frontend | Backend |
|---------|----------|----------------|---------|
| **Guest** | Giới thiệu hệ thống, đăng ký, xem nội dung mẫu công khai | Không yêu cầu JWT | Một số API công khai |
| **User** | Tạo gia phả cá nhân, scan tài liệu, quản lý dữ liệu của mình | `ProtectedRoute` | JWT + role `user` |
| **Admin** | Quản lý toàn hệ thống, cấu hình, crawl dữ liệu | `AdminRoute` | JWT + role `admin` |

---

## 2. Guest — Khách truy cập

**Mục tiêu:** Cho phép người dùng chưa đăng nhập xem thông tin giới thiệu và đăng ký tài khoản.

### 2.1. Quyền truy cập theo spec

| # | Tính năng | Trạng thái | Route | File triển khai |
|---|-----------|------------|-------|-----------------|
| 1 | Trang chủ | ✅ | `/` | `family-saga-io/src/pages/HomePage.tsx` |
| 2 | Đăng nhập | ✅ | `/login` | `family-saga-io/src/pages/LoginPage.tsx` |
| 3 | Đăng ký | ✅ | `/register` | `family-saga-io/src/pages/RegisterPage.tsx` |
| 4 | Hướng dẫn sử dụng | ✅ | `/huong-dan` | `family-saga-io/src/pages/GuidePage.tsx` |
| 5 | Xem gia phả mẫu — **danh sách** (công khai) | ✅ | `/gia-pha` | `PublicFamilyTreeListPage.tsx` |
| 6 | Xem gia phả mẫu — **chi tiết** (công khai) | ✅ | `/gia-pha/:treeId` | `PublicFamilyTreePage.tsx` |
| 7 | Xem tài liệu Hán-Nôm mẫu (theo gia phả, công khai) | ✅ | Tab trên chi tiết | `GET /api/public/family-trees/{id}/documents` |

### 2.2. Chi tiết từng tính năng

#### Trang chủ ✅

- Hero giới thiệu dự án, thống kê, tính năng nổi bật
- Navigation: Hướng dẫn, Tính năng, Về chúng tôi
- CTA Đăng nhập / Đăng ký
- Layout: `PublicLayout.tsx` (header responsive, drawer mobile)

#### Đăng nhập / Đăng ký ✅

| Thao tác | API |
|----------|-----|
| Đăng ký | `POST /api/register` |
| Đăng nhập | `POST /api/login` → JWT lưu `localStorage` |
| Phiên hiện tại | `GET /api/me` (sau khi đăng nhập) |

Sau đăng nhập: user → `/user/dashboard`, admin → có thêm shortcut khu vực quản trị.

#### Hướng dẫn sử dụng ✅

- Danh mục trang và mô tả chức năng
- Cấu hình trang: `family-saga-io/src/config/pages.ts`

#### Xem gia phả mẫu (công khai) ⚠️

**Yêu cầu spec:**
- Danh sách các cây gia phả được đánh dấu công khai
- Chi tiết: sơ đồ, hồ sơ thành viên, thống kê (thành viên, thế hệ)

**Hiện trạng:**

| Thành phần | Ghi chú |
|------------|---------|
| Route chi tiết | `/gia-pha/:treeId` — `PublicFamilyTreePage.tsx` |
| Tabs chi tiết | Sơ đồ (Balkan), Hồ sơ thành viên, sidebar tổ tiên |
| Route danh sách | **Chưa có** — khách không duyệt được gallery gia phả mẫu |
| API | `GET /api/family-trees/{id}` yêu cầu **admin JWT** → khách truy cập trực tiếp sẽ lỗi 401/403 |
| Cờ `is_public` | **Chưa có** trong DB — chưa phân biệt cây công khai / riêng tư |

**Khoảng trống cần bổ sung:**
1. Cột `is_public` (hoặc tương đương) trên bảng `family_tree`
2. API `GET /api/public/family-trees` (danh sách) và `GET /api/public/family-trees/{id}` (chi tiết, không cần admin)
3. Trang frontend danh sách gia phả mẫu + liên kết từ trang chủ

#### Xem tài liệu Hán-Nôm mẫu (công khai) ❌

**Yêu cầu spec:**
- Xem tài liệu gốc / phiên âm thuộc gia phả công khai
- Đi theo luồng: gia phả mẫu → kho tư liệu → xem tài liệu

**Hiện trạng:**
- Toàn bộ API tài liệu (`/api/family-trees/{id}/documents`, `/api/documents/{id}`) yêu cầu admin
- Tab **Kho tư liệu** chỉ có trên trang admin chi tiết (`FamilyTreeDetailPage.tsx`)
- Không có trang public xem tài liệu

---

## 3. User — Người dùng đã đăng nhập

**Mục tiêu:** Cho phép người dùng tạo gia phả, scan dữ liệu và quản lý tài liệu.

**Guard:** `ProtectedRoute` — yêu cầu JWT hợp lệ.  
**Layout:** `UserLayout.tsx` — sidebar: Dashboard, Phòng đọc tài liệu, Xem gia phả.

### 3.1. Quyền truy cập theo spec

| # | Tính năng | Trạng thái | Route | File triển khai |
|---|-----------|------------|-------|-----------------|
| 1 | Dashboard (tổng tài liệu scan, số cây gia phả) | ✅ | `/user/dashboard` | `DashboardPage.tsx` + `GET /api/user/stats` |
| 2 | Tạo gia phả: upload, scan, lịch sử upload | ⚠️ | `/user/document-reader` | Lưu scan server; OCR user chưa có |
| 3 | Chỉnh sửa nội dung sau OCR/AI | ⚠️ | `/user/family-tree` | Client-side; chưa edit server |
| 4 | Tạo cây gia phả từ dữ liệu đã xử lý | ✅ | Document reader modal | `POST /api/user/family-trees` |
| 5 | Danh sách tài liệu đã scan (bảng đầy đủ cột) | ✅ | `/user/documents` | `UserDocumentsPage.tsx` |
| 6 | Chi tiết tài liệu đã scan | ✅ | `/user/documents/:scanId` | `UserDocumentDetailPage.tsx` |
| 7 | Danh sách gia phả đã tạo (bảng đầy đủ cột) | ✅ | `/user/family-trees` | `UserFamilyTreesPage.tsx` |
| 8 | Lịch sử truy vấn | ✅ | `/user/document-reader` | Scoped theo `user_id` khi đăng nhập |
| 9 | Quản lý thông tin tài khoản | ✅ | `/user/profile` | `PATCH /api/me` |

### 3.2. Dashboard ⚠️

**Yêu cầu spec:**
- Thẻ thống kê: **tổng tài liệu đã scan**, **số cây gia phả đã tạo**
- Điều hướng nhanh tới các module

**Hiện trạng:**
- Chào user + hiển thị role
- 3 card điều hướng: Phòng đọc tài liệu, Xem gia phả, Hướng dẫn
- Admin thấy thêm shortcut sang khu vực quản trị
- **Chưa có** API thống kê theo `user_id`

### 3.3. Tạo gia phả — Upload & Scan ⚠️

**Yêu cầu spec:**
- Upload tài liệu (ảnh scan, Word, text)
- Scan / phân tích nội dung
- Lịch sử upload

**Hiện trạng — Phòng đọc tài liệu** (`DocumentReaderPage.tsx`):

| Chức năng | Chi tiết |
|-----------|----------|
| Upload file | Drag & drop; hỗ trợ `.docx`, `.txt`, `.doc`, ảnh |
| Preview | Ảnh: viewer; Word: mammoth → text |
| Phân tích | `POST /api/family-tree/analyze` → trích xuất thành viên & quan hệ (Gemini/NLP) |
| Kết quả | Lưu tạm `localStorage`, chuyển sang `/user/family-tree` |
| OCR Hán-Nôm | **Chưa có** cho user — OCR chỉ trong khu admin |
| Lưu server | **Chưa có** — file không upload MinIO, không gắn `user_id` |

**Luồng hiện tại:**

```
Upload file (local)
    → Preview
    → POST /api/family-tree/analyze
    → localStorage (nodes)
    → /user/family-tree (xem sơ đồ)
```

**Luồng mục tiêu (spec):**

```
Upload file
    → Lưu MinIO + metadata (user_id)
    → OCR (tuỳ chọn)
    → Chỉnh sửa nội dung
    → Tạo / cập nhật cây gia phả (persist DB)
```

### 3.4. Chỉnh sửa sau OCR/AI ⚠️

**Hiện trạng** (`FamilyTreePage.tsx`):
- Sửa thông tin thành viên trên client (modal edit)
- Export Excel (chế độ non-Balkan)
- Dữ liệu từ phân tích gần nhất hoặc **mock data** (`familyMockData.ts`)
- **Không** lưu thay đổi lên server

### 3.5. Tạo cây gia phả từ dữ liệu đã xử lý ⚠️

- Có thể **xem** cây từ kết quả phân tích (BalkanFamilyTreeView)
- **Chưa** gọi `POST /api/family-trees` để lưu cây thuộc user
- **Chưa** liên kết cây với tài liệu nguồn trên server

### 3.6. Danh sách tài liệu đã scan ❌

**Yêu cầu spec — bảng cột:**

| STT | Tên tài liệu | Loại file | Số trang | Ngày upload | Trạng thái OCR | Trạng thái gia phả | Thao tác |
|-----|--------------|-----------|----------|-------------|----------------|-------------------|----------|

**Hiện trạng:** Chưa có trang `/user/documents` hay bảng tương đương.  
Lịch sử truy vấn trong Phòng đọc chỉ hiển thị **request phân tích** (request_id, ngày, số người/quan hệ), không phải bảng tài liệu đầy đủ.

### 3.7. Chi tiết tài liệu đã scan ❌

**Yêu cầu spec:** Từ danh sách → xem preview, nội dung OCR, trạng thái, liên kết gia phả.

**Hiện trạng:** Chỉ có preview inline trong Phòng đọc khi vừa upload; không có trang chi tiết persistent.

### 3.8. Danh sách gia phả đã tạo ❌

**Yêu cầu spec — bảng cột:**

| STT | Tên gia phả | Tài liệu nguồn | Số thành viên | Số thế hệ | Ngày tạo | Ngày cập nhật | Thao tác |
|-----|-------------|----------------|---------------|-----------|----------|---------------|----------|

**Hiện trạng:**
- `/user/family-tree` hiển thị **một** cây (mock hoặc kết quả phân tích gần nhất)
- `GET /api/family-trees` chỉ dành cho admin
- **Chưa** có bảng danh sách gia phả của user

### 3.9. Lịch sử truy vấn ✅

**Vị trí:** Panel bên Phòng đọc tài liệu (`DocumentReaderPage.tsx`)

| Thao tác | API |
|----------|-----|
| Xem danh sách | `GET /api/family-tree/history?limit=10` |
| Xem chi tiết | `GET /api/family-tree/history/{request_id}` |
| Xóa toàn bộ | `DELETE /api/family-tree/history` |

**Lưu ý:** Lịch sử hiện **global** (không gắn `user_id` trên backend) — cần bổ sung khi triển khai multi-user thực sự.

### 3.10. Quản lý tài khoản cá nhân ❌

**Yêu cầu spec:** Đổi họ tên, email, mật khẩu; xem thông tin đăng ký.

**Hiện trạng:**
- `GET /api/me` trả thông tin user (dùng trong `AuthContext`)
- Sidebar hiển thị tên — **không** có trang `/user/profile` hay form chỉnh sửa

---

## 4. Admin — Quản trị hệ thống

**Mục tiêu:** Quản lý toàn bộ dữ liệu, người dùng và cấu hình hệ thống.

**Guard:** `AdminRoute` — JWT + `role === "admin"`.  
**Layout:** `AdminLayout.tsx`

### 4.1. Quyền truy cập theo spec

| # | Tính năng | Trạng thái | Route | File triển khai |
|---|-----------|------------|-------|-----------------|
| 1 | Dashboard quản trị | ✅ | `/admin/dashboard` | `AdminDashboardPage.tsx` |
| 2 | Quản lý gia phả (danh sách, chi tiết, từng loại dữ liệu) | ✅ | `/admin/gia-pha`, `/admin/gia-pha/:treeId` | Manager + Detail pages |
| 3 | Quản lý tài liệu Hán-Nôm (danh sách, chi tiết theo gia phả) | ✅ | Tab Kho tư liệu + `/admin/documents/:documentId/edit` | `FamilyTreeDocumentsPanel`, `EditDocumentPage` |
| 4 | Quản lý user hệ thống | ✅ | `/admin/users` | `AdminUsersPage.tsx` |
| 5 | Quản lý lịch sử scan và truy vấn | ✅ | `/admin/history` | `AdminHistoryPage.tsx` |
| 6 | Cấu hình hệ thống (crawl, OCR, lưu trữ) | ✅ | `/admin/developer/*` | Hannom, Storage, Docs pages |

### 4.2. Dashboard quản trị ⚠️

**Yêu cầu spec:** Tổng quan hệ thống — số cây, tài liệu, user, hoạt động gần đây.

**Hiện trạng:**
- Vào `/admin` redirect sang **Quản lý gia phả**
- Stat card **Tổng số cây gia phả** trên trang danh sách
- **Chưa có** dashboard tổng hợp riêng

### 4.3. Quản lý gia phả ✅

#### Danh sách — `/admin/gia-pha`

**File:** `FamilyTreeManagerPage.tsx`

| Cột (hiện tại) | Mô tả |
|----------------|--------|
| Gia phả | Tên + ID |
| Mô tả | Ellipsis |
| Đường link | `external_url` hoặc link vietnamgiapha |
| Tài liệu gốc | Checkbox `has_source_document` |
| Văn bản Hán-Nôm | Checkbox `has_hannom_text` |
| Thành viên | `node_count` |
| Cập nhật | `updated_at` |
| Thao tác | Chi tiết, Sửa, Tải tài liệu, Crawl+Sync (dropdown) |

**API:**

| Method | Endpoint |
|--------|----------|
| GET | `/api/family-trees` |
| POST | `/api/family-trees` |
| PUT | `/api/family-trees/{id}` |
| DELETE | `/api/family-trees/{id}` |
| POST | `/api/vietnamgiapha/crawl-sync` |

#### Chi tiết — `/admin/gia-pha/:treeId`

**File:** `FamilyTreeDetailPage.tsx`

| Tab | Nội dung |
|-----|----------|
| Sơ đồ Gia phả | BalkanFamilyTreeView tương tác |
| Hồ sơ Thành viên | `FamilyTreeMembersTable` |
| Kho Tư liệu Hán-Nôm & Văn bản | `FamilyTreeDocumentsPanel` |
| Quản lý quan hệ | Thêm/sửa/xóa node & link |

**Sidebar:** `FamilyTreeAncestralSidebar` — thông tin tổ tiên, thống kê.

**Thống kê hero:** Số thành viên, tài liệu, thế hệ.

**API bổ sung:**

| Method | Endpoint |
|--------|----------|
| GET | `/api/family-trees/{id}` |
| POST/PUT/DELETE | `/api/family-trees/{id}/nodes[/{nodeId}]` |
| POST/DELETE | `/api/family-trees/{id}/links` |
| PUT | `/api/family-trees/{id}/document` (JSON editor) |

### 4.4. Quản lý tài liệu Hán-Nôm ✅

#### Danh sách theo gia phả

**File:** `FamilyTreeDocumentsPanel.tsx` (tab trên trang chi tiết)

| Cột | Mô tả |
|-----|--------|
| Tiêu đề | Tên + mô tả ngắn |
| Loại | `han_nom`, `van_ban`, `hinh_anh`, `ket_qua_*` |
| Files | Số file đính kèm |
| Thao tác | Sửa |

#### Chi tiết & OCR — `/admin/documents/:documentId/edit`

**File:** `EditDocumentPage.tsx`, `EditDocumentForm.tsx`, `DocumentOcrPanel.tsx`

| Chức năng | API |
|-----------|-----|
| Xem / sửa metadata | `GET/PUT /api/documents/{id}` |
| Upload file | `POST /api/documents/{id}/upload-files` |
| Sắp xếp file | `PUT /api/documents/{id}/reorder-files` |
| Xóa file | `DELETE /api/documents/{id}/files/{fileId}` |
| OCR + phiên âm | `POST /api/documents/{id}/ocr-transliterate` |

**OCR pipeline:** Kim Hán Nôm API → lưu file `.txt` kết quả trên MinIO.

### 4.5. Quản lý user ✅

**File:** `AdminUsersPage.tsx` — `/admin/users`

| Cột | Mô tả |
|-----|--------|
| ID | User ID |
| Họ và tên | `full_name` |
| Email | `email` |
| Role | Select `user` / `admin` |
| Ngày tạo | `created_at` |
| Thao tác | Xóa |

| Method | Endpoint |
|--------|----------|
| GET | `/api/users` |
| PATCH | `/api/users/{id}/role` |
| DELETE | `/api/users/{id}` |

### 4.6. Lịch sử scan & truy vấn ⚠️

**Yêu cầu spec:** Admin xem toàn bộ lịch sử phân tích / scan của mọi user.

**Hiện trạng:**

| Thành phần | Ghi chú |
|------------|---------|
| API history | `GET /api/family-tree/history` — tồn tại, **không** yêu cầu admin, **không** gắn user |
| UI admin | `LogsPage.tsx` — log OCR debug **lưu local browser**, không phải lịch sử server |
| **Thiếu** | Trang admin quản lý lịch sử scan/truy vấn tập trung |

### 4.7. Cấu hình hệ thống ✅

| Module | Route | File | Chức năng |
|--------|-------|------|-----------|
| Cấu hình OCR Hán-Nôm | `/admin/developer/hannom-config` | `HannomConfigPage.tsx` | Token Kim Hán Nôm, trạng thái kết nối |
| Lưu trữ (MinIO) | `/admin/developer/storage` | `StoragePage.tsx` | Health, bucket info |
| Logs API | `/admin/developer/logs` | `LogsPage.tsx` | Log debug OCR (local) |
| Tài liệu API | `/admin/developer/docs` | `DocsPage.tsx` | CURL mẫu, schema |
| Crawl dữ liệu | Modal trên Manager | `FamilyTreeManagerPage.tsx` | `POST /api/vietnamgiapha/crawl-sync` |

---

## 5. Ma trận so sánh spec vs hiện trạng

### Guest

| Tính năng | Spec | Hiện trạng |
|-----------|------|------------|
| Trang chủ | ✓ | ✅ |
| Đăng nhập | ✓ | ✅ |
| Đăng ký | ✓ | ✅ |
| Hướng dẫn | ✓ | ✅ |
| Gia phả mẫu — danh sách | ✓ | ❌ |
| Gia phả mẫu — chi tiết | ✓ | ⚠️ (route có, API chặn guest) |
| Tài liệu Hán-Nôm mẫu | ✓ | ❌ |

### User

| Tính năng | Spec | Hiện trạng |
|-----------|------|------------|
| Dashboard thống kê | ✓ | ⚠️ (chỉ điều hướng) |
| Upload + scan | ✓ | ⚠️ (local, chưa lưu server) |
| Chỉnh sửa sau OCR/AI | ✓ | ⚠️ (client-only) |
| Tạo cây từ dữ liệu xử lý | ✓ | ⚠️ (xem được, chưa persist) |
| Bảng tài liệu đã scan | ✓ | ❌ |
| Chi tiết tài liệu | ✓ | ❌ |
| Bảng gia phả đã tạo | ✓ | ❌ |
| Lịch sử truy vấn | ✓ | ✅ |
| Quản lý tài khoản | ✓ | ❌ |

### Admin

| Tính năng | Spec | Hiện trạng |
|-----------|------|------------|
| Dashboard quản trị | ✓ | ⚠️ |
| Quản lý gia phả | ✓ | ✅ |
| Quản lý tài liệu Hán-Nôm | ✓ | ✅ |
| Quản lý user | ✓ | ✅ |
| Lịch sử scan/truy vấn | ✓ | ⚠️ |
| Cấu hình hệ thống | ✓ | ✅ |

### Tổng kết nhanh

| Vai trò | ✅ Hoàn thành | ⚠️ Một phần | ❌ Chưa có |
|---------|--------------|-------------|------------|
| **Guest** | 7 | 0 | 0 |
| **User** | 6 | 3 | 0 |
| **Admin** | 6 | 0 | 0 |

---

## 6. Hướng phát triển đề xuất

Ưu tiên theo phụ thuộc kỹ thuật:

### Giai đoạn 1 — Guest công khai

1. Thêm `is_public` vào `family_tree`
2. API public: `GET /api/public/family-trees`, `GET /api/public/family-trees/{id}`
3. Trang `/gia-pha` (danh sách) + sửa `PublicFamilyTreePage` dùng API public
4. API public tài liệu (chỉ cây `is_public = 1`)

### Giai đoạn 2 — User workspace

1. Gắn `user_id` cho tài liệu và cây gia phả
2. Upload user → MinIO (`POST /api/user/documents`)
3. Trang `/user/documents` — bảng đủ cột spec
4. Trang `/user/family-trees` — bảng đủ cột spec
5. Dashboard stats: `GET /api/user/stats`
6. Trang `/user/profile` — sửa thông tin cá nhân

### Giai đoạn 3 — Admin bổ sung

1. `/admin/dashboard` — tổng quan hệ thống
2. `/admin/history` — lịch sử scan/truy vấn toàn hệ thống
3. Scope lịch sử analyze theo `user_id`

### Ghi chú kiến trúc

Hiện tại hệ thống có **hai luồng song song**:

```
ADMIN ZONE                          USER ZONE
────────────                        ─────────
MySQL family_tree                   localStorage
MinIO documents                     File upload local
OCR server-side                     POST /analyze only
CRUD đầy đủ                         Xem mock / kết quả tạm
```

Mục tiêu dài hạn là **hợp nhất**: user tạo dữ liệu qua cùng pipeline lưu trữ (MinIO + MySQL), admin quản lý toàn bộ; guest chỉ xem subset được đánh dấu công khai.

---

## Tài liệu liên quan

| File | Nội dung |
|------|----------|
| [PROJECT.md](./PROJECT.md) | Tổng quan dự án, kiến trúc, API, DB |
| [readme.md](./readme.md) | Build, deploy, Docker |
| [business.md](./business.md) | Phân tích nghiệp vụ đề tài |

*Cập nhật lần cuối: 07/2026*
