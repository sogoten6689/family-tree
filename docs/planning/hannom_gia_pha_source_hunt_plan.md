# Plan — Tìm thêm dữ liệu gia phả Hán Nôm

> **Ngày:** 2026-10-05 · **Cấp phiên:** L0 → L2 (đọc web, ghi file local, chạy script nhỏ).
> Chưa tải ảnh, chưa gọi Firecrawl, chưa commit.
> **Liên quan:** [firecrawl_genealogy_source_discovery_plan.md](./firecrawl_genealogy_source_discovery_plan.md),
> [nomfoundation_crawl_plan.md](./nomfoundation_crawl_plan.md), `data/00_raw/hannom/books_catalog.json`
> **File sinh ra (local, `data/` bị gitignore):** `data/05_ops/sources_discovery/hannom/kyoto_gcr6/`
> (`GCR_WP6.pdf`, `list_p67-73.txt`, `parse_gcr6.py`, `gcr6_catalogue.csv`)

---

## 0. Kết luận ngắn

1. **Các kho online công khai gần như đã khai thác hết.** Nom Foundation/NLV, archive.org/BULAC và danh mục Kyoto đã
   được rà lại hôm nay (§2). Mọi gia phả thật có ảnh ở các kho này **đều đã có trong repo**.
   Độ tin cậy: cao với Nom Foundation và archive.org, vừa với các kho còn lại.
2. **Kho lớn chưa có ảnh online:**
   - **Viện Nghiên cứu Hán Nôm:** khoảng 313 mục, tổng khoảng 29.900 trang. Đã có danh mục đủ số hiệu (§3).
   - **Huế:** đã số hoá 417.955 trang, gồm tư liệu của **923 dòng họ** (theo báo chí), nhưng chưa có cổng đọc công khai.
3. Vì vậy, muốn tăng corpus Hán Nôm đáng kể thì **phải xin qua tổ chức**, crawl thêm không đủ. Đây là giả thuyết H1,
   nay đã có bằng chứng ủng hộ, nhưng chưa bị loại trừ hết (§6).

## 1. Hiện trạng repo (fact)

- `books_catalog.json`: 42 mục (`nomfoundation` 19, `archive_org_bulac` 7, `local_scan` 3, `tong_pho_pdf` 3,
  `local_docx` 3, `temple_nom` 2, `sach_ly_thuyet` 2, các nguồn khác mỗi nguồn 1).
- `data/DATA_INVENTORY.md` (sinh 31/08) vẫn ghi **28 cuốn**, tức là **lỗi thời**. Cần chạy lại `build_corpus_inventory`.

## 2. Kết quả rà từng nguồn (05/10/2026)

| Nguồn | Cách rà | Kết quả | Mới so với repo |
|---|---|---|---|
| **Nom Foundation** `lib.nomfoundation.org` | Tải trang danh sách theo subject của 4 collection (1.479 volume) rồi lọc tiêu đề theo 譜/族/系/忌/phả | Tất cả gia phả thật (R.28, 951, 952, 217, 676, 1910, 1983, 2011–13, 2242, 5860, TN.146–147) đều **đã có** | **Gia phả: 0.** Liên quan (§4): ngọc phả v596, v985, v1136; linh phả v988; tiên phả v1147; sổ hậu kỵ c4/v1472 |
| **archive.org** | advancedsearch API, nhiều truy vấn | 7/7 gia phả `ARC.HOANG.*` (BULAC, bộ Hoàng Xuân Hãn) **đã có** | Liên quan: `ARC.HOANG.49` (Phạm Kinh Vỹ niên phả), `.83`/`.84` (Ngô gia văn phái). Sách tham khảo: *Sưu tập sổ bộ Hán Nôm Nam Bộ 1819–1918* |
| **Danh mục Kyoto GCR WP6** (Jo 2025) | Tải PDF công khai, parse 332 dòng | 12 mục NLV = 12 mục repo đã có. **313 mục ở Viện Hán Nôm (VNCHN): không có ảnh online** | Đây là danh sách mục tiêu để xin truy cập (§3) |
| **HUC** `search.huc.edu.vn` | Trình duyệt trong app | 123 kết quả, đều là sách in quốc ngữ (hướng dẫn viết gia phả, tộc phả in…) | Chỉ dùng làm tài liệu lý thuyết, **không** có ảnh Hán Nôm |
| **British Library** (EAP219 thư viện EFEO cũ, EAP104 bộ Durand) | Catalog BL: 家譜 / 世譜 / 族譜 / "gia phả" | 0 gia phả Việt. Trang tìm kiếm EAP đòi CAPTCHA, **không vượt** | Gần như 0 |
| **Temple Univ. Nôm** (CONTENTdm `p16002coll24`) | API và trình duyệt | Không truy cập được (API không trả JSON, điều hướng bị từ chối) | **Chưa biết.** Thử lại bằng tay |
| **Thư viện TT‑Huế + Thư viện KHTH TP.HCM** | Báo chí | 417.955 trang / 5.211 tài liệu / 923 dòng họ / 187 làng, quản lý bằng Emiclib; "phòng đọc online" trong kế hoạch 2026–2030 | **Tiềm năng lớn nhất**, nhưng phải xin |
| Quảng Trị, Nghệ An (số hoá cộng đồng) | Báo chí | Ảnh thường trả lại cho dòng họ | Phải xin qua thầy, sở hoặc dòng họ |

## 3. Danh mục Kyoto: bản đồ để xin truy cập

- **Nguồn:** 趙浩衍 (Jo Hoyeon), *Danh mục gia phả lưu trữ tại Viện Nghiên cứu Hán Nôm và Thư viện Quốc gia Việt Nam*,
  GCR Working Paper No. 6, Kyoto CSEAS, 03/2025. PDF: https://gcr.cseas.kyoto-u.ac.jp/wp-content/uploads/2025/05/GCR_WP6.pdf
  Bài phân tích kèm theo: Jo 2026, *Tōnan Ajia Kenkyū* 63(2), DOI `10.20495/tak.25006`.
- **`gcr6_catalogue.csv`:** 332 dòng, 317 số hiệu khác nhau. Có 240 mục ghi số trang, tổng 29.865 trang, trung vị 91 trang.
  Phân hạng bản: A 110 · D 74 · A+D 31 · O 21 · trống 96.
  (Ký hiệu A/D/O là phân hạng của tác giả. Phần chú giải in bằng chữ Nhật bị hỏng font nên **chưa giải nghĩa được**.)
- **Giới hạn:** chữ Hán trong PDF hỏng ToUnicode, nên cột `title_raw_garbled` không đọc được. Các cột số hiệu, số trang và năm
  thì tin được. Để khôi phục tiêu đề: render trang 67–73 thành ảnh rồi đọc, hoặc OCR (**không** dùng Kim Hán Nôm, vì tốn tiền).
- **Dùng cho luận văn:** chọn mẫu phân tầng (niên đại × vùng × tầng lớp đỗ đạt) để xin ảnh. Nhờ danh mục này, luận văn có thể
  lập luận rằng corpus đại diện cho tổng thể 332 gia phả đã được kiểm kê.

## 4. Dữ liệu liên quan (để Lâm lọc)

| Nhóm | Mục | Dùng cho |
|---|---|---|
| Gần gia phả (Hán Nôm, có ảnh) | Ngọc phả / thần phả trên Nom Foundation (5 volume), sổ hậu kỵ (v1472), niên phả `ARC.HOANG.49`, văn phái `.83`/`.84` | Mở rộng tập "văn bản phả hệ" hoặc làm hard negative |
| Gia phả chữ Hán (Trung Quốc) | Thư viện Thượng Hải: khoảng 2.500 bộ 家譜 toàn văn ảnh + 68.000 metadata (open data); FamilySearch *China Collection of Genealogies*; Genealogy‑MBW (华谱, 23.646 người họ Ngô) | Pretrain bố cục, benchmark cấu trúc cây; xem `chinese_genealogy_model_hunt_plan.md` |
| Gia phả Hàn Quốc | SKKU 韓国族譜史料 `jokbo.skku.edu` | Đối chứng |
| Trích xuất thông tin chữ Hán cổ | CHisIEC (14k thực thể, 8,6k quan hệ, 12 loại quan hệ); Chinese Literature NER/RE | Gợi ý schema quan hệ, transfer |
| OCR / dịch Hán Nôm | NomNaOCR (2.953 trang); bộ HCMUS (khoảng 200k trang, 750k cặp câu); PaddleOCRv5 fine‑tune (arXiv 2510.04003) | Lab OCR và dịch |
| Lý thuyết | Sách gia phả học ở HUC; Tạp chí *Tộc ước tại VNCHN* (VJOL) | Chương tổng quan |

## 5. Bước tiếp theo đề xuất

| Bước | Việc | R |
|---|---|---|
| T1 | Khôi phục tiêu đề Hán cho `gcr6_catalogue.csv` (render trang PDF rồi đọc/OCR local) | R2 |
| T2 | Chọn khoảng 30–50 mục mục tiêu từ CSV, phân tầng theo năm, vùng và hạng bản | R1 |
| T3 | Soạn thư nháp xin truy cập gửi Viện Hán Nôm và Thư viện TT‑Huế, kèm danh sách T2. **Lâm hoặc thầy gửi** | R0 soạn / R5 gửi |
| T4 | Tải 5 ngọc phả + 1 sổ hậu kỵ (Nom Foundation) và 3 mục `ARC.HOANG` liên quan, **nếu Lâm chọn** | R2 + xin phép tải |
| T5 | Thử lại kho Temple bằng tay trên trình duyệt | R0 |
| T6 | Chạy lại `build_corpus_inventory` cho khớp 42 mục | R2 |
| — | Firecrawl: không cần cho các bước trên | R3 |

## 6. Còn chưa biết

- Ý nghĩa của phân hạng A/D/O trong danh mục Kyoto (phần chú giải bị hỏng font).
- Kho Temple có gia phả không.
- Huế/Emiclib có cho truy cập từ xa không, và với điều kiện gì.
- Thầy có sẵn kênh làm việc với Viện Hán Nôm hoặc Thư viện Huế không. Cần hỏi ở buổi họp tuần.

## Nguồn

- Kyoto GCR WP6: https://gcr.cseas.kyoto-u.ac.jp/wp-content/uploads/2025/05/GCR_WP6.pdf · NDL https://ndlsearch.ndl.go.jp/books/R100000002-I034054834
- Jo 2026: https://doi.org/10.20495/tak.25006 · https://kyoto-seas.org/wp-content/uploads/2026/01/630202_Jo.pdf
- Nom Foundation: https://lib.nomfoundation.org/ · NLV: https://nlv.gov.vn/ef/han-nom-collection.html
- archive.org BULAC: https://archive.org/details/ARC.HOANG.49
- Huế: https://baovanhoa.vn/van-hoa/hon-452000-trang-tu-lieu-han-nom-duoc-so-hoa-117385.html ·
  https://baovanhoa.vn/van-hoa/tp-hue-day-manh-so-hoa-va-phat-huy-gia-tri-tu-lieu-han-nom-172891.html
- Quảng Trị: https://baovanhoa.vn/di-san/so-hoa-di-san-tai-lieu-han-nom-dot-3-tai-quang-tri-43701.html
- HUC: https://search.huc.edu.vn/ · BL: https://searcharchives.bl.uk/ · EAP219: https://eap.bl.uk/node/2656
- UW guide (danh sách kho số Việt Nam): https://guides.lib.uw.edu/c.php?g=341405&p=2303597
- Thượng Hải: https://www.thepaper.cn/newsDetail_forward_3315279 · FamilySearch: https://www.familysearch.org/search/collection/1787988
- Genealogy‑MBW: https://www.zhonghuapu.com/Public/documents/Genealogy-MBW-Introduction(Chinese)-20220830.pdf
- CHisIEC: https://github.com/tangxuemei1995/CHisIEC · OCR: https://arxiv.org/abs/2510.04003
