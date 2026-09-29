# Gửi thầy — 28/09: tổng hợp định hướng đề tài + kết quả săn mô hình Hán TQ

> ~1 trang · 2026-09-28 · tổng hợp từ chỉ đạo thầy 20/07–21/09 + kết quả khảo sát mô hình (nhánh song song)

## Việc đã làm

**1. Tổng hợp toàn bộ chỉ đạo của thầy (4 buổi họp: 24/08, 31/08, 14/09, 21/09) thành 1 tài liệu định hướng** — `docs/thesis/dinh_huong_nghien_cuu_theo_thay_2026-09.md`. Đối chiếu fact/suy luận, tách rõ phần đã chắc (OCR ensemble + vote Levenshtein MED — đã làm, đo được) khỏi phần còn mơ hồ (ý "tự động hình [thành cây]", "bài toán song song" — chưa rõ, không tự đoán tiếp).

**2. Đọc thêm báo cáo 21/09 (kết quả "đi săn" mô hình gia phả Hán TQ, T1–T3)** — nằm trên nhánh Claude khác (`claude/meeting-project-evaluation-eui68s`), chưa merge vào nhánh làm việc chính. Phát hiện quan trọng nhất: **không có mô hình mã nguồn mở nào giải quyết trực tiếp "gia phả Hán TQ → cây có cấu trúc"** — khảo sát có hệ thống, không phải do tìm chưa đủ kỹ. Đây là bằng chứng củng cố khoảng trống học thuật cho đề tài, không phải tin xấu.

**3. Bảng ứng viên đã chạy thử thật (có log):**

| Ứng viên | Việc | Kết quả (chữ phồn thể — đúng dạng Hán-Nôm thật) | License |
|---|---|---|---|
| Jiayan | Tách từ | Đúng, không nhạy phồn/giản thể | MIT |
| guwen-ner (GuwenBERT) | NER | **0/4 thực thể** — gần như vô dụng nếu không ép giản thể | Apache-2.0 |
| CHAT_models (kraken) | OCR Hán cổ dọc | Đọc được phần lớn, cần ghim `kraken<5` | CC BY-NC 4.0 — **không còn là rào cản** (đề tài phi thương mại) |
| XunziLLM | IE người/sự kiện/địa điểm + dịch | **Chưa chạy thử được** — host ModelScope, bị chặn egress trong sandbox Claude Code cloud (xác nhận 2 lần độc lập) | Chưa rõ |

Bài **CBDB kinship normalization** (Harvard) chuẩn hoá quan hệ thân tộc Hán về đúng 3 loại (cha-con/mẹ-con/chồng-vợ) — **khớp thẳng** thiết kế rule hiện tại (`spouse_of`/`parent_of`/`sibling_of`), nên dùng làm cơ sở lý thuyết cho chương thiết kế quan hệ.

**4. Đã giao task cho Cursor** (`docs/planning/xunzillm_install_demo_task.md`): cài + chạy demo XunziLLM trên máy có thể truy cập ModelScope, dùng đúng câu test đã chạy với guwen-ner để so sánh công bằng, license-gate trước khi dùng.

## Câu đóng góp đề xuất (cần thầy chốt)

> *"Xây dựng và đánh giá corpus song ngữ Hán Nôm–Việt lĩnh vực gia phả (thu thập có phân loại, OCR ensemble kiểm định thống kê), làm nền fine-tune mô hình dịch nghĩa chuyên biệt và huấn luyện mô hình trích xuất thực thể–quan hệ để tự động sinh cây gia phả, có so sánh với hướng kế thừa từ mô hình gia phả Hán hiện có."*

## Cần thầy

1. Câu đóng góp trên có đúng ý thầy không?
2. "Gia phả xoay quanh nó... tự động hình [thành cây]" (họp 14/9) — câu ghi bị thiếu chữ, nhờ thầy nói lại đầy đủ. Nay đã rõ **không có 1 mô hình transfer trực tiếp sẵn** (mục 2), nên ý thầy có thể khác suy đoán ban đầu.
3. "Bài toán song song" — dữ liệu song ngữ hay xử lý đa luồng, hay cả hai?
4. Tài khoản `ethanyt` (tác giả các model `guwen-*`) — có phải một thành viên trong nhóm nghiên cứu của thầy không? Nếu đúng nên hỏi trực tiếp thay vì suy luận từ ngoài.
5. Timeline tiếp cận gia phả Nguyễn Phước.

Chi tiết đầy đủ (fact/suy luận/độ tin cậy từng điểm): `docs/thesis/dinh_huong_nghien_cuu_theo_thay_2026-09.md`.
