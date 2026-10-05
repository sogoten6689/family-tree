# Task — Đưa đủ 28 gia phả Hán Nôm vào DB + trang thống kê công khai

> **Ngày:** 2026-10-05 · **Trạng thái:** chưa code — file này để nhớ việc.
> **Yêu cầu (Lâm):** liệt kê gia phả Hán Nôm kèm trạng thái (mã định danh, OCR, phiên âm, dịch nghĩa,
> cô đọng, tạo cấu trúc), **đưa vào database với hình ảnh đầy đủ**, làm **trang thống kê công khai** trong web app.
> **Liên quan:** [hannom_gia_pha_source_hunt_plan.md](./hannom_gia_pha_source_hunt_plan.md) (đi tìm nguồn),
> [ma_dinh_danh_tu_dong.md](./ma_dinh_danh_tu_dong.md)

---

## 1. Dữ liệu hiện có (đọc từ file ngày 05/10, chưa đối chiếu DB VPS)

Nguồn: `data/00_raw/hannom/books_catalog.json` (42 mục) + record nghiên cứu
`../hannom-bilingual-dataset/data/*/*.json` (repo dữ liệu sibling, xem `research/hannom-bilingual-dataset/scripts/_repo_paths.py`).

### 1.1. 28 gia phả có ảnh chữ Hán/Nôm

"Trang" = số trang trong record nghiên cứu (Nom Foundation tính theo tờ, có thể < số ảnh, vd nom-84: 47 tờ / 94 ảnh).

| # | doc_id | Tên | Trang | Mã định danh | OCR | Phiên âm | Dịch nghĩa |
|--:|---|---|--:|---|:-:|:-:|:-:|
| 1 | nom-855 | Nguyễn tộc gia phả | 100 | F-A-NG-TrungTu-006-1843 | ✅ | ✅ | ✅ |
| 2 | nom-208 | Đông Trù Đoàn tộc phả | 79 | F-B-DO-DongTru-007-1845 | ✅ | ✅ | ✅ |
| 3 | nom-1255 | Chu tộc gia phả | 6 | F-L-CH-NongKhe-004-1911 | ✅ | ✅ | ✅ |
| 4 | nom-1158 | Giang Thị gia phả | 55 | F-L-GI-MongPhu-010-1848 | ✅ | ✅ | ✅ |
| 5 | nom-429 | Thuỵ Ứng gia phả | 9 | F-B-NG-ThuyUng-005-1912 | ✅ | ✅ | ✅ |
| 6 | nom-563 | Trạng nguyên Hu Liêu… | 44 | F-B-NG-BoiKhe-008-1496 | ✅ | ✅ | ✅ |
| 7 | nom-854 | Nguyễn đường phả ký | 40 | F-M-NG-TayTuu-009-1844 | ✅ | ✅ | ✅ |
| 8 | gpc-dang-1928 | Gia phả chí họ Đặng | 17 | F-D-DA-KimDoi-002-1928 | ✅ | ⚠️ 2/17 | ✅ |
| 9 | nom-84 | Bạch Vân Am… phả ký | 47 | — | ✅ | ✅ | ✅ |
| 10 | nom-147 | Chu tộc gia phả | 58 | — | ✅ | ✅ | ✅ |
| 11 | nom-207 | Đoàn tộc phả | 85 | — | ✅ | ✅ | ✅ |
| 12 | nom-557 | Thống Hội đại tộc thạch phả | 55 | — | ✅ | ✅ | ✅ |
| 13 | nom-833 | Mộ trạch Lê thị… | 60 | — | ✅ | ✅ | ✅ |
| 14 | nom-865 | Phả ký miếu mộ | 21 | — | ✅ | ✅ | ✅ |
| 15 | nom-1256 | Lê tộc đại tông gia phả | 30 | — | ✅ | ✅ | ✅ |
| 16 | pdf-1000-mai | Mai thị tông phả | 131 | — | ✅ | ✅ | ✅ |
| 17 | pdf-1001-la | Là thị tông phả | 118 | — | ✅ | ✅ | ✅ |
| 18 | pdf-1005-tran | Trần thị tông phả | 233 | — | ✅ | ✅ | ✅ |
| 19 | hxh-129 | Yên Lãng thượng thư công | 23 | — | ⚠️ 14/23 | ❌ | ❌ |
| 20 | hxh-105 | Gia phả các dòng họ (HXH) | 181 | — | ❌ | ❌ | ❌ |
| 21 | hxh-13 | Đoàn thị thực lục | 28 | — | ❌ | ❌ | ❌ |
| 22 | hxh-16 | Ngô gia thế phả | 58 | — | ❌ | ❌ | ❌ |
| 23 | hxh-73 | Đặng gia thế phả | 47 | — | ❌ | ❌ | ❌ |
| 24 | nguyen-khoa-q1 | Nguyễn Khoa thế phổ q.1 | 94 | — | ❌ | ❌ | ❌ |
| 25 | nguyen-khoa-q2 | Nguyễn Khoa thế phổ q.2 | 105 | — | ❌ | ❌ | ❌ |
| 26 | nlv-1042 | Đỗ tộc gia phả | 14 | — | ❌ | ❌ | ❌ |
| 27 | nom-308 | Nguyễn Đường phả kí | 20 | — | ❌ | ❌ | ❌ |
| 28 | nom-309 | Nguyễn Đường phả kí (Nôm) | 33 | — | ❌ | ❌ | ❌ |

**Cô đọng:** 0/28. Bước này chưa được viết (`nlp_family_extractor/app/pipeline/service.py:428` báo lỗi "chưa triển khai").
**Cấu trúc cây:** 0/28 cây có người. `data/00_raw/hannom/family_trees/nom-855|208|1255.json` chỉ có `nodes: []`.

### 1.2. Thống kê

| Chỉ số | Cuốn / 28 | Trang / 1.791 |
|---|--:|--:|
| Có mã định danh | 8 | — |
| OCR xong | 18 (+1 dở) | 1.202 (67%) |
| Phiên âm xong | 17 (+1 dở) | 1.173 (65%) |
| Dịch nghĩa xong | 18 | 1.188 (66%) |
| Cô đọng | 0 | 0 |
| Cấu trúc cây | 0 | — |
| Chưa làm gì | 9 | 580 |

Mã `001` (`pdf-phan-gia-cong-pha`, ấn bản) và `003` (`docx-nguyen-van`, DOCX dịch) **không** thuộc 28 bộ trên.

### 1.3. Ngoài 28 bộ (để tham khảo)

- 5 văn bản dòng họ chữ Hán (không phải gia phả), 4 ảnh/in quốc ngữ, 3 DOCX dịch, 2 sách lý thuyết. Xem `books_catalog.json`.
- Tải ngày 05/10: 10 bộ **liên quan** (ngọc phả, sổ hậu kỵ, niên phả, văn phái), 430 ảnh, 331 MB, nằm ở
  `data/00_raw/hannom/related/` (`SUMMARY.md`). **Không** gộp vào 28 bộ.
- Danh mục Kyoto GCR WP6: 332 gia phả ở Viện Hán Nôm và Thư viện Quốc gia. Cả 12 mục có ảnh online repo đã có;
  313 mục ở Viện Hán Nôm không có ảnh online. File: `data/05_ops/sources_discovery/hannom/kyoto_gcr6/gcr6_catalogue.csv`.

## 2. Quyết định của Lâm (05/10)

| Câu hỏi | Trả lời |
|---|---|
| Danh sách 28 bộ lấy từ đâu | **Đưa cả 28 bộ vào database, kèm đủ hình ảnh** (kể cả 9 bộ chưa làm) |
| Ai xem trang thống kê | **Công khai** |
| Cấp cho việc này | **L4**: được code, chạy local, commit và push nhánh riêng. Deploy hoặc ghi DB VPS = R5, phải hỏi riêng |

## 3. Phát hiện kỹ thuật (fact, từ code)

- `nlp_family_extractor/tools/import_hannom_bilingual_corpus.py` **bỏ qua record draft/chưa có text** (dòng ~532),
  nên 9 bộ chưa làm hiện không thể vào DB.
- Script import gọi `normalize_balkan_nodes` (**Gemini, tốn tiền, R3**) để dựng cây cho mỗi bộ mới. Repo có
  `GOOGLE_API_KEY` trong `.env`, nên chạy import là có thể gọi thật.
- Ảnh: `tools/attach_hannom_corpus_images.py` đọc từ MinIO staging `hannom-corpus-staging/<đường dẫn sau data/00_raw/>`
  (upload bằng `mc cp -r data/00_raw/ <alias>/<bucket>/hannom-corpus-staging/`), tạo tree rỗng nếu chưa có, rồi gắn Document.
- API thống kê hiện có: `GET /api/admin/stats` (chỉ đếm tổng). Chưa có API tiến độ theo bộ.
- Trạng thái theo bước nằm ở `user_scans` (mã định danh, `ocr_status`, `tree_status`, `family_tree_id`)
  và `gia_pha_page_content` (hannom/transliteration/translation theo trang, version hiện tại).
- DB local (`infra/docker-compose.yml`, MySQL cổng 3309) là **schema cũ, chỉ 7 scan**. Dữ liệu thật nằm trên VPS.

## 4. Plan thực hiện

| Bước | Việc | File | R |
|---|---|---|---|
| 1 | Import: thêm cờ `--include-draft` (tạo UserScan `ocr_status=pending` + `gia_pha_page` có `image_file_key`, không có version/content) và `--no-tree` (bỏ Gemini) | `tools/import_hannom_bilingual_corpus.py` | R1 |
| 2 | Pytest cho nhánh draft / no-tree | `tests/` | R1–R2 |
| 3 | API công khai `GET /api/public/hannom-progress`: từng bộ (doc_id, tên, số trang, ảnh, mã định danh, số trang OCR / phiên âm / dịch nghĩa, cô đọng = chưa triển khai, cây có ≥1 người) + phần tổng hợp. **Không** trả văn bản gia phả, chỉ trạng thái | `app/workspace/router.py`, schemas, repository | R1 |
| 4 | Trang công khai `/thong-ke-han-nom`: thẻ số liệu, thanh tiến độ theo bước, bảng 28 bộ lọc được, link sang trang tài liệu (chỉ admin hoặc chủ bộ mới mở được) | `family-saga-io/src/pages/HannomProgressPage.tsx`, `App.tsx`, menu | R1 |
| 5 | Vitest + `npm run test && npm run build`; pytest backend | — | R2 |
| 6 | Chạy thử toàn bộ trên local: import `--include-draft --no-tree`, upload ảnh lên MinIO local, attach, mở trang | — | R2 |
| 7 | Commit + push nhánh `feat/hannom-progress`, mở PR | — | R3–R4 |
| 8 | **Hỏi riêng:** chạy import + upload ảnh trên VPS, deploy | — | **R5** |
| 9 | **Hỏi riêng:** dựng cây bằng Gemini cho các bộ đã dịch | — | **R3** |

## 5. Câu hỏi còn mở

- 9 bộ chưa làm có cần OCR ngay không? Nếu có: chạy vote OCR (Kim Hán Nôm / Google Vision = tốn tiền) hay chỉ Paddle local?
- "Cô đọng" định nghĩa thế nào (tóm tắt phả ký? trích bảng người)? Bước này chưa có code.
- Trang tài liệu chi tiết vẫn giới hạn admin/chủ bộ. Có muốn công khai cả ảnh không?

## 6. Tiếp tục làm việc

```bash
docker compose -f infra/docker-compose.yml --project-directory . up -d mysql minio
cd nlp_family_extractor && PYTHONPATH=. python -m pytest tests/ --ignore=tests/test_family_tree_api.py -q
cd ../family-saga-io && npm run test && npm run build
```
