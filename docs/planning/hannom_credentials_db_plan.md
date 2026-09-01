# Kim Hán Nôm — lưu credential DB & auto re-login

> **Ngày:** 2026-07-25  
> **Trạng thái:** Đã triển khai backend MVP  
> **Mục tiêu:** Lưu `username`, `password`, `token` trên MySQL (mã hóa), tự refresh khi JWT hết hạn hoặc API trả 401.

---

## 1. Vấn đề hiện tại

| Cách cũ | Hạn chế |
|---------|---------|
| `HANNOM_API_TOKEN` trong `.env` | Mất khi redeploy; phải sửa tay |
| Fetch token qua UI | Chỉ **runtime** — restart container mất token |
| Không biết `exp` | OCR fail giữa chừng khi token hết hạn |

---

## 2. Thiết kế

### 2.1. Bảng `hannom_credential` (singleton — 1 dòng)

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `id` | int PK | Luôn `1` |
| `username` | varchar(255) | Email / user Kim Hán Nôm |
| `password_enc` | text | Fernet encrypt |
| `token_enc` | text nullable | JWT encrypt |
| `token_expires_at` | datetime nullable | Parse từ JWT `exp` |
| `token_source` | varchar(64) | `cookie:token`, `json_body`, … |
| `last_login_at` | datetime nullable | |
| `last_error` | text nullable | Lỗi login/refresh gần nhất |
| `updated_at` | datetime | |

### 2.2. Mã hóa at-rest

- Key: `HANNOM_SECRETS_KEY` hoặc fallback `JWT_SECRET_KEY` → SHA-256 → Fernet key
- **Không** lưu password/token plain text trong DB
- API **không** trả password; token chỉ preview `abc12345...wxyz`

### 2.3. Thứ tự ưu tiên token (runtime)

```text
1. HANNOM_API_TOKEN (env) — override dev / khẩn cấp
2. DB: token còn hạn (exp - 5 phút buffer)
3. DB: re-login bằng username + password_enc → lưu token mới
4. Runtime cache (fetch-token trong phiên)
5. Lỗi → HannomApiError
```

### 2.4. Auto re-login

| Trigger | Hành động |
|---------|-----------|
| `token_expires_at` < now + 5m | Login lại trước khi gọi OCR |
| Kim Hán Nôm HTTP **401** | `force_refresh()` → retry request **1 lần** |
| Admin PUT credentials | Login validate → lưu token |

Lock `threading.Lock` — tránh nhiều OCR song song login cùng lúc.

---

## 3. API (Admin JWT)

| Method | Route | Mô tả |
|--------|-------|--------|
| GET | `/api/developer/hannom/credentials` | Trạng thái (không lộ password) |
| PUT | `/api/developer/hannom/credentials` | Lưu username/password → login → lưu token |
| POST | `/api/developer/hannom/fetch-token` | Login (form) + **lưu DB** nếu có password |
| GET | `/api/developer/hannom/token-status` | Mở rộng: `source=db`, `expires_at` |

---

## 4. Luồng VPS production

```bash
# 1. Deploy stack (MySQL bật)
docker compose up -d --build backend

# 2. Admin UI → Developer → Hán-Nôm → Lưu tài khoản lên server
#    hoặc:
curl -X PUT https://giapha.../api/developer/hannom/credentials \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{"username":"email@...","password":"..."}'

# 3. Không cần HANNOM_API_TOKEN trong .env (tuỳ chọn override)
curl .../api/developer/hannom/token-status
```

---

## 5. Bảo mật & rủi ro

| Rủi ro | Giảm thiểu |
|--------|------------|
| Password trong DB | Fernet + key từ env server |
| Admin JWT lộ → đọc metadata | Chỉ admin route; không trả password |
| Key rotation | Đổi `HANNOM_SECRETS_KEY` → re-save credentials |
| Kim Hán Nôm đổi login flow | Giữ module `auth.py` tách biệt |

**Lưu ý luận văn / compliance:** lưu mật khẩu dịch vụ bên thứ ba — chỉ dùng server tin cậy; ghi trong tài liệu vận hành.

---

## 6. File code

| File | Vai trò |
|------|---------|
| `app/hannom/models.py` | SQLAlchemy model |
| `app/hannom/credential_store.py` | Encrypt, get/refresh token |
| `app/hannom/jwt_utils.py` | Parse JWT `exp` |
| `app/hannom/bootstrap.py` | `create_all` |
| `app/hannom/router.py` | API credentials |
| `app/hannom/client.py` | Dùng store + retry 401 |
| `tests/test_hannom_credentials.py` | Unit tests |

---

## 7. Acceptance criteria

- [ ] PUT credentials → OCR batch chạy sau `docker compose restart backend`
- [ ] Token hết hạn → auto re-login không cần admin thao tác
- [ ] `token-status` hiển thị `source=db` và `expires_at`
- [ ] Env `HANNOM_API_TOKEN` vẫn override được (backward compat)
