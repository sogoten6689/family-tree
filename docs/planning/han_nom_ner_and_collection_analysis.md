# Phân tích: NER/RE cho chữ Hán và thu thập dữ liệu Hán Nôm (GP-3, GP-7, GP-8, GP-9)

Ngày 12/10/2026. Số liệu đo từ cơ sở dữ liệu web (trang hiện tại của 21 tài liệu hoạt động) và từ repo. Điều gì là suy luận được ghi rõ.

## 1. Hiện trạng kho Hán trên web (đã đo)

| Mục | Giá trị |
|---|---|
| Tài liệu hoạt động | 21 (đã bỏ bản trùng ID 13) |
| Trang | 1.298; 1.284 trang có chữ Hán |
| Chữ Hán trong văn bản hiện tại | 265.835 ký tự Hán (291.481 ký tự kể cả ký tự khác) |
| So với gold Việt hiện có | ~4 lần số ký tự của 25 cây Việt đã soát (68.152) — nhưng **0 nhãn người** |
| Độ phủ engine OCR (số trang có kết quả) | deepseek 1.240 · google_vision 1.072 · paddle_v6 1.059 · kim_hannom_lab 590 · gemini 534 (trên 1.298) |
| Độ đồng thuận giữa engine (`similarity_to_others`, trung bình) | paddle_v6 0,58 · kim_hannom_lab 0,56 · deepseek 0,55 · google_vision 0,50 · gemini 0,45 |

Diễn giải: đồng thuận 0,45–0,58 là **thấp**: các engine đọc cùng một trang ra những chuỗi khác nhau khá nhiều. Đây **không phải độ chính xác** (không có chữ chuẩn để đối chiếu), nhưng cho thấy lỗi OCR sẽ là nguồn nhiễu lớn cho NER, nhất là với tên người. Hạn chế: không có chân trị OCR nên chưa nói được engine nào đúng nhất.

## 2. Rủi ro kỹ thuật đã xác nhận

- **Lệch offset ngoài BMP (câu hỏi mở Q1 của schema):** 847 ký tự ngoài BMP (chữ Hán/Nôm mở rộng như 𭘾, 𠁅) nằm ở **95/1.298 trang (7,3%)**. Python đếm theo code point, trình duyệt theo UTF-16; ở các trang này nhãn có thể lệch sang phải bằng số ký tự ngoài BMP đứng trước. Đã thêm `utf16_to_codepoint` / `codepoint_to_utf16` (có test) để đổi offset khi nhập/xuất; **chưa kiểm** xem bản Label Studio đang dùng đếm theo cách nào (cần thử một trang thật).
- **Chất lượng OCR** (mục 1): nên lọc trang theo đồng thuận khi chọn mẫu gán nhãn.
- **Tài liệu hỗn hợp Việt–Hán** (ID 18) không phù hợp quy tắc "chỉ Hán Nôm": đã loại khỏi mẫu pilot.
- **Quy ước nhãn Hán:** D3–D7 trong `docs/schemas/NER_RE_LABEL_SCHEMA_AND_PIPELINE.md` chưa được thầy duyệt; gán nhãn nhiều trước khi duyệt có thể phải làm lại.

## 3. Phân tích mô hình (GP-7, GP-8, GP-9)

Đã biết từ phần Việt (đo thật): XLM-R-base F1 0,609 ± 0,012, PhoBERT-base 0,539; PER_NAME ≈ 0,39–0,40 yếu nhất; RE F1 0,18 do nhãn quan hệ nhiễu và chỉ có 30 quan hệ người soát. Kết luận rút ra: **nút thắt là số nhãn người soát, không phải kiến trúc**.

Suy ra cho Hán (giả thuyết, chưa kiểm):
- Hán gán nhãn mức ký tự, tên người thường là chuỗi ngắn có hậu tố (公, 氏) nên có thể dễ hơn tên Việt — nhưng OCR nhiễu có thể triệt tiêu lợi thế này.
- SikuBERT (Apache-2.0, mức ký tự) vẫn là ứng viên chính. Chưa có thực nghiệm nên chưa biết cần bao nhiêu nhãn (Q4 của schema).
- Với RE, đừng lặp lại sai lầm cũ: không huấn luyện trên nhãn quan hệ máy chưa soát. Phải có tập quan hệ do người soát đủ lớn trước (hiện 30).

## 4. Đề xuất pilot (không tốn tiền ở giai đoạn này)

Đã dựng mẫu bằng `research/label_studio_pipeline/build_han_pilot.py` (xác định, chạy lại được):
- 97 trang, 18 sách, **25.112 ký tự Hán**, đồng thuận OCR trung bình 0,70 (cao hơn mức chung 0,45–0,58 vì ưu tiên trang đồng thuận cao), 9 trang có ký tự ngoài BMP.
- Đầu ra (gitignore): `data/03_derived/han_pilot_v1/{tasks.json, manifest.csv, report.json}`.
- Tiêu chí thành công đề xuất: IAA ≥ 0,8 cho PER_NAME/LOC/DATE trên 20% phần gán chồng; bảng lỗi theo quy tắc H1–H9.

## 5. Thu thập thêm dữ liệu Hán Nôm (GP-3)

Nguồn đã biết trong repo (`data/05_ops/sources_discovery/sources_registry.json`):
- Nom Foundation (lib.nomfoundation.org): điểm 85, đã thu 5 volume / 163 trang (theo registry; web hiện có nhiều hơn từ các lô khác).
- Thư viện Quốc gia (hannom.nlv.gov.vn): điểm 70, **chưa thu**, cần parser riêng (OPAC).
- 4 sách trong danh mục chưa lên web: Việt sử kính (nom-130), Tả Thanh Oai Ngô tộc tổ mộ (nom-595), Chu tộc hậu kỵ (nom-716), Nguyễn Kế Hán-Nôm.

Tìm kiếm web (12/10/2026) **không** thấy một kho công khai cho tải ảnh gia phả hàng loạt; thấy:
- Thư viện Tổng hợp Thừa Thiên Huế đã số hoá ~418.000 trang (923 họ tộc) từ 2009, chưa rõ công khai; kế hoạch 2026–2030 có "phòng đọc trực tuyến" (chưa có sản phẩm).
- Thư viện Quảng Trị: 11.250 trang, có 99 gia phả (2018), chưa rõ công khai.
- Mục lục gia phả của Viện Hán Nôm và Thư viện Quốc gia do Đại học Kyoto biên soạn (2025): hữu ích để **biết sách nào tồn tại**, không phải để tải.
- Giới hạn: tìm kiếm chỉ lướt; chưa mở từng trang nguồn, chưa kiểm giấy phép. Nhiều tư liệu thuộc sở hữu dòng họ nên cần kiểm quyền sử dụng trước khi đưa vào luận văn.

Đề xuất thứ tự: (1) đưa 4 sách còn thiếu lên web; (2) NLV OPAC (đã chấm 70); (3) liên hệ trực tiếp thư viện địa phương (Huế, Quảng Trị) hỏi điều kiện sử dụng; (4) sách do anh/thầy nhận tay (lô `du_lieu_han_nom_moi`).

## 6. Cần quyết định

1. Có dùng Gemini gán nhãn trước cho Hán không (D9; tốn tiền, RamCloud đang hết hạn mức)? Đề xuất: pilot 25 trang đầu **không** gán trước để đo độ khó thật, rồi so.
2. Ai gán nhãn (cần ≥ 2 người để đo IAA)?
3. Có xin thầy duyệt D3–D7 trước khi gán nhãn không? (đề xuất: có)
4. Kiểm cách đếm offset của Label Studio bằng một trang thật có ký tự ngoài BMP.
