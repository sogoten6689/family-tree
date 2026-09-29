# Hướng dẫn dùng 2 tool LLM API (ChatGPT & Gemini)

Hai tool bọc **web UI** của ChatGPT và Gemini bằng Selenium để gọi như API, dùng
cho việc tách câu Hán tự / Hán Việt / Quốc ngữ thành JSON `{cn, sv, vi}` phục vụ
Track 1 & 2 của repo.

> **Đây không phải API chính thức.** Cả 2 tool điều khiển browser thật, phụ thuộc
> DOM của trang web nên **sẽ vỡ khi nhà cung cấp đổi giao diện**. Kết quả trả về
> phải được người soát kiểm tra trước khi ghi vào `data/` — xem §Ràng buộc.

## Trạng thái thật (16.09.2026)

| Tool | Khởi động browser | Đăng nhập | Gửi/nhận end-to-end |
|---|---|---|---|
| `TOOL_ChatGPT_API` | Chạy được | **Chưa** | **Chưa xác minh** |
| `TOOL_Gemini_API` | Chạy được | **Chưa** | **Chưa xác minh** |

Cả 2 tool đều dừng ở bước đăng nhập. Chưa tool nào chạy trọn vẹn một lượt
gửi prompt → nhận câu trả lời. Đừng coi phần dưới là "đã hoạt động".

## Vị trí

```
TOOL_ChatGPT_API/     tool_chatgpt_api.py  + .ini + test.py
TOOL_Gemini_API/      tool_gemini_api.py   + .ini + test.py + probe_dom.py
```

## Cài đặt

```bash
cd TOOL_ChatGPT_API      # hoặc TOOL_Gemini_API
pip install -r requirements.txt
```

Cần Chrome cài sẵn. `undetected_chromedriver` tự tải ChromeDriver; cả 2 tool đã
đọc phiên bản Chrome thật và truyền `version_main` nên không bị lệch phiên bản.

## Cách dùng

API công khai của 2 tool **giống hệt nhau**, đổi tên class là xong:

```python
from tool_chatgpt_api import ToolChatGPTAPI   # hoặc:
from tool_gemini_api import ToolGeminiAPI

tool_api = ToolChatGPTAPI()                   # hoặc ToolGeminiAPI()
tool_api.upload_file("/duong/dan/file.txt")   # -> bool
resp = tool_api.send_request("Dịch: 乾坤天意愛維新")   # -> str | None
tool_api.reset()                              # restart browser, giữ config
tool_api.quit()
```

Helper `extract_json(text)` (có ở cả 2 file) bóc object JSON đầu tiên khớp
`{"cn": ...}` từ câu trả lời.

## Đăng nhập (bước đang chặn)

Lần đầu **bắt buộc** đăng nhập tay để sinh cookie:

```bash
# sửa file .ini: manual_login = True, headless_mode = False
python3 test.py
# Chrome mở ra -> đăng nhập -> quay lại terminal nhấn Enter
```

Cookie ghi ra `cookies.pkl`; sau đó trỏ `cookies_path` tới file này và có thể
đặt lại `manual_login = False`.

Vì sao không tự động hoá được: cả 2 trang đều chặn ở màn đăng nhập, và khi chưa
đăng nhập thì **DOM khác hoàn toàn**:

- ChatGPT chỉ render "lightweight composer" (id `mobile-composer-prompt`), không
  có `#prompt-textarea` mà code cần → timeout.
- Gemini vẫn hiện ô nhập cho khách nhưng không lưu hội thoại, và các phần tử
  khung trả lời chưa dựng nên không kiểm chứng được selector.

## Cấu hình (`*.ini`)

| Khoá | Ý nghĩa |
|---|---|
| `user-data-dir` | Thư mục profile Chrome riêng cho tool |
| `manual_login` | `True` để dừng cho đăng nhập tay |
| `headless_mode` | `True` chạy ẩn (chỉ dùng sau khi đã có cookie) |
| `log_level` | `none/info/debug/error` — `debug` in ra selector nào match |
| `cookies_path` | File cookie đã lưu |
| `wait_time` | Thời gian chờ 1 element (giây) |
| `timeout` | Thời gian tối đa chờ 1 câu trả lời (giây) |
| `cleanup_context` | Kết thúc thì xoá ngữ cảnh / mở chat mới |
| `context_content` | Prompt hệ thống, dùng `@` để ngắt dòng |

Đường dẫn trong 2 file `.ini` hiện trỏ `/tmp/...` (macOS). Nếu chạy trên Windows
phải sửa lại `user-data-dir`.

## Khác biệt giữa 2 tool

| | ChatGPT | Gemini |
|---|---|---|
| Chọn model | `use_chatgpt4o = True/False` | Không có; đổi model bằng tay trên UI |
| Xoá ngữ cảnh | Xoá hẳn hội thoại | Mở chat mới (`new_chat()`) hoặc reload |
| Chờ trả lời | Dựa vào selector nút Stop / voice | Poll text đến khi ngừng đổi (3 lần giống nhau) |
| Upload file | `input[type=file]` có sẵn trong DOM | Phải bấm "Upload & tools" mới có input |
| Selector | Hardcode 1 selector/vai trò | Danh sách ứng viên, thử lần lượt |

Cách chờ trả lời của bản Gemini ít phụ thuộc DOM hơn nên bền hơn; bản ChatGPT
vẫn dùng selector cũ từ giữa 2024.

## Trạng thái selector

Bản Gemini đã dò DOM thật bằng `probe_dom.py`:

- **Đã xác minh:** ô nhập `rich-textarea div.ql-editor[contenteditable="true"]`;
  nút gửi `button[aria-label="Send message"]` (chỉ hiện sau khi ô nhập có chữ);
  nút mở upload `button[aria-label="Upload & tools"]`.
- **Chưa xác minh:** khung trả lời, nút Stop, New chat, `input[type=file]` —
  cần đăng nhập mới kiểm được.

Lưu ý: `button.send-button` (xuất hiện trong nhiều tài liệu automation Gemini)
**không tồn tại** trên DOM hiện tại.

Bản ChatGPT: các selector trong `send_request` / `upload_file` / `delete_context`
(`aria-label='Send prompt'`, `aria-label='Start voice mode'`, XPath nút Delete)
viết theo DOM giữa 2024, **chưa kiểm lại**. Rất có thể phải cập nhật sau khi
đăng nhập xong.

Dò lại DOM Gemini bất cứ lúc nào:

```bash
cd TOOL_Gemini_API && python3 probe_dom.py
```

Script này chỉ đọc DOM: đếm selector nào match, gõ thử chuỗi vào ô nhập để nút
gửi hiện ra, liệt kê các nút đang hiện, chụp `gemini_probe.png`. **Không bấm gửi**
nên không tạo request nào lên Gemini.

## Lỗi thường gặp

| Triệu chứng | Nguyên nhân |
|---|---|
| `SessionNotCreatedException: only supports Chrome version N` | Lệch ChromeDriver — đã fix bằng `version_main`, nếu còn thì xoá cache `~/.local/share/undetected_chromedriver` |
| `TimeoutException` khi chờ ô nhập | Chưa đăng nhập (hay gặp nhất), hoặc DOM đã đổi |
| `send_request` trả `None` | Không tìm được ô nhập, hoặc hết `timeout` |
| `upload_file` trả `False` | Không mở được menu upload / không thấy `input[type=file]` |
| Chrome không mở, treo im | Còn tiến trình Chrome cũ giữ `user-data-dir` — dùng `reset()` hoặc kill tay |

## Ràng buộc khi dùng cho dữ liệu repo

Theo `CLAUDE.md` và `AGENTS.md`:

1. Output của LLM là **inference**, không phải fact. Ghi vào `ghi_chu` phải gắn
   nhãn rõ, không trình bày như đã đọc trực tiếp bản gốc.
2. Không dùng để đoán `quy_mo` / `hinh_thuc` / `dia_danh` / `nien_dai` — thiếu
   bằng chứng thì để `null`.
3. Chỉ xử lý tài liệu **bản thân một bộ phả**; không dùng cho kế ước, tế văn,
   sách lý thuyết (xem `manifest/classification.json` → `loai_khoi_pham_vi`).
4. Không thay thế cơ chế vote OCR: LLM **không** được tính là engine thứ 3 trong
   `scripts/vote_ocr.py`.
5. Validate schema trước mọi commit dữ liệu.
