# Gửi thầy — tuần 28/08–03/09: OCR kế ước vs tế văn; lab; Qwen

> ½–1 trang · 2026-08-28 · track B (Hán-Nôm) · Label Studio **pending**

## Việc đã làm

Đối soát **15 trang** scan Nguyễn Kế Hán-Nôm (Diên Khánh, thảo/khế) với `Tài liệu dịch hán nôm Ô.cố.docx`. Bảng: `data/00_raw/du_lieu_han_nom_moi/25_8_2026/Hương/doi_soat_oco.md`.

## Số liệu Paddle (cùng engine PP-OCRv6 medium)

| Mẫu | Script | Mean | Ghi chú |
|-----|--------|------|---------|
| Tế văn Vũ Lâm (24/08, 1 tờ in, sau RTL) | chữ in, cột thẳng | **~0.91** | 17 dòng; lab phiên âm **có** |
| Kế ước Hương (25/08, 15 trang) | thảo / khế không đều | **0.70** | 235 dòng; trang yếu 1–7, 11–12, 14 |

Chênh ~0.21 là **khác loại chữ và layout**, không khác model. Trang Hương in sẵn + chữ ký (p.10, header Pháp `REQUÊTES`) mean ~0.91 — cùng mức tế văn.

## Ô.cố

Word **không** phải bản Hán từng dòng (gần 0 CJK). Là 6 mục dịch/ghi chú Quốc ngữ. Map được:

- p.0–2: phân gia tài — OCR **阮泰 / 阮朋 / 阮珠**, cha **阮文顛**. Word §5 ghi con **Thị Khảm / Khảng / Chinh** → lệch, cần Hương/thầy xem lại ảnh.
- p.9 ≡ p.13 (trùng ảnh): **阮有朋** (≈ Nguyễn Hữu Bằng) tuyệt mại cho **阮玉珠**.
- p.14: **喬文祿** ≈ Kiều Văn Lộc (§1). Niên hiệu Thành Thái 19 trong Word **không** đọc được trên OCR trang này.

Lab Kim Hán Nôm trên Hương: **0/15** (`access_denied`). Không có chuỗi Hán đã hiệu đính cho 15 trang.

## Qwen dịch nghĩa

**Chưa chạy.** Repo không có API key Qwen; lệnh tuần này là *một trang* trên Hán đã hiệu đính, **không** fine-tune 37B. Stub: `docs/lab/note_meeting_weekly/28_08_2026/qwen_dich_nghia.md`.

Khi có API: ưu tiên **một khế kế ước** (p.0 hoặc p.9, sau hiệu đính) chứ không tế văn — đúng domain LV. Tế văn đã có dịch tay.

## Cần thầy

1. Key / endpoint Qwen (một lần gọi trang).  
2. Xác nhận §5 Ô.cố (nam 阮 vs nữ Thị).  
3. Lab Hương: tài khoản còn `access_denied`?

Không OCR 477 trang Nguyễn Phúc (Quốc ngữ in 1995). Không FT Qwen tuần này.
