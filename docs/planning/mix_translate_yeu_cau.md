# Yêu cầu thông tin — chạy pipeline Hương (OCR → âm → nghĩa → cây)

> Điền **vào** `nlp_family_extractor/.env` (không paste key vào file markdown này).  
> Plan: [mix_translate_family_tree_plan.md](./mix_translate_family_tree_plan.md)  
> Probe máy: 2026-08-31 — lab L2 **OK**; Qwen **thiếu**; Gemini **401**; Docker **tắt**.

---

## Cách dùng

1. Tick mục đã có.  
2. Mục **bắt buộc còn thiếu** → lấy key rồi thêm vào `.env`.  
3. Không commit `.env`. Không sửa Word / ảnh gốc Hương.

Mẫu biến: `nlp_family_extractor/.env.example`.

---

## A. Bắt buộc để chạy P0 (p.0 + p.2 → âm + nghĩa)

### A1. Kim Hán Nôm — dịch âm (L2)

| Biến | Cần? | Trạng thái máy | Ghi vào `.env` |
|------|------|----------------|----------------|
| `HANNOM_EMAIL` | Có | Đã có, login OK | (giữ) |
| `HANNOM_PASSWORD` | Có | Đã có, login OK | (giữ) |
| `HANNOM_API_BASE_URL` | Có | Đã có | `https://kimhannom.fit.hcmus.edu.vn` |
| `HANNOM_FONT_TYPE` | Nên | Chưa ghi — default `1` vẫn phiên âm được | `1` |
| `HANNOM_TRANSLITERATION_LANG_TYPE` | Nên | Chưa ghi — default `1` OK | `1` |

**Không cần** cho L2: `HANNOM_OCR_ID`. File lab sẵn dùng `ocr_id=1`; `.env` đang `3` — **đừng OCR lại**.

- [x] A1 đủ để chạy phiên âm

### A2. Dịch nghĩa (L3) — **còn thiếu** (chọn một)

Họp 24/08: nghĩa = **Qwen**. Gemini chỉ dự phòng nếu Qwen chưa có.

**Phương án 1 — Qwen (ưu tiên)**

| Biến | Ví dụ | Lấy ở đâu |
|------|--------|-----------|
| `DASHSCOPE_API_KEY` | `sk-…` | [Alibaba Model Studio](https://modelstudio.console.alibabacloud.com) (Singapore / intl) |
| `QWEN_BASE_URL` | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | Cùng console, compatible-mode |
| `QWEN_MODEL` | `qwen3.6-27b` | Bản T đã thử (không phải 37B) |

- [ ] Đã tạo key DashScope và ghi 3 dòng trên vào `.env`

**Phương án 2 — Gemini (cây `analyze` cũng cần)**

| Biến | Ghi chú |
|------|---------|
| `GOOGLE_API_KEY` | Key **Google AI Studio** (thường `AIza…`). Key hiện tại **401** — cần key mới |
| `GEMINI_MODEL_NAME` | Optional; mặc định `models/gemini-2.5-flash` |

- [ ] Đã thay `GOOGLE_API_KEY` mới và ping không còn 401

**P0 L3 không chạy** nếu cả hai phương án đều trống/hỏng.

---

## B. Mở cây trên admin (DOM) — **KHÔNG CẦN, đã quyết định bỏ (2026-08-31)**

Quyết định: không dùng Docker/MySQL/admin cho pipeline này. Xem trực tiếp cây bằng
`tools/render_family_tree.py` (đọc `nodes.json` → HTML tĩnh, mở bằng trình duyệt local,
không backend, không Docker). Chi tiết renderer: [mix_translate_family_tree_plan.md §Renderer](./mix_translate_family_tree_plan.md).

Giữ bảng dưới lại chỉ để tham khảo — **không cần làm** trừ khi sau này muốn triển khai app thật:

| Biến / việc | Mặc định compose | Trạng thái |
|-------------|------------------|------------|
| Bật Docker Desktop | — | **Tắt** (2026-08-31) — không cần bật |
| `MYSQL_HOST` | `localhost` | Chưa có trong `.env` extractor — không cần |
| `MYSQL_PORT` | `3309` (host → 3306 container) | Chưa có — không cần |
| `MYSQL_DATABASE` | `family_tree` | Chưa có — không cần |
| `MYSQL_USER` / `MYSQL_PASSWORD` | xem `infra/.env.production.example` / compose | Chưa có — không cần |
| API extractor + FE | `infra/scripts/compose.sh` / dev local | Chưa chạy — không cần |

- [x] Quyết định: dùng renderer HTML tĩnh thay admin — không cần Docker/MySQL cho P0

---

## C. Không phải key — nhưng cần có trước khi chạy lệnh

| Việc | Ai làm | Ghi chú |
|------|--------|---------|
| Thư mục `data/01_interim/huong_nguyen_ke/{mix,l2,l3}/` | Script / tay | **Chưa tạo** |
| CLI mix 2 OCR **hoặc** dùng lab `result_ocr_text` làm L1* | Dev | Chưa có `tools/mix*.py` |
| `--out` L2/L3 → `01_interim` | Dev | **Cấm** ghi `dich/` trong thư mục Hương |
| Catalog `nguyen-ke-han-nom` | Đã có | 15 trang Paddle + lab |

- [ ] Đã có thư mục `01_interim` (không đụng `.docx` / `pages/*.jpg`)

---

## D. Block copy vào `.env` (điền giá trị, không commit)

Chỉ copy các dòng **còn thiếu**. Đừng xoá `HANNOM_*` đang chạy.

```text
# --- L3 Qwen (bắt buộc nếu không dùng Gemini) ---
DASHSCOPE_API_KEY=
QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen3.6-27b

# --- Gemini (cây analyze + L3 dự phòng); thay key nếu 401 ---
# GOOGLE_API_KEY=
# GEMINI_MODEL_NAME=models/gemini-2.5-flash

# --- Admin / MySQL (chỉ khi mở DOM) ---
MYSQL_HOST=localhost
MYSQL_PORT=3309
MYSQL_DATABASE=family_tree
MYSQL_USER=family_user
MYSQL_PASSWORD=family_password

# --- L2 lab (optional, khớp default) ---
HANNOM_FONT_TYPE=1
HANNOM_TRANSLITERATION_LANG_TYPE=1
```

---

## E. Bạn gửi lại gì (nếu nhờ chạy hộ)

Không gửi mật khẩu lab / key vào chat nếu không cần. Đủ xác nhận:

| Câu | Trả lời |
|-----|---------|
| Đã dán `DASHSCOPE_API_KEY` vào `.env`? | Có / Không |
| Đã thay `GOOGLE_API_KEY` (hết 401)? | Có / Không / Bỏ Gemini |
| Cần mở cây admin tuần này? | Có (sẽ bật Docker) / Không (chỉ file JSON) |
| P0 chỉ p.0 + p.2? | Có (mặc định) / Không, liệt kê trang |

---

## F. Đã đủ / chưa (tóm tắt — cập nhật 2026-08-31)

| Mục tiêu | Trạng thái |
|----------|--------|
| Chỉ **dịch âm** 2 tờ | ✅ Không thiếu key |
| **Dịch nghĩa** Qwen | ✅ `DASHSCOPE_API_KEY` đã có, đã test HTTP 200 |
| **Cây** qua API analyze | ✅ `GOOGLE_API_KEY` mới đã có, đã test hoạt động |
| **Sơ đồ tự nhiên** từ JSON, 1 file/gia đình | Renderer đã viết & test (`tools/render_family_tree.py`) — chỉ còn thiếu `nodes.json` thật (chờ mix→L2→L3→analyze) |
| Sơ đồ trên web admin | Không cần — đã bỏ (mục B) |
