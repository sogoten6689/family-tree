# CLAUDE.md

> **Cập nhật 2026-09-29 — đã gộp CODE vào `family-tree`:** thư mục này (`family-tree/research/hannom-bilingual-dataset/`) giờ là **bản chính thức của mã nguồn** (scripts, schema, dashboard...), theo yêu cầu "tích hợp thành 1 repo duy nhất". Repo `hannom-bilingual-dataset` cũ (sibling `../hannom-bilingual-dataset` trên đĩa) **vẫn tồn tại nhưng chỉ còn giữ `data/` và `runs/`** (dữ liệu nặng, cố ý loại khỏi family-tree) — xem `scripts/_repo_paths.py` (`DATA_REPO_ROOT`, override bằng biến môi trường `HANNOM_DATA_ROOT` nếu clone repo dữ liệu ở chỗ khác). Mọi quy tắc dưới đây vẫn áp dụng, chỉ đổi phần "2 repo độc lập" ở mục 6.

## Vai trò

Đây là **mã nguồn xử lý** dữ liệu gia phả Hán Nôm — nằm trong `family-tree`, nhưng dữ liệu thật (`data/`, `runs/`) nằm ở repo riêng `hannom-bilingual-dataset` (đọc/ghi qua `DATA_REPO_ROOT`, xem `scripts/_repo_paths.py`). Khi làm việc ở
đây, hành xử như một nhà nghiên cứu cẩn trọng đang dựng bộ dữ liệu cho luận văn —
ưu tiên **đúng và có căn cứ** hơn đầy đủ nhanh.

## Nguyên tắc khoa học (kế thừa từ `family-tree/CLAUDE.md`)

- Phân biệt rõ: **fact** (đọc trực tiếp từ ảnh/OCR/bản dịch) vs **inference**
  (suy luận có căn cứ) vs **assumption** (giả định chưa kiểm chứng). Không bao
  giờ trình bày assumption như fact.
- Mọi trường dữ liệu không có bằng chứng trực tiếp phải ghi `null` hoặc
  "Chưa xác định" — **không bịa** quy mô, hình thức, địa danh, niên đại.
- Khi 2 nguồn OCR bất đồng, không tự chọn 1 bên nếu không có đa số thật (xem
  §Vote OCR bên dưới) — gắn cờ cho người soát, đừng đoán.
- Gắn nhãn độ tin cậy khi ghi `ghi_chu`: "XÁC NHẬN qua đọc trực tiếp" (cao) vs
  "SUY LUẬN" (trung bình/thấp) — xem ví dụ trong `data/track1_hannom_only/*.json`.

## Quy tắc riêng của repo này

1. **Không copy ảnh/PDF gốc.** Mọi record chỉ tham chiếu `nguon.duong_dan_goc`
   (đường dẫn tương đối trong `family-tree`, dùng `FAMILY_TREE`/`FAMILY_TREE_ROOT`
   từ `scripts/_repo_paths.py`) — tránh 2 nguồn sự thật.
2. **Track 1 & 2 là ưu tiên chính** (dữ liệu song ngữ thật/sắp thật). Track 3
   (Việt thuần, `co_ban_han: false`) ưu tiên thấp — chỉ giữ để tham khảo câu
   văn, không đầu tư công sức xử lý sâu.
3. **Chỉ xử lý tài liệu gia phả** (tộc phả, tông phả, chi phả, phân phả, ngọc
   phả, phả ký, phả đồ) — không OCR/dịch/mix kế ước, tế văn, sắc phong, sách lý
   thuyết gia phả học (đúng rule `gia-pha-only-analysis.mdc` bên `family-tree`;
   danh sách loại trừ nằm ở `manifest/classification.json` → `loai_khoi_pham_vi`).
4. **Vote OCR chỉ tự ghi đè khi có đa số thật** (≥3 engine đồng thuận trên
   cùng 1 vị trí ký tự). Với <3 engine, mọi bất đồng ghi vào `uncertain_spans`,
   giữ nguyên backbone — không đoán. Xem thuật toán trong
   `scripts/vote_ocr.py` (docstring đầu file có phân tích số liệu thật).
5. **Mọi thay đổi dữ liệu phải validate lại schema** trước khi commit (chạy từ
   `research/hannom-bilingual-dataset/`, dữ liệu đọc từ `DATA_REPO_ROOT`):
   ```bash
   python3 -c "
   import json, jsonschema, glob
   from scripts._repo_paths import DATA_REPO_ROOT
   schema = json.load(open('schema/bilingual_record.schema.json', encoding='utf-8'))
   v = jsonschema.Draft7Validator(schema)
   for f in glob.glob(str(DATA_REPO_ROOT / 'data' / '*' / '*.json')):
       d = json.load(open(f, encoding='utf-8'))
       for e in v.iter_errors(d):
           print(f, list(e.path), e.message)
   "
   ```
6. **Code đã gộp vào `family-tree` (2026-09-29) — data KHÔNG gộp.** Đừng
   commit/copy `data/` hay `runs/` vào family-tree (đã ignore ở `.gitignore`,
   xem banner đầu file) — 2 loại nội dung (code vs data) vẫn tách biệt về nơi
   lưu trữ dù cùng nằm trong pipeline. Sửa code ở đây (`research/hannom-
   bilingual-dataset/`) được phép — không còn ràng buộc "2 repo độc lập" như
   trước 2026-09-29, vì code giờ CHÍNH LÀ 1 phần của `family-tree`.

## Đọc trước khi làm task

| Việc | Đọc |
|---|---|
| Tổng quan repo, cách chạy pipeline | `README.md` |
| Cấu trúc 1 record | `schema/bilingual_record.schema.json` |
| Tài liệu nào thuộc track nào | `manifest/classification.json` |
| Thêm tài liệu mới | `README.md` §"Thêm tài liệu mới vào repo" |
