# Kiểm kê dữ liệu gốc trên máy Windows — đối chiếu với repo

> Ngày: 25/10/2026 · Phương pháp: **chỉ đọc**. Một script Python nhỏ chạy tạm trên máy Windows (đã xoá sau khi chạy) đọc
> metadata: tên, kích thước, ngày sửa, MD5 (PDF), số trang PDF (đếm đối tượng `/Type /Page`), kích thước ảnh JPG/PNG,
> số đoạn/ký tự DOCX. **Không** chép PDF/ảnh về Mac, **không** sửa/xoá/di chuyển file dữ liệu, **không** gọi dịch vụ tốn tiền.
> Thư mục gốc (trên Windows): `D:\cao-hoc\dulieu-thay-cho\data-caohoc\data-caohoc`.
> Đối chiếu với `data/` của checkout chính (gitignored): so MD5 (PDF), so kích thước byte (mọi file > 50 KB trong `data/`,
> 13.579 file), so nhan đề với `00_raw/hannom/books_catalog.json` (31 mục) và `03_derived/han_full_v1/` (20 sách NER Hán).

Quy ước: **[F]** fact (đo/đếm trực tiếp) · **[S]** suy luận · **[?]** không chắc / chưa kiểm.

## 1. Tóm tắt

| Thư mục | File | Đã có trong repo | Không chắc | Mới | Rỗng 0 byte |
|---|--:|--:|--:|--:|--:|
| `Family_Han` | 59 | 2 | 0 | **44** | 13 |
| `Family_HánViệt` | 34 | 5 | 2 | **27** | 0 |
| `Family_NômViệt` | 1 | 0 | 1 | 0 | 0 |
| `Family_Việt` | 2 | 2 | 0 | 0 | 0 |
| **Tổng** | **96** | **9** | **3** | **71** | **13** |

Theo loại file [F]: 65 PDF, 27 JPG, 2 PNG, 2 DOCX (+14 thư mục). Ngày sửa của mọi file là 23–24/10/2026 (ngày chép sang máy, không phải ngày gốc).

**Phát hiện chính**

1. [F] **13/59 PDF trong `Family_Han` là file rỗng 0 byte** (MD5 `d41d8cd9…`): 429, 500, 562, 652, 680, 962, 1349, 1743, 1776, 1937, 2609, 3776, 3806. Nhiều khả năng tải dở [S]; không dùng được nếu chưa tải lại. Vì vậy tổng ~1.984 MB ở kiểm kê sơ bộ thật ra nằm trong 46 file.
2. [F] Chỉ **2 PDF `Family_Han` đã có trong repo**: `1001` (La thị, tập 1) và `1005` (Trần thị, tập 1) — MD5 khớp với `00_raw/du_lieu_han_nom_moi/13_8_2026/`. Cuốn `1000` (Mai thị) có trong repo nhưng **không** có trên máy Windows.
3. [S, tin cậy vừa–cao] 3 cuốn PDF này là `scan_id` 15 (Mai, chữ 梅 + niên hiệu 乾隆), 16 (La, chữ 羅) và 17 (Trần, trang đầu là `陳氏族譜序`) trong `han_full_v1`, tức nằm trong 20 sách NER Hán. Bằng chứng: đếm họ phổ biến trong văn bản theo `scan_id`, cộng số trang khớp gần đúng (128/131, 105/118, 152/233 trang sau khi lọc `min_han=30`). Không có bảng `user_scans` ở local để xác nhận (DB thật ở VPS).
4. [F] **44 PDF `Family_Han` mới**, tổng **6.136 trang**, ~1.962 MB, thuộc **21 bộ tông phổ** (khác nhan đề). Không file nào trùng byte với `data/`, không bộ nào có trong `books_catalog.json`.
5. [F] Mọi PDF `Family_Han` **không có font** (chỉ ảnh scan) → bắt buộc OCR trước khi gán nhãn.
6. [S, tin cậy cao] `Family_Han` là **tông phổ Trung Quốc** (họ chữ giản thể `宗谱`, địa danh 旌义, 湟中, 蘄陽, 休寧, 祁門; số đầu tên file giống mã của một kho số hoá). Khác miền với gia phả Việt Nam (niên hiệu nhà Thanh, địa danh Trung Quốc). Có thể giúp PER_NAME/GENERATION, nhưng LOC/DATE sẽ lệch miền.
7. [F] Tư liệu **Việt Nam mới thật sự**: `Hoang Toc Luoc Bien.pdf` (BnF, iText 2023; không đếm được số trang vì cây trang bị nén, 42 ảnh nhúng → ước ~42 trang [?]) và bộ ảnh `A.Phuong` (23 JPG + 2 PNG + 1 PDF 1 trang "GP họ Tăng tr8").
8. [F/S] 3 PDF Nom Foundation (`周族后忌`, `朱族家譜`, `譜記廟墓`) **cùng nhan đề** với `nom-716`, `nom-147`, `nom-865` trong repo nhưng khác định dạng (repo giữ ảnh JPG) → "không chắc". `nom-147`, `nom-865` đã OCR; `nom-716` (Chu tộc hậu kỵ) **chưa OCR** (thư mục chỉ có 37 JPG + 2 JSON).

## 2. Số cuốn mới theo loại

| Loại | Số file mới | Số bộ/cuốn | Trang | Ghi chú |
|---|--:|--:|--:|---|
| Tông phổ Trung Quốc (PDF scan, `Family_Han`) | 44 | 21 bộ | 6.136 | cùng bộ nhiều tập: 鄧 6, 陈 5, 程 4, 施 4, 罗 3, 任 3, 李 3, 范 2, 张 2; 12 bộ chỉ 1 tập |
| Gia phả Việt Nam chữ Hán, PDF (`Hoang Toc Luoc Bien`) | 1 | 1 | ~42 [?] | nguồn BnF; có font → có thể đã có lớp chữ [?] |
| Ảnh rời Việt Nam (`A.Phuong`) | 26 | 1–3 [?] | 26 ảnh/trang | tên ảnh rời số trang (Tr. 01, 08, 26…; 07, 16, 38…; trang 12, 33…) → chỉ là **trang chọn lọc**, không trọn cuốn |
| PDF Nom Foundation trùng nhan đề | — | 3 (không chắc) | 40 + 61 + 24 | `周族后忌` có thể coi là mới về OCR |
| Rỗng, cần tải lại | 13 | 13 | 0 | |

Ghi chú [S]: `A.Phuong` chứa cả `gia pha ho tran 200.docx` (trùng `docx-tran-200` của repo) → bộ ảnh có thể là bản gốc chữ Hán của gia phả họ Trần 200 đã có bản dịch. Nếu đúng, đây là cặp **ảnh gốc + bản dịch người làm** — hiếm và quý cho soát RE. Chưa mở ảnh để kiểm [?].

## 3. Đề xuất 8 cuốn nên OCR/gán nhãn tiếp

Tiêu chí: (a) chưa có trong repo; (b) **họ mới** so với 20 sách đã dùng → thêm nhóm sách độc lập cho CV theo sách, tránh rò tên giữa các tập cùng họ (La/Trần đã có tập 1 trong train); (c) số trang vừa phải để kiểm soát chi phí OCR (Kim Hán Nôm = R3, phải hỏi trước); (d) ưu tiên tư liệu Việt Nam vì đúng miền mục tiêu.

| Ưu tiên | Cuốn | Trang | Lý do |
|--:|---|--:|---|
| 1 | `周族后忌` Chu tộc hậu kỵ (`Family_HánViệt`; = `nom-716`?) | 40 | Việt Nam, ảnh đã có ở repo nhưng **chưa OCR**; sổ hậu kỵ giàu PER_NAME + DATE. Không cần chép gì từ Windows |
| 2 | `Hoang Toc Luoc Bien.pdf` (Hoàng tộc lược biên) | ~42 [?] | Việt Nam, gia phả hoàng tộc nhà Nguyễn, nhiều quan hệ cha–con → hợp cho RE Hán. Cần đếm lại số trang và kiểm có lớp chữ không |
| 3 | Bộ ảnh `A.Phuong` (25 ảnh chữ Hán + `GP ho Tang tr8.pdf`) | 26 | Việt Nam; nếu đúng là bản gốc của `docx-tran-200` thì có bản dịch người để soát nhãn [?]. Cần anh Lâm/thầy xác nhận nguồn |
| 4 | `1011.龚氏宗谱` tập 1 (Củng thị) | 89 | họ mới, tập 1 (thường có tựa, phàm lệ, thế hệ đầu) |
| 5 | `1035.胡氏宗谱` tập 6 (Hồ thị) | 121 | họ mới, độ dài vừa |
| 6 | `859.杜氏宗谱` tập 4 (Đỗ thị) | 127 | họ mới; họ Đỗ cũng phổ biến ở Việt Nam → tên gần miền hơn [S] |
| 7 | `950.會修尹氏宗譜` tập 2 (Doãn thị) | 105 | họ mới, chữ phồn thể (đa dạng hoá so với các bộ giản thể) |
| 8 | `588.鄧氏宗譜` tập 10 (Đặng thị) | 45 | họ mới, ngắn → thử nhanh quy trình OCR + gán nhãn; bộ có 6 tập nên mở rộng được về sau (để cả bộ ở cùng một fold) |

Tổng ≈ **595 trang** (3 Việt ~108 + 5 Trung 487), gần bằng một nửa 1.162 trang hiện có. Dự phòng: `678.鄒氏` (84 tr.), `978.仇氏` (41 tr.), `347.鄂氏` (12 tr.).

Không đề xuất: tập 3/4/6 họ La và tập 3/4 họ Trần (cùng họ với sách đã train → rò rỉ nếu chia fold sai; nếu dùng phải gộp chung nhóm với `scan_id` 16/17 [S]); các tập rất dài 886/893 `任氏` (317/341 tr.), 817 `张氏` (289 tr.) vì tốn OCR.

**Lưu ý khi dùng** [S]: tông phổ Trung Quốc lệch miền; nên báo F1 riêng theo miền (VN / TQ) và không để chúng lấn át tập test Việt Nam.

## 4. Còn chưa biết / việc tiếp theo

- [?] Xác nhận ánh xạ `scan_id` 15/16/17 ↔ Mai/La/Trần bằng bảng `user_scans` trên VPS.
- [?] Số trang thật của `Hoang Toc Luoc Bien.pdf` (cần thư viện PDF hoặc mở bằng tay); có lớp chữ OCR của BnF không.
- [?] `A.Phuong` có phải bản gốc của `docx-tran-200` không — cần xem vài ảnh (chép về Mac là việc phải hỏi trước).
- [?] Nguồn tải của 13 file rỗng để tải lại (mã số đầu tên file có thể tra ngược kho gốc).
- [?] Ba PDF Nom Foundation có đúng là cùng bản với ảnh JPG trong repo không (so số trang: 40 vs 37 ảnh, 61 vs 58 tờ, 24 vs 21 tờ — chênh ~3 trang, có thể là bìa/trang phụ).

## 5. Bảng 96 file

Số trang PDF đếm bằng đối tượng `/Type /Page` [F]; khớp với `books_catalog.json` ở 2 file kiểm được (118, 233). `?` = không đếm được.

| # | Thư mục | Tên file | Loại | Kích thước | Số trang | Đã có trong repo? | Bằng chứng |
|--:|---|---|---|--:|---|---|---|
| 1 | `Family_Han` | 347.鄂氏宗譜- - ngạc thị tông phả - .pdf | PDF | 1.2 MB | 12 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 2 | `Family_Han` | 429.吳氏宗譜五卷- - ngô thị tông phả ngũ quyển - .pdf | PDF | 0 B | 0 | **không dùng được** | file rỗng 0 byte (tải dở) |
| 3 | `Family_Han` | 500.泗水余氏會通世譜五卷外紀一卷- - tứ thuỷ dư thị hội thông thế phả ngũ quyển ngoại kỉ nhất quyển - .pdf | PDF | 0 B | 0 | **không dùng được** | file rỗng 0 byte (tải dở) |
| 4 | `Family_Han` | 562.漆林章氏宗譜六卷- - tất lâm chương thị tông phả lục quyển - .pdf | PDF | 0 B | 0 | **không dùng được** | file rỗng 0 byte (tải dở) |
| 5 | `Family_Han` | 588.Deng shi zong pu 鄧氏宗譜-第10册 - Deng shi zong pu đặng thị tông phả - Tập 10.pdf | PDF | 6.0 MB | 45 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 6 | `Family_Han` | 603.Deng shi zong pu 鄧氏宗譜-第25册 - Deng shi zong pu đặng thị tông phả - Tập 25.pdf | PDF | 4.7 MB | 35 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 7 | `Family_Han` | 607.Deng shi zong pu 鄧氏宗譜-第29册 - Deng shi zong pu đặng thị tông phả - Tập 29.pdf | PDF | 4.1 MB | 31 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 8 | `Family_Han` | 614.Deng shi zong pu 鄧氏宗譜-第36册 - Deng shi zong pu đặng thị tông phả - Tập 36.pdf | PDF | 3.8 MB | 29 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 9 | `Family_Han` | 616.Deng shi zong pu 鄧氏宗譜-第38册 - Deng shi zong pu đặng thị tông phả - Tập 38.pdf | PDF | 5.2 MB | 38 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 10 | `Family_Han` | 622.Deng shi zong pu 鄧氏宗譜-第44册 - Deng shi zong pu đặng thị tông phả - Tập 44.pdf | PDF | 3.1 MB | 24 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 11 | `Family_Han` | 652.新安詹氏統宗世譜十四卷- - tân an thiêm thị thống tông thế phả thập tứ quyển - .pdf | PDF | 0 B | 0 | **không dùng được** | file rỗng 0 byte (tải dở) |
| 12 | `Family_Han` | 678.鄒氏合族續修宗譜- - trâu thị hợp tộc tục tu tông phổ - .pdf | PDF | 9.7 MB | 84 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 13 | `Family_Han` | 680.梅溪汪氏宗譜十二卷- - mai khê uông thị tông phả thập nhị quyển - .pdf | PDF | 0 B | 0 | **không dùng được** | file rỗng 0 byte (tải dở) |
| 14 | `Family_Han` | 693.蘄陽范氏五修宗譜- - kỳ dương phạm thị ngũ tu tông phổ - .pdf | PDF | 12.8 MB | 86 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 15 | `Family_Han` | 696.蘄陽范氏五修宗譜- - kỳ dương phạm thị ngũ tu tông phổ - .pdf | PDF | 12.2 MB | 82 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 16 | `Family_Han` | 753.黄氏宗谱-第1册 - hoàng thị tông phổ - Tập 1.pdf | PDF | 58.0 MB | 152 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 17 | `Family_Han` | 765.罗氏宗谱-第3册 - là thị tông phổ - Tập 3.pdf | PDF | 15.0 MB | 81 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 18 | `Family_Han` | 766.罗氏宗谱-第4册 - là thị tông phổ - Tập 4.pdf | PDF | 14.4 MB | 78 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 19 | `Family_Han` | 768.罗氏宗谱-第6册 - là thị tông phổ - Tập 6.pdf | PDF | 7.5 MB | 41 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 20 | `Family_Han` | 817.张氏宗谱-第15册 - trương thị tông phổ - Tập 15.pdf | PDF | 110.9 MB | 289 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 21 | `Family_Han` | 830.张氏宗谱-第28册 - trương thị tông phổ - Tập 28.pdf | PDF | 62.2 MB | 157 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 22 | `Family_Han` | 840.程氏宗谱-第6册 - trình thị tông phổ - Tập 6.pdf | PDF | 30.4 MB | 114 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 23 | `Family_Han` | 843.程氏宗谱-第9册 - trình thị tông phổ - Tập 9.pdf | PDF | 67.9 MB | 256 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 24 | `Family_Han` | 850.程氏宗谱-第16册 - trình thị tông phổ - Tập 16.pdf | PDF | 67.4 MB | 230 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 25 | `Family_Han` | 853.程氏宗谱-第19册 - trình thị tông phổ - Tập 19.pdf | PDF | 57.7 MB | 212 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 26 | `Family_Han` | 859.杜氏宗谱-第4册 - đỗ thị tông phổ - Tập 4.pdf | PDF | 39.5 MB | 127 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 27 | `Family_Han` | 880.何氏宗谱-第21册 - hà thị tông phổ - Tập 21.pdf | PDF | 84.2 MB | 224 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 28 | `Family_Han` | 886.任氏宗谱-第1册 - nhậm thị tông phổ - Tập 1.pdf | PDF | 122.4 MB | 317 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 29 | `Family_Han` | 889.任氏宗谱-第4册 - nhậm thị tông phổ - Tập 4.pdf | PDF | 87.6 MB | 227 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 30 | `Family_Han` | 893.任氏宗谱-第8册 - nhậm thị tông phổ - Tập 8.pdf | PDF | 118.6 MB | 341 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 31 | `Family_Han` | 917.陈氏宗谱-第10册 - trần thị tông phổ - Tập 10.pdf | PDF | 46.1 MB | 120 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 32 | `Family_Han` | 925.陈氏宗谱-第18册 - trần thị tông phổ - Tập 18.pdf | PDF | 37.2 MB | 100 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 33 | `Family_Han` | 929.陈氏宗谱-第22册 - trần thị tông phổ - Tập 22.pdf | PDF | 57.4 MB | 148 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 34 | `Family_Han` | 942.许氏宗谱-第11册 - hổ thị tông phổ - Tập 11.pdf | PDF | 79.6 MB | 255 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 35 | `Family_Han` | 950.會修尹氏宗譜-第2册 - hội tu doãn thị tông phả - Tập 2.pdf | PDF | 33.1 MB | 105 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 36 | `Family_Han` | 962.祁門奇峰鄭氏本宗譜四卷- - kỳ môn cả phong trịnh thị vốn tông phổ tứ quyển - .pdf | PDF | 0 B | 0 | **không dùng được** | file rỗng 0 byte (tải dở) |
| 37 | `Family_Han` | 978.仇氏宗谱-第8册 - cừu thị tông phổ - Tập 8.pdf | PDF | 10.2 MB | 41 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 38 | `Family_Han` | 1001.罗氏宗谱-第1册 - là thị tông phổ - Tập 1.pdf | PDF | 44.7 MB | 118 | **có** | MD5 khớp `00_raw/du_lieu_han_nom_moi/13_8_2026/`; đã OCR + nằm trong 20 sách NER Hán (scan_id 16, suy luận) |
| 39 | `Family_Han` | 1005.陈氏宗谱-第1册 - trần thị tông phổ - Tập 1.pdf | PDF | 73.3 MB | 233 | **có** | MD5 khớp `00_raw/du_lieu_han_nom_moi/13_8_2026/`; đã OCR + nằm trong 20 sách NER Hán (scan_id 17, suy luận) |
| 40 | `Family_Han` | 1007.陈氏宗谱-第3册 - trần thị tông phổ - Tập 3.pdf | PDF | 51.8 MB | 163 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 41 | `Family_Han` | 1011.龚氏宗谱-第1册 - củng thị tông phổ - Tập 1.pdf | PDF | 63.3 MB | 89 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 42 | `Family_Han` | 1019.陈氏宗谱-第4册 - trần thị tông phổ - Tập 4.pdf | PDF | 28.5 MB | 84 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 43 | `Family_Han` | 1035.胡氏宗谱-第6册 - hồ thị tông phổ - Tập 6.pdf | PDF | 22.6 MB | 121 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 44 | `Family_Han` | 1037.李氏宗谱-第2册 - lý thị tông phổ - Tập 2.pdf | PDF | 69.0 MB | 239 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 45 | `Family_Han` | 1046.李氏宗谱-第11册 - lý thị tông phổ - Tập 11.pdf | PDF | 57.0 MB | 193 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 46 | `Family_Han` | 1056.李氏宗谱-第21册 - lý thị tông phổ - Tập 21.pdf | PDF | 75.6 MB | 253 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 47 | `Family_Han` | 1078.施氏宗谱-第5册 - thi thị tông phổ - Tập 5.pdf | PDF | 53.6 MB | 163 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 48 | `Family_Han` | 1081.施氏宗谱-第8册 - thi thị tông phổ - Tập 8.pdf | PDF | 48.4 MB | 153 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 49 | `Family_Han` | 1086.施氏宗谱-第13册 - thi thị tông phổ - Tập 13.pdf | PDF | 47.1 MB | 151 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 50 | `Family_Han` | 1088.施氏宗谱-第15册 - thi thị tông phổ - Tập 15.pdf | PDF | 52.3 MB | 167 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 51 | `Family_Han` | 1349.休寧流塘詹氏宗譜六卷- - hưu ninh lưu đường thiêm thị tông phả lục quyển - .pdf | PDF | 0 B | 0 | **không dùng được** | file rỗng 0 byte (tải dở) |
| 52 | `Family_Han` | 1743.童氏宗谱-第11册 - đồng thị tông phổ - Tập 11.pdf | PDF | 0 B | 0 | **không dùng được** | file rỗng 0 byte (tải dở) |
| 53 | `Family_Han` | 1776.馮氏宗譜十卷首一卷- - phùng thị tông phả thập quyển thủ nhất quyển - .pdf | PDF | 0 B | 0 | **không dùng được** | file rỗng 0 byte (tải dở) |
| 54 | `Family_Han` | 1937.休寧厚田吳氏重修宗譜六卷- - hưu ninh hậu điền ngô thị trùng tu tông phổ lục quyển - .pdf | PDF | 0 B | 0 | **không dùng được** | file rỗng 0 byte (tải dở) |
| 55 | `Family_Han` | 2609.南阳叶氏宗谱-第16册 - nam dương hiệp thị tông phổ - Tập 16.pdf | PDF | 0 B | 0 | **không dùng được** | file rỗng 0 byte (tải dở) |
| 56 | `Family_Han` | 3057.旌义包氏宗谱-第1册 - tinh nghĩa bao thị tông phổ - Tập 1.pdf | PDF | 122.3 MB | 239 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 57 | `Family_Han` | 3273.湟中侯氏世系宗谱-第2册 - hoàng trung hầu thị thế hệ tông phổ - Tập 2.pdf | PDF | 684 KB | 40 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 58 | `Family_Han` | 3776.江阳何氏宗谱-第8册 - giang dương hà thị tông phổ - Tập 8.pdf | PDF | 0 B | 0 | **không dùng được** | file rỗng 0 byte (tải dở) |
| 59 | `Family_Han` | 3806.重订徐氏宗谱-第1册 - trùng đính từ thị tông phổ - Tập 1.pdf | PDF | 0 B | 0 | **không dùng được** | file rỗng 0 byte (tải dở) |
| 60 | `Family_HánViệt` | Hoang Toc Luoc Bien.pdf | PDF | 8.9 MB | ? | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 61 | `Family_HánViệt` | [周族后忌] • [Chu tộc hậu kỵ].pdf | PDF | 2.6 MB | 40 | **không chắc** | cùng nhan đề với `nom-716` (37 ảnh JPG Nom Foundation, **chưa OCR**); PDF 40 tr., không trùng byte |
| 62 | `Family_HánViệt` | 朱族家譜 • Chu tộc gia phả.pdf | PDF | 5.7 MB | 61 | **không chắc** | cùng nhan đề với `nom-147` (58 tờ, đã OCR); không trùng byte |
| 63 | `Family_HánViệt\A.Phuong` | gia pha ho tran 200.docx | DOCX | 58 KB | 361 đoạn, 20390 ký tự | **có** | cùng tên + cùng 57.824 byte với `24_8_2026/` (`docx-tran-200`) |
| 64 | `Family_HánViệt\A.Phuong\bản gốc 1` | Tr. 01.JPG | JPG | 1.8 MB | 1 ảnh 1936×2592 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 65 | `Family_HánViệt\A.Phuong\bản gốc 1` | Tr. 08.JPG | JPG | 1.7 MB | 1 ảnh 1936×2592 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 66 | `Family_HánViệt\A.Phuong\bản gốc 1` | Tr. 09.JPG | JPG | 1.9 MB | 1 ảnh 1936×2592 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 67 | `Family_HánViệt\A.Phuong\bản gốc 1` | Tr. 26.JPG | JPG | 1.6 MB | 1 ảnh 1936×2592 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 68 | `Family_HánViệt\A.Phuong\bản gốc 1` | Tr. 28.JPG | JPG | 1.9 MB | 1 ảnh 1936×2592 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 69 | `Family_HánViệt\A.Phuong\bản gốc 1` | Tr. 30.JPG | JPG | 1.7 MB | 1 ảnh 1936×2592 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 70 | `Family_HánViệt\A.Phuong\bản gốc 1` | Tr.17a.JPG | JPG | 1.5 MB | 1 ảnh 1936×2592 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 71 | `Family_HánViệt\A.Phuong\chũ hán 1` | IMG_6440.PNG | PNG | 498 KB | 1 ảnh 1024×768 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 72 | `Family_HánViệt\A.Phuong\chũ hán 1` | IMG_6445.PNG | PNG | 473 KB | 1 ảnh 1024×768 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 73 | `Family_HánViệt\A.Phuong\chữ Hán gốc 1` | 07.jpg | JPG | 230 KB | 1 ảnh 956×1276 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 74 | `Family_HánViệt\A.Phuong\chữ Hán gốc 1` | 16.jpg | JPG | 203 KB | 1 ảnh 956×1276 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 75 | `Family_HánViệt\A.Phuong\chữ Hán gốc 1` | 38.jpg | JPG | 238 KB | 1 ảnh 961×1281 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 76 | `Family_HánViệt\A.Phuong\chữ Hán gốc 1` | 42.jpg | JPG | 219 KB | 1 ảnh 960×1280 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 77 | `Family_HánViệt\A.Phuong\chữ Hán gốc 1` | 44.jpg | JPG | 220 KB | 1 ảnh 956×1276 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 78 | `Family_HánViệt\A.Phuong\chữ Hán gốc 2` | 46.jpg | JPG | 1.6 MB | 1 ảnh 1299×2008 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 79 | `Family_HánViệt\A.Phuong\chữ Hán gốc 2` | 58.jpg | JPG | 1.5 MB | 1 ảnh 1299×2008 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 80 | `Family_HánViệt\A.Phuong\chữ Hán gốc 2` | 70.jpg | JPG | 1.3 MB | 1 ảnh 1299×2008 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 81 | `Family_HánViệt\A.Phuong\chữ Hán gốc 2` | 55a.jpg | JPG | 1.6 MB | 1 ảnh 1299×2008 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 82 | `Family_HánViệt\A.Phuong\chữ Hán gốc 2` | 65a.jpg | JPG | 1.9 MB | 1 ảnh 1299×2008 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 83 | `Family_HánViệt\A.Phuong\size nho` | trang 12.JPG | JPG | 4.5 MB | 1 ảnh 4032×3024 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 84 | `Family_HánViệt\A.Phuong\size nho` | trang 33.JPG | JPG | 4.6 MB | 1 ảnh 4032×3024 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 85 | `Family_HánViệt\A.Phuong\size nho` | trang 35.JPG | JPG | 4.4 MB | 1 ảnh 4032×3024 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 86 | `Family_HánViệt\A.Phuong\size nho` | trang 37.JPG | JPG | 3.5 MB | 1 ảnh 4032×3024 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 87 | `Family_HánViệt\A.Phuong\size nho` | trang 43.JPG | JPG | 3.4 MB | 1 ảnh 4032×3024 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 88 | `Family_HánViệt\A.Phuong\size nho` | trang 54.JPG | JPG | 3.7 MB | 1 ảnh 4032×3024 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 89 | `Family_HánViệt\A.Phuong\trang 7-24` | GP ho Tang tr8.pdf | PDF | 355 KB | 1 | **không** | không trùng kích thước byte với file nào trong `data/`; không có trong `books_catalog.json` |
| 90 | `Family_HánViệt\huong\Nguyễn Kế Hán Nôm` | IMG_2527.JPG | JPG | 275 KB | 1 ảnh 1280×960 | **có** | cùng kích thước byte với ảnh ở `25_8_2026/Hương/` (= `pages/11.jpg`, manifest ghi nguồn IMG_2527) |
| 91 | `Family_HánViệt\huong\Nguyễn Kế gia phả` | IMG_9637.JPG | JPG | 245 KB | 1 ảnh 956×1276 | **có** | cùng kích thước byte với ảnh ở `25_8_2026/Hương/` |
| 92 | `Family_HánViệt\huong\Nguyễn Kế gia phả` | IMG_9654(1).JPG | JPG | 256 KB | 1 ảnh 956×1276 | **có** | cùng kích thước byte với ảnh ở `25_8_2026/Hương/` |
| 93 | `Family_HánViệt\huong\Nguyễn Kế gia phả` | IMG_9668(1).JPG | JPG | 253 KB | 1 ảnh 956×1276 | **có** | cùng kích thước byte với ảnh ở `25_8_2026/Hương/` |
| 94 | `Family_NômViệt` | Phả ký miếu mộ • 譜記廟墓.pdf | PDF | 1.7 MB | 24 | **không chắc** | cùng nhan đề với `nom-865` (21 tờ, đã OCR); không trùng byte |
| 95 | `Family_Việt` | Nguyen_Phuc_Toc_The_Pha.pdf | PDF | 15.0 MB | 477 | **có** | MD5 khớp `28_8_2026/` (`pdf-nguyen-phuc-the-pha`, Quốc ngữ in) |
| 96 | `Family_Việt` | gia pha ho tran 200.docx | DOCX | 58 KB | 361 đoạn, 20390 ký tự | **có** | cùng tên + cùng 57.824 byte với `24_8_2026/` (`docx-tran-200`) |
