# Thống kê dữ liệu gia phả có chữ Hán Nôm, chia theo nguồn gốc (23/11/2026)

Kiểm kê chỉ đọc: không sửa `data/`, VPS, Drive; không gọi Gemini, Kim Hán Nôm hay Colab.
Mỗi con số có ghi nguồn ở cột "Nguồn" hoặc ở cuối mục, theo bảng mã dưới đây.

## 0. Nguồn số liệu và cách đếm

| Mã | Nơi lấy | Cách đếm |
|---|---|---|
| **S1** | Kho `hannom-bilingual-dataset/data/<track>/<doc_id>.json` (50 bản ghi) | trang = số phần tử `pages`; trang OCR = trang có `l1_ocr.voted_text` khác rỗng; chữ Hán = ký tự CJK (khối cơ bản, Ext A–H, tương thích) trong `voted_text`; cặp = tổng `pairs` (cặp Hán–Việt máy dóng, `align_method` phần lớn `llm_draft`) |
| **S2** | `data/00_raw/hannom/books_catalog.json` (40 mục) | trường `source`, `kind`, `page_count` |
| **S3** | `docs/lab/windows_data_inventory.md` (25/10/2026) | kiểm kê thư mục `D:\cao-hoc\dulieu-thay-cho\data-caohoc` trên máy Windows, so MD5/kích thước với `data/` |
| **S4** | `docs/planning/han_nom_gia_pha_data_discovery.md` bảng "đang có theo nguồn" | ghi rõ Nom Foundation 13, NLV 1, BULAC 8, Temple 2, "PDF/tư liệu nhận qua thầy ~6" |
| **S5** | `data/05_ops/khung_run/<cuốn>/khung/*.json` và `cap_cau.csv` | "chữ có khung" = tổng phần tử `chu`; "thiếu" = tổng trường `thieu`; trang có khung = tệp có ≥ 1 ô |
| **S6** | VPS `vps-caohoc`, container `family-tree-backend`: `/app/data/doi_chieu/<nhóm>/<cuốn>/` | số ảnh trong thư mục; `soat_nhap.json` → độ dài `da_soat` (số trang đã bấm soát) |
| **S7** | VPS MySQL bảng `user_scans` (chỉ `SELECT`) | ánh xạ `scan_id` → `doc_id`, `ma_dinh_danh` |
| **S8** | `data/03_derived/han_full_v1/manifest.csv`, `report.json` | bộ nhãn NER chữ Hán (nhãn máy Gemini): trang và chữ Hán theo `scan_id` |
| **S9** | `data/00_raw/du_lieu_han_nom_moi/<lô>/inventory.md`, `thong_ke.md`; `data/INCOMING.md` | ngày nhận lô, đường dẫn chép |

Mức tin cậy về **nguồn gốc**: **cao** = có bằng chứng trực tiếp (tệp nằm trong thư mục `dulieu-thay-cho` của thầy, hoặc ảnh mang mã kho số công khai); **vừa** = suy ra từ cùng lô/cùng cách đặt tên hoặc tài liệu dự án ghi lại; **chưa rõ** = không tìm được ghi chép.

Cách hiểu "dữ liệu của anh Lâm ban đầu": em xếp vào nhóm này những cuốn **anh tự tải từ thư viện số công khai** (Nom Foundation/NLV, BULAC trên archive.org, Temple University). Bằng chứng: script tải `crawl-han-nom-tools/lib.nomfoundation.org/download_nom_images.py` và S4. Nếu anh muốn hiểu "ban đầu" theo nghĩa khác (ví dụ tư liệu gia đình), anh báo em sắp lại.

---

## 1. Nhóm A: anh Lâm tự thu thập từ kho số công khai

### A1. Nom Foundation (Thư viện Quốc gia, `lib.nomfoundation.org`) — tin cậy cao

Nguồn gốc: `source=nomfoundation` (S2); tải bằng script của anh. Ảnh: `data/00_raw/hannom/nomfoundation/volumes/<id>/pages`.

| doc_id | Tên | Mã F (`ma_dinh_danh`) | Trang (S1) | Trang OCR | Chữ Hán OCR | Cặp Hán–Việt | Nhãn NER Hán máy (trang, S8) | Nhóm trên web (S6) |
|---|---|---|--:|--:|--:|--:|--:|---|
| nom-84 | Bạch Vân Am cư sĩ Nguyễn Văn Đạt phả ký | — | 47 | 47 | 23.445 | 1.228 | 47 | Phúc |
| nom-147 | Chu tộc gia phả | — | 58 | 58 | 13.843 | 1.010 | 57 | Minh |
| nom-207 | Đoàn tộc phả | — | 85 | 85 | 26.445 | 1.775 | 84 | Minh |
| nom-208 | Đông Trù Đoàn tộc phả | F-B-DO-DongTru-007-1845 | 79 | 79 | 23.774 | 1.587 | 77 | Phúc |
| nom-308 | Nguyễn Đường phả kí (bản Hán) | — | 20 | 20 | 4.322 | 261 | — | Phúc |
| nom-309 | Nguyễn Đường phả kí (bản **chữ Nôm**) | — | 33 | 33 | 9.706 | 537 | — | Phúc |
| nom-429 | Thuỵ Ứng gia phả | F-B-NG-ThuyUng-005-1912 | 9 | 9 | 1.217 | 106 | 7 | Minh |
| nom-557 | Thống Hội đại tộc thạch phả | — | 55 | 55 | 25.532 | 2.065 | 54 | Khôi |
| nom-563 | Trạng nguyên Hu Liêu tiên sinh gia phả | F-B-NG-BoiKhe-008-1496 | 44 | 44 | 6.018 | 560 | 44 | Phúc |
| nom-595 | Tả Thanh Oai Ngô tộc tổ mộ | — | 76 | 76 | 15.512 | 1.147 | — | Minh |
| nom-716 | Chu tộc hậu kỵ | — | 37 | 37 | 5.793 | 1.218 | — | Phúc |
| nom-833 | Mộ trạch Lê thị gia phả sự tích ký | — | 60 | 60 | 15.481 | 858 | 59 | Khôi |
| nom-854 | Nguyễn đường phả ký | F-M-NG-TayTuu-009-1844 | 40 | 40 | 8.734 | 735 | 39 | Phúc |
| nom-855 | Nguyễn tộc gia phả | F-A-NG-TrungTu-006-1843 | 100 | 100 | 29.631 | 2.012 | 100 | Trí |
| nom-865 | Phả ký miếu mộ | — | 21 | 21 | 3.255 | 273 | 19 | Trí |
| nom-1158 | Giang Thị gia phả | F-L-GI-MongPhu-010-1848 | 55 | 55 | 9.282 | 1.070 | 54 | Minh |
| nom-1255 | Chu tộc gia phả | F-L-CH-NongKhe-004-1911 | 6 | 6 | 610 | 57 | 6 | Trí |
| nom-1256 | Lê tộc đại tông gia phả | — | 30 | 30 | 4.522 | 320 | 28 | Phúc |
| **Cộng 18 cuốn** | | 7 cuốn có mã F | **855** | **855** | **227.122** | **16.819** | **675** | |

Ngoài bảng: **nom-130** Việt sử kính (42 trang nguồn, S2/DATA_INVENTORY) — có chữ Hán nhưng **không phải gia phả**, chưa có bản ghi trong S1.

### A2. Các kho số công khai khác — tin cậy cao về kho, vừa–cao về việc anh tự tải

| doc_id | Tên | Kho gốc | Trang | Trang OCR | Chữ Hán OCR | Cặp | NER máy | Web |
|---|---|---|--:|--:|--:|--:|--:|---|
| nlv-1042 | Đỗ tộc gia phả | NLV (hannom.nlv.gov.vn) | 14 | 14 | 2.897 | 223 | — | Minh |
| nguyen-khoa-q1 | Nguyễn Khoa thế phổ q.1 | Temple University | 94 | 94 | 14.051 | 2.270 | — | Minh |
| nguyen-khoa-q2 | Nguyễn Khoa thế phổ q.2 | Temple University | 105 | 105 | 14.964 | 2.429 | — | Khôi |
| hxh-105 | Gia phả các dòng họ (Hoàng Xuân Hãn sưu tập) | BULAC/archive.org | 181 | 136 | 28.214 | 2.200 | — | Trí |
| hxh-129 | Yên Lãng thượng thư công gia phả | BULAC | 23 | 22 | 1.674 | 152 | 9 | Minh |
| hxh-13 | Đoàn thị thực lục | BULAC | 28 | 28 | 5.577 | 286 | — | Phúc |
| hxh-16 | Ngô gia thế phả | BULAC | 58 | 48 | 8.821 | 1.160 | — | Khôi |
| hxh-73 | Đặng gia thế phả | BULAC | 47 | 45 | 3.309 | 880 | — | Phúc |
| hxh-119 | Đỗ tướng công niên phả, họ Phan… | BULAC | 50 | 41 | 10.880 | 800 | — | chưa giao |
| hxh-76 | Gia phả họ Nguyễn xã Vy Viễn (vở chép Quốc ngữ) | BULAC | 53 | 0 | 0 | 0 | — | chưa giao |
| pham-kinh-vy | Phạm Kinh Vỹ niên phả (范經偉年譜) | BULAC (ảnh in nhãn "ARC HOANG 49") | 23 | 23 | 4.027 | 193 | — | chua-giao (lab) |
| **Cộng 11 cuốn** | | | **676** | **556** | **94.414** | **10.593** | **9** | |

Nguồn kho: trường `nguon.duong_dan_goc` (S1: `bulac/ARC.HOANG.*`, `temple_nom/*`, `nlv_veridian/*`), S4. Riêng pham-kinh-vy: một trang OCR ra đúng chữ "ARC HOANG 49" (S1), khớp mục `ARC.HOANG.49` ở `docs/planning/hannom_gia_pha_source_hunt_plan.md`.

**Cộng nhóm A: 29 cuốn, 1.531 trang, 1.411 trang đã OCR, 321.536 chữ Hán, 27.412 cặp Hán–Việt** (S1). Thêm nom-130 (42 trang, không phải gia phả).

---

## 2. Nhóm B: thầy giao/cho

Bằng chứng chính: thư mục gốc trên máy Windows tên `dulieu-thay-cho\data-caohoc` (S3), gồm `Family_Han`, `Family_HánViệt`, `Family_NômViệt`, `Family_Việt`. S4 cũng ghi "PDF/tư liệu nhận qua thầy (tông phả Mai, Là, Trần; Phan gia công phả; docx dịch…)".

### B1. Đã đưa vào xử lý

| doc_id | Tên | Lô nhận (S9) | Tin cậy nguồn | Loại | Trang | Trang OCR | Chữ Hán OCR | Cặp | Khung ô chữ (S5) | Soát trên web (S6) | NER máy (S8) | Web |
|---|---|---|---|---|--:|--:|--:|--:|---|---|--:|---|
| pdf-1000-mai | Mai thị tông phả, tập 1 | 13/8 | vừa (cùng lô; **không** có trên Windows, S3) | PDF scan Hán | 131 | 131 | 21.974 | 3.486 | — | — | 128 | Trí |
| pdf-1001-la | Là thị tông phả, tập 1 | 13/8 | cao (MD5 khớp, S3) | PDF scan Hán | 118 | 118 | 9.931 | 1.342 | — | — | 105 | Minh |
| pdf-1005-tran | Trần thị tông phả, tập 1 | 13/8 | cao (MD5 khớp, S3) | PDF scan Hán | 233 | 233 | 19.325 | 2.342 | — | — | 152 | Khôi |
| tq-347 | Ngạc thị tông phả | 04/11 | cao (`Family_Han` #1) | PDF scan Hán | 12 | 11 | 2.034 | 137 | chưa có | 11 trang | — | chua-giao |
| tq-588 | Đặng thị tông phả, tập 10 | 04/11 | cao (#5) | PDF scan Hán | 45 | 41 | 7.123 | 447 | 39 tr · 3.345 chữ có khung · 3.778 thiếu | 41 trang | — | chua-giao |
| tq-678 | Trâu thị tông phả | 04/11 | cao (#12) | PDF scan Hán | 84 | 83 | 30.770 | 4.971 | 83 tr · 20.054 · 10.699 thiếu | 0 | — | chua-giao |
| tq-693 | Kỳ Dương Phạm thị ngũ tu tông phả (693) | 04/11 | cao (#14) | PDF scan Hán | 86 | 85 | 29.823 | 2.428 | 85 tr · 25.626 · 4.195 thiếu | 0 | — | chua-giao |
| tq-696 | Kỳ Dương Phạm thị ngũ tu tông phả (696) | 04/11 | cao (#15) | PDF scan Hán | 82 | 81 | 28.540 | 2.336 | 79 tr · 24.907 · 3.629 thiếu | 0 | — | chua-giao |
| tq-859 | Đỗ thị tông phả, tập 4 | 04/11 | cao (#26) | PDF scan Hán | 127 | 125 | 19.872 | 2.176 | 125 tr · 13.612 · 6.260 thiếu | 36 trang | — | chua-giao |
| tq-950 | Hội tu Doãn thị tông phả, tập 2 | 04/11 | cao (#35) | PDF scan Hán | 105 | 103 | 29.392 | 1.753 | 103 tr · 28.089 · 1.303 thiếu | 103 trang | — | chua-giao |
| tq-978 | Cừu thị tông phả, tập 8 | 04/11 | cao (#37) | PDF scan Hán | 41 | 38 | 1.453 | 164 | 38 tr · 739 · 714 thiếu | 38 trang | — | chua-giao |
| tq-1035 | Hồ thị tông phả, tập 6 | 04/11 | cao (#43) | PDF scan Hán | 121 | 119 | 6.249 | 1.997 | 118 tr · 5.590 · 659 thiếu | 0 | — | chua-giao |
| pdf-phan-gia-cong-pha | Phan gia công phả (F-B-PN-GiaThien-001-1930) | 31/8 | vừa (S4) | PDF: dịch Việt + bản Hán chụp | 86 | 85 | 17.455 | 1.283 | — | — | 79 | Phúc |
| docx-nguyen-van | Gia phả Nguyễn Văn (F-C-NG-HoiSon-003-1975) | 24/8 | vừa (cùng lô với docx-tran-200; S4) | DOCX: Hán + phiên âm + dịch | 1 tệp | 1 | 2.629 | 412 | — | — | — | Minh |
| docx-tran-200 | Gia phả họ Trần (Thanh Thủy Thượng, Huế) | 24/8 | cao (cùng byte, S3 #63/#96) | DOCX dịch Việt | 0 | 0 | 0 | 0 | — | — | — | Trí |
| docx-pham-1876 | Gia phả + Phó ý họ Phạm | 24/8 | vừa (cùng lô) | DOCX dịch Việt | 0 | 0 | 0 | 0 | — | — | — | chưa giao |

Chú thích:
- "Lô 04/11" của tq-*: ngày trong `provenance.ngay` (S1); mỗi cuốn có `drive_file_id`, tệp gốc `data/00_raw/du_lieu_han_nom_moi/tq-*/goc.pdf`. Tên trong S3 giữ số đầu tệp (347, 588, …) trùng với hậu tố `tq-`.
- OCR các cuốn tq-*: **một nguồn** (`gemini_web_tool`), chưa vote; tq-347 có thêm `claude_doc_anh` (S1).
- Ở cột khung: "chữ có khung" + "thiếu" = chữ Hán OCR của cuốn (ví dụ tq-588: 3.345 + 3.778 = 7.123), nên hai nguồn S1 và S5 khớp nhau.
- "Soát trên web" là số trang trong `da_soat` của `soat_nhap.json` (S6), sửa lần cuối 08/11; chưa biết ai bấm.

**Cộng B1: 16 cuốn, 1.272 trang, 1.254 trang đã OCR, 226.570 chữ Hán, 25.274 cặp** (S1). Trong đó 9 tông phổ tq-*: 703 trang, 155.256 chữ Hán, 16.409 cặp.

### B2. Thầy cho nhưng chưa xử lý (chỉ có ở máy Windows, theo S3)

| Phần | Số tệp | Trang | Ghi chú |
|---|--:|--:|---|
| Tông phổ Trung Quốc `Family_Han` còn lại | 35 PDF | 5.433 | 44 PDF mới có 6.136 trang (S3 §2), trừ 9 cuốn tq-* đã làm (703 trang) |
| `Family_Han` tệp rỗng 0 byte | 13 | 0 | phải tải lại (S3 phát hiện 1) |
| Hoàng tộc lược biên (`Family_HánViệt`) | 1 PDF | ~42 (chưa đếm được) | trên web đã có thư mục `ha-dang-khoi/hoang-toc-luoc-bien` nhưng 0 ảnh (S6) |
| Bộ ảnh `A.Phuong` | 25 ảnh + 1 PDF 1 trang | 26 | trang chọn lọc; có thể là bản gốc Hán của docx-tran-200 (S3, chưa kiểm) |
| 3 PDF Nom Foundation trùng nhan đề với nom-716 / nom-147 / nom-865 | 3 | 40 + 61 + 24 | bản PDF thầy cho; ảnh trong repo là bản anh tải (nhóm A), nên không đếm hai lần |

### B3. Thầy cho, có ít hoặc không có chữ Hán (để anh biết, không cộng vào tổng Hán)

| doc_id | Tên | Ghi chú |
|---|---|---|
| nguyen-ke-han-nom | Kế ước Nguyễn Kế (lô 25/8 "Hương") | 15 trang **có chữ Hán**, nhưng là kế ước, **không phải gia phả**; đã Paddle (S2) |
| nguyen-ke-gia-pha | Nguyễn Kế gia phả | 53 ảnh Quốc ngữ viết tay (S2) |
| pdf-nguyen-phuc-the-pha | Nguyễn Phúc tộc thế phả | 477 trang Quốc ngữ in 1995 (S2, S3 #95) |

---

## 3. Nhóm C: chưa xác định được nguồn

| doc_id / thư mục | Tên | Loại | Trang | Trang OCR | Chữ Hán OCR | Cặp | Tình trạng | Vì sao chưa rõ |
|---|---|---|--:|--:|--:|--:|---|---|
| gpc-dang-1928 | Gia phả chí họ Đặng, Bảo Đại 1928 (F-D-DA-KimDoi-002-1928) | ảnh scan Hán | 17 | 17 | 1.092 | 81 | OCR + dịch từ 17/08; NER máy 14 trang (S8); web: Minh | `source=local_scan` (S2), không thấy ghi người đưa; không có trong thư mục của thầy (S3) |
| giang-thi-gia-pha | Giang thị gia phả (江氏家譜) | ảnh chụp, dấu Viện Nghiên cứu Hán Nôm | 56 | 55 | 9.269 | 676 | OCR một nguồn Gemini web; khung 55 trang · 7.533 chữ có khung · 1.736 thiếu (S5); chưa soát (S6) | chép từ ổ `/Volumes/Data_2/cao_hoc/data-giapha/22-11-2026/1/` (S9); không ghi ai gửi |
| `../gia-pha-anh-quyen/` (ngoài repo) | Tư liệu "anh Quyền" | 28 ảnh | 28 | ? | ? | — | OCR Kim Hán Nôm + dịch nháp 19/10 (`gia-pha-anh-quyen-ket-qua/KET_QUA.md`); phần lớn là văn khế ruộng, không phải gia phả | không có ghi chép nguồn trong repo |
| `../gia-pha-ho-bui/` (ngoài repo) | Phả đồ họ Bùi (裴) | 3 ảnh = 2 trang | 2 | — | — | — | Claude đọc tay, chưa người duyệt; ảnh đã lên web (`user_scans` id 35, S7) | không có ghi chép nguồn |

**Cộng nhóm C (chỉ hai cuốn trong kho S1): 73 trang, 72 trang OCR, 10.361 chữ Hán, 757 cặp.**

---

## 4. Bảng tổng hợp theo nguồn (tư liệu gia phả Hán Nôm đã vào kho S1)

Kho S1 có 50 bản ghi. Bảng dưới bỏ 3 bản chỉ có Quốc ngữ (giaphatphcm-080-ha-ngoc, nguyen-ke-gia-pha, pdf-nguyen-phuc-the-pha), còn 47. Trong 47 bản này vẫn có 3 bản chưa có chữ Hán nào trong kho: hxh-76 (vở chép, chưa OCR), docx-tran-200 và docx-pham-1876 (bản dịch). Chúng vẫn được tính vào số cuốn nhưng cộng 0 chữ.

| Nguồn | Số cuốn | Trang | Trang đã OCR | Chữ Hán OCR | Cặp Hán–Việt (máy) | Có mã F | Có khung ô chữ | Đã soát trên web (trang) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| A. Anh Lâm tự thu thập (kho số công khai) | 29 | 1.531 | 1.411 | 321.536 | 27.412 | 7 | 1 (pham-kinh-vy) | 23 |
| B. Thầy giao/cho (đã xử lý) | 16 | 1.272 | 1.254 | 226.570 | 25.274 | 2 | 8 (tq-*) | 229 |
| C. Chưa rõ nguồn | 2 | 73 | 72 | 10.361 | 757 | 1 | 1 (giang) | 0 |
| **Tổng** | **47** | **2.876** | **2.737** | **558.467** | **53.443** | **10** | **10** | **252** |

Nguồn từng cột: số cuốn, trang, OCR, chữ Hán, cặp = S1; mã F = S1/S7 (10 mã, đều `ma_dinh_danh_nguon=catalogue`); khung = S5; đã soát = S6 (pham-kinh-vy 23; tq-347 11 + tq-588 41 + tq-859 36 + tq-950 103 + tq-978 38 = 229).

Phần **chưa xử lý** (không có trong tổng trên): thầy cho thêm 35 PDF tông phổ Trung Quốc (5.433 trang), Hoàng tộc lược biên (~42 trang), bộ A.Phuong (26 ảnh), 13 tệp rỗng (S3); anh tự có nom-130 (42 trang, không phải gia phả); chưa rõ nguồn: 28 ảnh anh Quyền và 2 trang họ Bùi.

### Gán nhãn

| Bộ nhãn | Nội dung | Nguồn của văn bản | Người soát? |
|---|---|---|---|
| NER chữ Hán `han_full_v1` (S8) | 20 cuốn, 1.162 trang, 261.252 chữ Hán | A: 15 cuốn (14 Nom Foundation + hxh-129; xem cột "NER máy") · B: 4 cuốn (pdf-1000/1001/1005, Phan gia công phả) · C: gpc-dang-1928 | **Không**. Toàn bộ là nhãn máy Gemini; `han_test_v1/reviewed/` chưa có |
| `gold_labels` (25 cây người + 114 cây bán tự động) | Phả ký **Quốc ngữ** crawl từ vietnamgiapha.com | anh tự crawl | 25 cây có người soát |

`gold_labels` không có chữ Hán nên không thuộc bảng thống kê Hán Nôm; em ghi ở đây để anh khỏi tìm.

Ánh xạ `scan_id` → cuốn (S7): 1 nom-1158, 2 nom-1255, 3 nom-1256, 4 nom-147, 5 nom-207, 6 nom-208, 7 nom-429, 8 nom-557, 9 nom-563, 10 nom-833, 11 nom-84, 12 nom-854, 14 nom-865, 15 pdf-1000-mai, 16 pdf-1001-la, 17 pdf-1005-tran, 19 gpc-dang-1928, 20 pdf-phan-gia-cong-pha, 21 hxh-129, 22 nom-855. Điều này **xác nhận** suy luận 15/16/17 = Mai/Là/Trần trong S3.

---

## 5. Điều cần anh để ý

1. **giang-thi-gia-pha có thể trùng nội dung với nom-1158** (tin cậy vừa–cao). Cả hai cùng tên 江氏家譜, và OCR của cả hai đều có bài 江族祠堂記, câu đề 江貴公, niên hiệu 紹治 (S1). Có thể đây là hai bản chụp (NLV và Viện Hán Nôm) của cùng một cuốn. Em chưa so ảnh. Nếu đúng là trùng thì nhóm C chỉ còn gpc-dang-1928 và khi chia fold phải xếp hai bản vào cùng một nhóm.
2. **nom-309 là bản chữ Nôm**, nằm ngoài phạm vi Hán–Việt theo ý thầy, nhưng đang giao cho Phúc (S6). Em vẫn đếm vào nhóm A vì có chữ Nôm.
3. **pdf-1000-mai** không có trong thư mục thầy trên Windows (S3), nên nguồn chỉ ở mức "vừa".
4. **nom-855** có hai dòng trong `user_scans` (id 13 đã xoá mềm, id 22 còn dùng) (S7). Không ảnh hưởng số đếm ở đây.
5. Các tông phổ tq-* chỉ có một nguồn OCR (Gemini), cả 9 cuốn chưa vote. Vì vậy số chữ Hán của nhóm B có độ chắc thấp hơn các cuốn Nom Foundation đã vote 3–5 engine.
6. Chưa biết: ai đưa gpc-dang-1928, giang-thi-gia-pha, tư liệu anh Quyền và họ Bùi; Hoàng tộc lược biên có đúng ~42 trang không.

## 6. Cách chạy lại các số chính

```bash
# S1: đếm theo kho bản ghi (chỉ đọc)
cd ../hannom-bilingual-dataset/data && python3 - <<'EOF'
import json,glob
han=lambda s: sum(1 for c in s if '\u3400'<=c<='\u9fff' or '\uf900'<=c<='\ufaff' or 0x20000<=ord(c)<=0x323af)
for f in sorted(glob.glob('*/*.json')):
    d=json.load(open(f)); P=d.get('pages') or []
    print(f, len(P), sum(han((p.get('l1_ocr') or {}).get('voted_text') or '') for p in P), sum(len(p.get('pairs') or []) for p in P))
EOF
```

S5: đọc `data/05_ops/khung_run/<cuốn>/khung/*.json`, cộng `len(chu)` và `thieu`. S6: `ssh vps-caohoc 'docker exec family-tree-backend ls /app/data/doi_chieu/<nhóm>'`.
