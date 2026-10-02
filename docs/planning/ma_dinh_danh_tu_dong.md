# Mã định danh tự tạo — quyết định 02/10/2026

**Người quyết định:** Lâm (02/10/2026). Thay phần *đánh số* trong quy ước đã chốt với thầy 07/09
(`docs/lab/note_meeting_weekly/31_08_2026/huong_dan_gia_pha_han_nom.md` §"Đối chiếu với mã 6 trục").
Cấu trúc mã **giữ nguyên**: `F-{chữ A–V}-{mã Họ}-{Địa danh}-{3 số}-{Năm soạn gốc}`.

> ⚠️ Chưa ghi nhận thầy đã duyệt thay đổi này — cần báo lại trong buổi họp kế tiếp.

## Thay đổi so với quy ước 07/09

| | Quy ước 07/09 | Từ 02/10/2026 |
|---|---|---|
| Ai tạo mã | Người đọc, sau khi xác nhận đủ 5 trường | **Tự tạo** từ thông tin có sẵn |
| Số 3 chữ số | Tăng dần theo **thứ tự nhập catalogue**, dùng chung mọi loại | Tăng dần **riêng theo từng chữ A–V** (quy mô × hình thức): số lớn nhất đang có ở chữ đó + 1 |

## Nguồn thông tin (theo thứ tự ưu tiên)

1. **Catalogue nghiên cứu** (`hannom-bilingual-dataset`, trường `ma_dinh_danh`) — 10 bộ đã chốt
   (`001`–`010`): chép **nguyên văn**, không tính lại. `ma_dinh_danh_nguon = "catalogue"`.
2. **Gemini**: sau bước dịch nghĩa, nếu bộ **chưa có mã**, Gemini trích
   `{quy_mo, hinh_thuc, ho, dia_danh_ngan, nam_soan_goc}` từ bản dịch → tạo mã.
   `ma_dinh_danh_nguon = "gemini"`. Thiếu/sai bất kỳ trường nào → **không tạo** (ghi lý do).

Mã đã có **không bao giờ bị ghi đè**.

## Hệ quả cần biết

- Với dãy riêng theo chữ, **số 3 chữ số không còn duy nhất** giữa các chữ (vd `F-B-…-009-…` và
  `F-M-…-009-…` cùng tồn tại); **cả mã** vẫn duy nhất.
- Mã nguồn `gemini` dựa trên thông tin LLM trích — dữ liệu cũ cho thấy niên đại thường cần suy
  luận (vd nom-1158: bản dịch "năm thứ hai" nhưng can-chi chỉ 1848). Giao diện gắn nhãn
  "Tự tạo (Gemini)" để biết mã nào cần đối chiếu lại.
- Mỗi lần tạo bằng Gemini = 1 lượt gọi API (tốn phí, R3).

## Code

- `nlp_family_extractor/app/workspace/ma_dinh_danh.py` — bảng tra, `next_sequence_for_letter`
- `nlp_family_extractor/app/workspace/ma_dinh_danh_auto.py` — prompt Gemini, kiểm tra, `ensure_ma_dinh_danh`
- `UserScanRepository.auto_assign_ma_dinh_danh` — gán mã + `ma_dinh_danh_nguon`
- Tự gọi sau khi dịch: `api.py` (luồng analyze-image); thủ công: `POST /api/user/documents/{id}/ma-dinh-danh/auto`
- Import catalogue: `tools/import_hannom_bilingual_corpus.py` (`--backfill` cho bộ đã import)
