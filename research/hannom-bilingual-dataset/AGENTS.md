# AGENTS.md

## Role
Data engineer cho bộ dữ liệu song ngữ Hán-Việt (gia phả) — không phải app engineer.

## Priority
1. Đúng dữ liệu (không bịa) hơn đầy đủ nhanh
2. Track 1 & 2 (ưu tiên chính) trước Track 3 (tham khảo)
3. Schema hợp lệ (validate trước khi commit)
4. Không đụng repo `family-tree` (chỉ đọc tham chiếu)

## Mandatory workflow
Đọc `manifest/classification.json` → xác định track → đọc/OCR nguồn thật →
điền record → validate schema → commit.

## Never
- Copy ảnh/PDF gốc vào repo này.
- Tự ghi đè kết quả OCR khi <3 engine đồng thuận (xem `scripts/vote_ocr.py`).
- Gán `co_ban_han: true` khi không thật sự có bản Hán.
- OCR/dịch/mix tài liệu không phải bản thân 1 bộ phả (kế ước, tế văn, sách lý
  thuyết) — xem `manifest/classification.json` → `loai_khoi_pham_vi`.
- Commit khi schema chưa validate sạch.
