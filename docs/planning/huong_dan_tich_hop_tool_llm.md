# Hướng dẫn tích hợp tool LLM (ChatGPT / Gemini) vào web

Dành cho: Lâm tự làm sau. Viết 02/10/2026, khớp code tại commit `2e0f159`.

Web đã có sẵn **khe cắm engine phiên âm + dịch nghĩa**. Việc cần làm chỉ là viết **1 file adapter**
gọi tool của bạn (`research/hannom-bilingual-dataset/TOOL_ChatGPT_API`, `TOOL_Gemini_API`) và trả
kết quả đúng định dạng. Toàn bộ phần còn lại (hàng đợi chạy nền, kiểm tra, tạo version, giao diện,
xuất dữ liệu train) đã làm xong.

> Có 2 đường đưa kết quả LLM vào web — chọn 1 hoặc dùng cả 2:
>
> | | A. Engine chạy trên server (tài liệu này) | B. Nhập file kết quả |
> |---|---|---|
> | Tool chạy ở đâu | Trong container backend | Trên máy bạn |
> | Cần sửa server | Có (Chrome, cookie) | Không |
> | Dùng khi | Muốn bấm "Chạy" ngay trên web | Đã có sẵn file `{page, cn, sv, vi}` |
>
> Đường B: tab **"Phiên bản & nhập LLM"** → **Nhập kết quả LLM** (định dạng ở §7).

---

## 1. Hợp đồng của 1 engine

```python
def engine(hannom_text: str, *, page_number: int) -> list[dict]:
    ...
    return [{"cn": "乾坤天意愛維新", "sv": "Càn khôn thiên ý ái duy tân", "vi": "…"}, …]
```

| Quy tắc | Chi tiết |
|---|---|
| Input | Văn bản Hán Nôm (OCR đã vote) của **1 trang** + số trang |
| Output | `list` các câu, mỗi câu có đủ `cn` (chữ Hán), `sv` (phiên âm), `vi` (dịch nghĩa), đều khác rỗng |
| Trường `page` | **Không cần** — runner tự gắn |
| Câu có `[Chú giải]` | Tự bị bỏ qua |
| Thiếu/rỗng 1 trường, hoặc trả về không phải `list` | **Cả lần chạy bị đánh lỗi**, version giữ nguyên nội dung cũ |
| Exception | Lần chạy bị đánh lỗi, thông báo hiện ở cột **Chạy** (rê chuột vào "Lỗi") |
| Thời gian | Tối đa **600 giây / trang** (`text_engine_runner.DEFAULT_PAGE_TIMEOUT_SECONDS`) |
| Tên engine | Chữ thường/số/`-`/`_`, ≤ 50 ký tự (vd `gemini-web`, `chatgpt-web`) |

Kết quả mỗi lần chạy = **1 version mới** (không đổi version hiện tại), phiên âm = các `sv` nối
dòng, dịch nghĩa = các `vi` nối dòng, cặp câu lưu để train. Kết quả engine **tự động ở trạng thái
"đã duyệt"** → có ngay trong file xuất dữ liệu train (đổi ở
`text_engine_runner.ENGINE_RESULT_REVIEW_STATUS` nếu muốn qua bước duyệt như file nhập).

---

## 2. Tạo file adapter

```bash
cd nlp_family_extractor/app/hannom
cp text_engines_local.example.py text_engines_local.py
```

Backend tự nạp `text_engines_local.py` khi khởi động (`app/hannom/text_engines.py:load_local_engines`).
Không có file → web vẫn chạy bình thường. File lỗi → server **không sập**, lỗi hiện ở
**Admin › Cấu hình › Engine phiên âm / dịch nghĩa**.

---

## 3. Viết adapter cho tool của bạn

Khung mẫu — phần duy nhất bạn phải tự viết là `goi_tool`:

```python
from __future__ import annotations

import json
import re

from app.hannom.text_engines import register_text_engine

# Prompt {cn, sv, vi} — lấy nguyên từ `context_content` trong
# TOOL_Gemini_API/tool_gemini_api.ini (thay "@" bằng xuống dòng).
PROMPT = """…prompt của bạn…

Văn bản cần xử lý:
{text}"""

JSON_OBJECT = re.compile(r'\{\s*"cn".*?\}', re.DOTALL)


def goi_tool(prompt: str) -> str:
    """BẠN VIẾT: gửi prompt qua tool của bạn, trả về câu trả lời dạng text."""
    raise NotImplementedError


def gemini_web(hannom_text: str, *, page_number: int) -> list[dict]:
    answer = goi_tool(PROMPT.format(text=hannom_text))
    rows = [json.loads(m) for m in JSON_OBJECT.findall(answer)]
    if not rows:
        raise ValueError(f"Trang {page_number}: tool không trả về JSON {{cn, sv, vi}}")
    return [{"cn": r["cn"], "sv": r["sv"], "vi": r["vi"]} for r in rows]


register_text_engine("gemini-web", gemini_web)
```

Lưu ý khi viết:

- `extract_json()` trong tool **chỉ lấy object đầu tiên** — 1 trang thường nhiều câu, nên dùng
  `findall` như trên để lấy **tất cả**.
- Muốn 2 engine (ChatGPT + Gemini): viết 2 hàm, gọi `register_text_engine` 2 lần với 2 tên khác nhau.
- Mỗi engine chạy **tuần tự 1 việc/lần** (1 thread riêng / engine) → hợp với tool chỉ điều khiển
  1 trình duyệt. 2 engine khác nhau có thể chạy song song.
- Khởi tạo tool **1 lần** (biến toàn cục, tạo lười ở lần gọi đầu) thay vì mỗi trang mở 1 trình
  duyệt mới. Khi gặp lỗi, gọi `reset()` của tool để lần sau chạy lại sạch.
- Quá 600 giây, Python **không dừng được** lời gọi đang chạy — nó vẫn chạy ngầm và có thể giữ
  trình duyệt bận, nên lần chạy kế tiếp phải chờ. Nên đặt timeout trong chính tool (`timeout` ở
  `.ini`) **nhỏ hơn 600 giây**.

---

## 4. Thử luồng chạy trước, chưa cần tool

File mẫu có sẵn engine **`echo`** (không gọi dịch vụ nào, mỗi dòng Hán Nôm thành 1 câu):

1. Để nguyên file mẫu (chưa sửa) dưới tên `text_engines_local.py`, khởi động lại backend
   (`uvicorn api:app --reload --port 8002`).
2. **Admin › Cấu hình** → card **"Engine phiên âm / dịch nghĩa"** phải thấy `echo`.
3. Mở 1 bộ gia phả có OCR → tab **"Phiên bản & nhập LLM"** → chọn `echo` → **Chạy engine**.
4. Cột **Chạy**: Đang chờ → Đang chạy → **Xong** (bảng tự tải lại mỗi 5 giây).

Chạy được `echo` = khe cắm hoạt động; sau đó mới thay bằng tool thật.

---

## 5. Bật/tắt engine

**Admin › Cấu hình › Engine phiên âm / dịch nghĩa**: mỗi engine 1 công tắc, lưu vào setting
`HANNOM_TEXT_ENGINES`. Bắt buộc bật **ít nhất 1** engine (khi đã có engine đăng ký). Chưa lưu lần
nào → mặc định bật tất cả engine đã đăng ký.

Ai mở được bộ gia phả (chủ bộ hoặc admin) thì bấm **Chạy** được.

---

## 6. Triển khai trên server (phần bạn tự lo)

Hiện trạng (`nlp_family_extractor/Dockerfile`, `infra/docker-compose.yml`):

- Image backend là `python:3.11-slim`, **không có Chrome**.
- `COPY . .` → file `text_engines_local.py` có mặt trong thư mục lúc build sẽ vào image.
- Container chỉ mount `./nlp_family_extractor/data:/app/data`.
- uvicorn chạy **1 tiến trình**. Hàng đợi engine nằm trong bộ nhớ của tiến trình đó — **đừng** thêm
  `--workers N` (mỗi worker sẽ có hàng đợi riêng, 2 job có thể điều khiển cùng 1 trình duyệt).

Việc cần làm:

1. Cài Chrome + thư viện của tool (`selenium`, `undetected-chromedriver`, …) vào image backend.
2. Đăng nhập tay 1 lần trên máy có màn hình để sinh `cookies.pkl` (xem `TOOLS_LLM_API.md`), rồi
   đưa cookie + thư mục profile Chrome vào container bằng **volume** (đừng commit cookie vào repo).
3. Sửa `.ini` của tool: `cookies_path`, `user-data-dir` trỏ tới đường dẫn **trong container**;
   `headless_mode = True`; `manual_login = False`.
4. Khởi động lại backend → kiểm tra card Cấu hình không báo lỗi nạp file.

Cookie hết hạn → mọi lần chạy báo lỗi đăng nhập → làm lại bước 2.

Khi server khởi động lại, các lần chạy đang chờ/chạy dở **tự chuyển sang Lỗi** ("Server khởi
động lại…") — bấm **Chạy** lại.

---

## 7. Định dạng file nhập (đường B, không cần server)

JSON hoặc JSONL, mỗi câu 1 record:

```text
{"source": "gemini-web", "model_note": "Gemini 2.5, prompt v1"}
{"page": 1, "cn": "乾坤天意愛維新", "sv": "Càn khôn thiên ý ái duy tân", "vi": "…"}
{"page": 1, "cn": "…", "sv": "…", "vi": "…"}
```

- `page` = số trang của bộ gia phả trên web (bắt đầu từ 1).
- Bấm **Kiểm tra & xem trước** trước khi **Nhập**: lỗi (thiếu trường, trang không tồn tại) chặn
  nhập; cảnh báo (< 80% chữ Hán khớp OCR của trang) vẫn cho nhập.
- File nhập tạo version **chờ duyệt** — admin duyệt mới vào dữ liệu train.
- Gọi bằng script: `POST /api/user/documents/{scan_id}/imports` với
  `{"source", "model_note", "records": […], "dry_run": true}` (token đăng nhập), đổi `dry_run`
  thành `false` để nhập thật.

---

## 8. Lấy dữ liệu train

Admin → tab **"Phiên bản & nhập LLM"** của bất kỳ bộ nào → **Xuất dữ liệu train (JSONL)**
(`GET /api/admin/training-export`). Mỗi dòng: `{scan_id, version_id, source, page, cn, sv, vi}` —
gồm mọi version có `review_status = approved`: version nhập file đã được admin duyệt + version
engine (tự đặt "đã duyệt"). Mang file lên Colab để train (nhớ tắt runtime khi xong).

> ⚠️ Giới hạn đã biết (chưa sửa): export lọc theo `review_status`, **không** xét lần chạy engine có
> thành công không. Version engine được tạo bằng cách sao chép version cha (gồm cả `pairs`), nên
> nếu version cha có `pairs` mà lần chạy engine **lỗi** hoặc chỉ chạy **một phần trang**, các cặp câu
> sao chép đó vẫn bị xuất với `source = engine-…`. Thường không xảy ra (version cha là pipeline/v1
> import, không có `pairs`). Cách tránh khi sửa: export chỉ lấy version engine có bước dịch `done`,
> và chỉ trang do engine ghi.

---

## 9. Xử lý sự cố

| Triệu chứng | Nguyên nhân thường gặp | Xử lý |
|---|---|---|
| Card Cấu hình báo "Lỗi khi nạp text_engines_local.py" | Lỗi cú pháp, thiếu thư viện trong image | Đọc traceback trên card; cài thư viện vào image |
| Không thấy engine trong ô chọn | Chưa `register_text_engine`, hoặc engine đang tắt | Kiểm tra card Cấu hình |
| Nút **Chạy engine** mờ | Không có engine nào đang bật | Bật ở card Cấu hình |
| Lỗi "Không có trang nào có văn bản Hán Nôm" | Bộ chưa OCR / chưa có trang | OCR trước, hoặc chạy `--backfill` cho bộ đã import |
| Lỗi "Kết quả engine không hợp lệ: … thiếu sv" | Tool trả JSON thiếu trường | Sửa prompt / phần tách JSON trong adapter |
| Lỗi `TimeoutError: quá 600s` | Tool chờ trả lời quá lâu | Giảm `timeout` trong `.ini`; kiểm tra cookie |
| Kẹt ở "Đang chạy" rất lâu | Lời gọi trước quá giờ vẫn giữ trình duyệt | Khởi động lại backend |

---

## Tham chiếu code

| Phần | File |
|---|---|
| Đăng ký engine, nạp adapter | `nlp_family_extractor/app/hannom/text_engines.py` |
| Hàng đợi chạy nền, timeout, khởi động lại | `nlp_family_extractor/app/hannom/text_engine_runner.py` |
| File mẫu | `nlp_family_extractor/app/hannom/text_engines_local.example.py` |
| Kiểm tra `{cn, sv, vi}` | `nlp_family_extractor/app/workspace/llm_import.py` |
| Endpoint | `POST /api/user/documents/{id}/text-engine-runs`, `GET /api/user/text-engines`, `GET/PUT /api/admin/text-engines` |
| Giao diện | `family-saga-io/src/components/documents/LlmImportPanel.tsx`, `components/settings/OcrEnginesCard.tsx` |
| Test | `nlp_family_extractor/tests/test_text_engines.py` |
