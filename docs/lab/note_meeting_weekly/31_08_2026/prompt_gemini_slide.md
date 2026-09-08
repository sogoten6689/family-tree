# Prompt cho Gemini — tạo Google Slides "Hướng dẫn Gia phả Hán Nôm"

Copy nguyên khối dưới đây, dán vào Gemini (trong Google Slides: *Trợ giúp tôi tạo* / Gemini app rồi xuất sang Slides).

---

```
Tạo một bộ slide Google Slides tiếng Việt, chủ đề "Phân loại và Mã định danh Gia phả Hán Nôm", dùng để báo cáo trong buổi họp lab với giảng viên hướng dẫn. Phong cách: học thuật, tối giản, nhiều bảng/sơ đồ hơn là văn xuôi dài. Khoảng 12–14 slide, cấu trúc và nội dung CHÍNH XÁC như sau (không tự thêm số liệu hay ví dụ ngoài những gì liệt kê):

Slide 1 — Tiêu đề: "Phân loại & Mã định danh Gia phả Hán Nôm". Phụ đề: báo cáo tuần 31/08–07/09.

Slide 2 — Quy trình xử lý (sơ đồ ngang 5 bước):
Thu thập (phân loại trước) → OCR (mixing PaddleOCR v6, DeepSeek, CLC, Google Vision, Gemini) → Dịch âm (mô hình Lab) → Dịch nghĩa (Qwen 3.6 37B) → Dựng cây gia phả.

Slide 3 — Phân loại theo Quy mô & Phạm vi (bảng 5 dòng, cột "Cấp" + "Tên gọi" + "Phạm vi"):
1 Hợp phả/Tông phả — toàn gia tộc, nhiều dòng/chi ở nhiều địa phương, chung thủy tổ.
2 Tộc phả/Đại tộc phả — toàn bộ nhánh/chi của một họ lớn từ Thủy tổ một địa phương.
3 Chi phả/Phân chi phả — một chi/nhánh/phái tách từ họ lớn.
4 Phân phả/Nhánh phả — một tiểu chi, từ ông/bố xuống con cháu trong một gia đình nhỏ.
5 Ngọc phả/Tôn phả — gia phả hoàng gia, hoàng tộc.

Slide 4 — Phân loại theo Hình thức trình bày (4 ô ngang, có icon gợi ý):
Bộ phả (譜編) — sách chép tay, văn xuôi tự sự chi tiết.
Phả đồ (譜圖) — sơ đồ cây/bảng biểu, chỉ tên + quan hệ thứ bậc.
Phả điệp (譜牒) — trích lục tóm tắt, chỉ đời chính + sự kiện lớn.
Bia phả — khắc trên đá tại nhà thờ họ.
Ghi chú nhỏ dưới slide: "Phả ký không thuộc nhóm này — đó là một thành phần Nội dung, xem slide 5."

Slide 5 — Phân loại theo Nội dung & Chức năng (5 gạch đầu dòng):
Thế hệ phả (danh sách các thế hệ từ Thủy tổ).
Tộc ký/Phả ký (văn xuôi kể lịch sử nguồn gốc, di dân, chiến công).
Tộc ước/Gia quy (quy định, điều cấm, lệ họ).
Trạch điền bạ/Hương tự bạ (sổ ruộng thờ + vị trí mộ).
Gia lễ & Tế văn (văn tế, bài khấn).

Slide 6 — Vì sao KHÔNG dùng tên họ làm tiêu chí phân loại chính (3 lý do):
Trùng lặp quá lớn (họ Nguyễn ~38–40% dân số VN).
Không cùng huyết thống (Nguyễn Hà Tĩnh ≠ Nguyễn Bắc Ninh, Thủy tổ khác nhau).
Lịch sử từng đổi họ (Mạc → Nguyễn/Trịnh).
Kết luận: công thức định danh đúng = {Tên Họ} + {Địa danh Thủy tổ} + {Loại Phả}.

Slide 7 — Cấu trúc một bộ gia phả chuẩn (4 phần, dạng timeline dọc):
1. Tự/Phả tự — lời tựa, địa danh, niên hiệu, triết lý "Tôn tổ thu tộc".
2. Phả lệ/Tông phổ lệ — quy tắc ghi chép, chu kỳ trùng tu 10–20 năm.
3. Phả đồ & Phả ký — sơ đồ thế hệ (Chiêu–Mục) + tiểu sử từng người.
4. Tộc ước & Từ đường — quy ước đạo đức, quản trị hương hỏa.

Slide 8 — Quy trình xây dựng mã định danh, 5 bước (sơ đồ dọc có mũi tên):
Bước 1: Lấy 8 trường metadata cốt lõi.
Bước 2: Cấu trúc mã [Bộ sưu tập]-[Địa danh]-[Họ]-[SốTT].[Dạng thức].
Bước 3: Lập thẻ Catalogue chi tiết.
Bước 4: Lập bảng thư mục tra cứu tổng hợp.
Bước 5: Search indexing theo Địa danh / Nhân vật / Niên đại.

Slide 9 — Ví dụ mã định danh (bảng 3 dòng):
HN-GP.HD.VU-008.B | Vũ tộc đại phả | Vũ | Bình Giang, Hải Dương | 1865 | Sách giấy
HN-GP.HT.NG-002.Đ | Nguyễn thị phân chi đồ | Nguyễn | Can Lộc, Hà Tĩnh | 1912 | Phả đồ
HN-GP.HN.TR-015.M | Trần công mộ chí minh | Trần | Thanh Oai, Hà Nội | 1789 | Bia đá

Slide 10 — Case study: Phan gia công phả (潘家公譜):
Ấn bản học thuật song ngữ, Nxb Thế Giới 2006, tập 8 CTNC Gia phả Việt Nam (GS Phan Huy Lê hiệu đính).
169 trang ảnh, 0 lớp text — chỉ facsimile tr.141–310 nên OCR, cấm OCR trang dịch.
4 chứng bản A–D đối chiếu, 2 bản lưu tại Viện Hán Nôm (A.2963, A.2691).
Mã áp dụng: HN-GP.HT.PN-001.B (Tộc phả, họ Phan, Hà Tĩnh, dạng Bộ phả).

Slide 11 — Lưu ý số hóa tài liệu gốc (4 gạch đầu dòng):
Không dùng scanner khay nạp/ép phẳng — dùng máy chụp overhead/DSLR.
File Master: TIFF/RAW không nén, ≥300 DPI (nên 600 DPI), 24-bit màu.
Không dùng đèn flash trực tiếp (UV làm giòn giấy dó).
Không chỉnh màu tự nhiên hay xoá dấu ố mốc — đó là chứng cứ niên đại.

Slide 12 — 2 điểm mâu thuẫn cần thầy chốt (bảng 2 cột "Theo tài liệu chuẩn" / "Theo lời dặn trong họp"):
Hình thức: Bộ/Đồ/Điệp/Bia  ||  Bộ/Đồ/Ký/Điệp
Mã định danh: 4 thành phần (không có Quy mô, Thời gian)  ||  6 trục (có Quy mô + Thời gian)

Slide 13 — Việc cần làm tuần này (checklist):
Chốt định nghĩa ID và Thời gian trong mã.
Xác nhận nguồn bảng Hình thức.
Timeline: tháng nào xong data, tháng nào xong mô hình.
Đọc kỹ để chuẩn bị trả lời hội đồng.

Slide 14 — Cảm ơn / Hỏi đáp.

Yêu cầu định dạng: mỗi slide có tiêu đề rõ, nội dung dạng bullet ngắn hoặc bảng, không viết đoạn văn dài. Dùng font dễ đọc, màu trung tính (trắng/xám/xanh navy), không dùng màu quá sặc sỡ. Giữ đúng thuật ngữ Hán Việt và chữ Hán (譜編, 譜圖, 譜牒, 潘家公譜...) như đã cho, không phiên âm lại.
```
