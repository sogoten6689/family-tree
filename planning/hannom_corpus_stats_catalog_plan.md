# Plan — Catalog & thống kê toàn bộ sách Hán-Nôm trong source

> **Ngày:** 2026-08-22  
> **Trạng thái:** ✅ Phase A (catalog + HTML danh mục) — 2026-08-22  
> **Bối cảnh:** HTML so sánh OCR lab / Paddle / dịch mới cover **1 cuốn** (*Gia phả chí*). Cần thống kê **mọi cuốn Hán-Nôm** đang có trong source trước khi OCR hàng loạt.  
> **Liên quan:** [labeling_and_hannom_ocr_plan.md](./labeling_and_hannom_ocr_plan.md) (Track B OCR) · [nomfoundation_crawl_plan.md](./nomfoundation_crawl_plan.md) · [nomfoundation_storage_ocr_metadata_gaps.md](./nomfoundation_storage_ocr_metadata_gaps.md) · viewer hiện tại `data/du_lieu_han_nom_moi/thong_ke_han_nom.html` · CLI `nlp_family_extractor/tools/build_hannom_compare_html.py`

Đơn vị nghiên cứu (đã chốt tuần 17/08): **cuốn** = 1 sách; họ = nhóm tra cứu; **1 loại** + **nhiều tag bố cục**.

---

## 1. Mục tiêu

1. Có **một catalog SSOT** mọi cuốn Hán-Nôm local (ảnh scan, PDF, volume Nom).
2. HTML thống kê **theo cuốn** (không chỉ theo trang *Gia phả chí*): địa chỉ, số trang, metadata, trạng thái OCR/dịch.
3. So sánh 2 tool OCR + bản dịch **khi cuốn đã có** — *Gia phả chí* là mẫu; cuốn khác mặc định “chưa OCR”.
4. Không trộn corpus Quốc ngữ VGP (`gia_pha/`, `vgp_corpus/`) vào catalog này.

**Không làm trong plan này:** OCR batch mọi cuốn; fine-tune Paddle; extract cây.

---

## 2. Hiện trạng (2026-08-22)

| Thành phần | Phạm vi | So sánh OCR |
|------------|---------|-------------|
| `thong_ke_han_nom.html` | 17 trang *Gia phả chí* + liệt kê PDF + volume Nom (thiếu sâu) | Lab vs Paddle vs `*-dich.md` — **chỉ 1 cuốn** |
| Nom Foundation local | 15 volume trong catalog | Chưa OCR Paddle; lab OCR nếu có thì chưa gắn vào HTML |
| PDF 13/08 | 3 tông phả | Chưa tách trang, chưa OCR |
| Track B plan | Pilot 1255 / 1256 | CLI OCR volume **chưa viết** |

Hai bản copy ảnh Nom (cùng nội dung):

| Chỗ | Path |
|-----|------|
| Source crawl | `data/hannom/nomfoundation/volumes/{id}/pages/` |
| Review | `data/review_corpus/hannom/{id}/pages/` + `viewer.html` |

Catalog HTML phải **trỏ cả hai**, chọn **một SSOT số trang** (ưu tiên `volumes/` + `metadata.json`).

---

## 3. Inventory — sách đang có trong source

Đếm **cuốn**, không đếm tree VGP Quốc ngữ.

### 3.1. Nom Foundation (`data/hannom/nomfoundation/`)

Nguồn: `catalog.json` + JPG local. URL gốc `lib.nomfoundation.org`.

| volume_id | Nhan đề | Mã | Catalog pages | JPG local | Ghi chú |
|-----------|---------|----|---------------|-----------|---------|
| 1255 | 朱族譜記 Chu tộc gia phả | TNVNPF-001 | 6 | 6 | Pilot ngắn |
| 1256 | 黎族大宗家譜 Lê tộc đại tông | TNVNPF-002 | 30 | 30 | Pilot vừa |
| 147 | 朱族家譜 Chu tộc gia phả | NLVNPF-0130 | 58 | 58 | Khác 1255 — cùng họ, khác cuốn |
| 207 | 段族譜 Đoàn tộc phả | NLVNPF-0154 | 85 | 85 | |
| 208 | 東稠段族譜 Đông Trù Đoàn | NLVNPF-0155 | **50** | **79** | Lệch catalog vs file — cần chốt `page_count` |
| 833 | 慕澤黎氏家譜事跡記 | NLVNPF-0665 | 60 | 60 | |
| 854 | 阮堂譜記 | NLVNPF-0685 | 40 | 40 | |
| 855 | 阮族家譜 | NLVNPF-0686 | 100 | **0** | Có metadata, **thiếu ảnh** |
| 865 | 譜記廟墓 | NLVNPF-0696 | 21 | 21 | |
| 84 | 白雲庵居士阮文達譜記 | NLVNPF-0081 | 47 | 47 | |
| 557 | 統會大族石譜 | NLVNPF-0397 | 55 | 55 | |
| 563 | 狀元樗寮先生家譜 | NLVNPF-0404 | 44 | 44 | |
| 1158 | 江氏家譜 | NLVNPF-1034 | 55 | 55 | |
| 429 | 瑞應家譜 Thuỵ Ứng | — | 0 | **0** | Catalog trống |
| 130 | 越史鏡 Việt sử kính | NLVNPF-0118 | 42 | 42 | **Không phải gia phả** — vẫn Hán-Nôm |

**Cộng JPG Nom có ảnh:** ~622 trang (13 cuốn). **2 cuốn chỉ metadata:** 429, 855.

### 3.2. Scan / PDF ngoài Nom (cùng `du_lieu_han_nom_moi/`)

| book_id đề xuất | Nhan đề | Path | Trang / file | OCR / dịch |
|-----------------|---------|------|--------------|------------|
| `gpc-dang-1928` | 家譜誌 Gia phả chí (họ Đặng, Bảo Đại 1928) | `data/du_lieu_han_nom_moi/gia_pha_chi/` | 17 JPG | Lab + Paddle + dich **đủ** |
| `pdf-1000-mai` | 梅氏宗譜 tập 1 | `.../13_8_2026/1000.…pdf` | 1 PDF ~35 MB | Chưa |
| `pdf-1001-la` | 罗氏宗譜 tập 1 | `.../1001.…pdf` | 1 PDF ~45 MB | Chưa |
| `pdf-1005-tran` | 陈氏宗譜 tập 1 | `.../1005.…pdf` | 1 PDF ~73 MB | Chưa |

Ba PDF là **tông phả chữ Hán** (nguồn Trung / in ấn), khác layout scan Nom Việt — vẫn đưa vào catalog, tag `nguon=tong_pho_pdf`.

### 3.3. Có trong source nhưng **không** đưa vào catalog Hán-Nôm gia phả

| Path | Lý do |
|------|--------|
| `data/sach/Gia phả học tinh hoa.pdf` | Sách lý thuyết Quốc ngữ hiện đại |
| `data/sach/3742.pdf` | Cần mở metadata; mặc định **loại trừ** cho đến khi xác nhận là gia phả Hán |
| `data/gia_pha/`, `data/vgp_corpus/` | Phả ký Quốc ngữ VGP |
| `nlp_family_extractor/data/nomfoundation/` | Mirror job/runtime — không phải cuốn thứ hai |
| `../crawl-han-nom-tools/` | Tool tải ảnh, **ngoài** repo `family-tree`; chỉ ghi chú, không nhân bản catalog |

**Tổng cuốn đưa vào catalog v1:** 15 Nom + 1 Gia phả chí + 3 PDF = **19 cuốn**.

---

## 4. Thiết kế

### 4.1. SSOT catalog

File mới (repo data):

`data/hannom/books_catalog.json`

Mỗi phần tử = **1 cuốn**:

```json
{
  "book_id": "nom-1255",
  "source": "nomfoundation | local_scan | tong_pho_pdf",
  "title_han": "朱族譜記",
  "title_vn": "Chu tộc gia phả",
  "clan_key": "chu",
  "loai": ["toc_pha"],
  "layout_tags": [],
  "language": "han | nom | mixed | unknown",
  "script_hint": "khai | thao | printed | unknown",
  "page_count": 6,
  "page_count_source": "metadata | jpg_count | pdf_pages",
  "paths": {
    "root": "data/hannom/nomfoundation/volumes/1255",
    "pages": "data/hannom/nomfoundation/volumes/1255/pages",
    "review": "data/review_corpus/hannom/1255",
    "url": "https://lib.nomfoundation.org/collection/2/volume/1255/"
  },
  "ocr": {
    "lab": false,
    "paddle": false,
    "dich": false
  },
  "notes": ""
}
```

Quy ước `book_id`:

| Nguồn | `book_id` |
|--------|-----------|
| Nom | `nom-{volume_id}` |
| Gia phả chí | `gpc-dang-1928` |
| PDF 13/08 | `pdf-1000-mai`, `pdf-1001-la`, `pdf-1005-tran` |

Generator HTML **đọc catalog này**, không hard-code từng thư mục.

### 4.2. HTML (mở rộng viewer hiện có)

Cùng file `data/du_lieu_han_nom_moi/thong_ke_han_nom.html` (hoặc đổi tên `data/hannom/index.html` rồi redirect — chốt lúc implement).

| Tab | Nội dung |
|-----|----------|
| **Tổng quan** | Số cuốn, tổng trang, % có ảnh / có OCR lab / Paddle / dịch; lọc theo `source`, `loai` |
| **Danh mục cuốn** | Bảng 19 cuốn: nhan đề, họ, trang, path, URL, trạng thái OCR — bấm vào cuốn |
| **So sánh OCR** | Như hiện tại, **theo `book_id`**. Mặc định *Gia phả chí*. Cuốn chưa OCR: hiện ảnh trang + “chưa có lab/Paddle” |
| **Địa chỉ** | Path repo `family-tree-data`, LFS, trùng `volumes/` vs `review_corpus/` |

Không OCR giúp người xem: catalog phải chạy **không cần** Paddle/API.

### 4.3. Đếm trang

| Loại | Cách đếm |
|------|----------|
| Nom JPG | `len(pages/*.jpg)` so với `metadata.page_count` — flag `mismatch` (vd. 208: 50 vs 79; 855: 100 vs 0) |
| Gia phả chí | stem số `0.jpg`…`16.jpg` |
| PDF | `pypdfium2` / `pypdf` số trang — **chưa convert** thành JPG trong phase 1 |

---

## 5. Lộ trình

### Phase A — Catalog (ưu tiên)

1. Viết `books_catalog.json` (tay hoặc script quét 3 nguồn).
2. Script `build_hannom_compare_html.py` đọc catalog → bảng mọi cuốn + giữ so sánh GPC.
3. Flag cuốn thiếu ảnh (429, 855) và lệch page_count (208).
4. Tag sơ bộ: `gia_pha` vs `su_lieu` (130 Việt sử kính) vs `tong_pho_pdf`.

**Xong khi:** mở HTML thấy 19 cuốn, path copy được, GPC vẫn so sánh 3 cột.

### Phase B — Viewer đa cuốn (ảnh)

1. Nom: đọc `pages/` + `metadata.json` trong trang chi tiết cuốn (lật trang, không bắt buộc OCR).
2. PDF: embed / link file; optional render thumbnail trang 1.
3. Không copy thêm ảnh — chỉ relative path.

### Phase C — OCR / dịch theo cuốn (sau catalog)

Không chạy hết ~600+ trang một lúc.

Thứ tự đề xuất (khớp Track B cũ + bài học GPC):

| Ưu tiên | book_id | Lý do |
|---------|---------|--------|
| P0 | `gpc-dang-1928` | Đã có A/B — giữ làm baseline UI |
| P0 | `nom-1255` | 6 trang, đã quen thesis |
| P1 | `nom-1256` | 30 trang, Hán, scale |
| P2 | `nom-208` | Stress; chốt 79 vs 50 trước |
| Backlog | PDF 3 cuốn | Cần render trang trước OCR |
| Loại trừ OCR gia phả | `nom-130` | Không phải phả |

Rule engine (đã rút từ GPC): Paddle cho khải/in Hán; lab cho Nôm/thảo; văn tế không lấy Paddle làm metric.

### Phase D — Tag loại / bố cục (glossary)

Sau catalog: gắn `loai` (`toc_pha` / `tong_pha` / `chi_pha` / `ho_pha`) và tag bố cục từng cuốn — **chờ glossary anh Phương**, không đoán hàng loạt.

---

## 6. Rủi ro

| Rủi ro | Xử lý |
|--------|--------|
| `volumes/` và `review_corpus/` lệch file | Catalog ghi cả hai path; `page_count` từ SSOT `volumes/` |
| 855 / 429 không có JPG | Hiện “thiếu ảnh”; không OCR |
| 208 50 vs 79 | Ghi `mismatch`; lấy số JPG cho thống kê local |
| PDF LFS (`.lfsconfig`) | HTML chỉ link; clone thiếu LFS → file pointer |
| Trùng tên “Chu tộc” 1255 vs 147 | `book_id` theo volume, không theo title |

---

## 7. Acceptance criteria

- [x] `data/hannom/books_catalog.json` liệt kê đủ 19 cuốn (hoặc số cập nhật nếu thêm cuốn).
- [x] HTML tổng quan: số cuốn, tổng trang local, cuốn thiếu ảnh.
- [x] Mỗi cuốn có `book_id`, path repo, URL Nom nếu có.
- [x] *Gia phả chí* vẫn so sánh lab / Paddle / dịch.
- [x] Cuốn Nom chưa OCR không bị báo lỗi; trạng thái `ocr.lab/paddle/dich = false`.
- [x] Quốc ngữ VGP **không** lẫn bảng này.
- [x] Regenerator: `python nlp_family_extractor/tools/build_hannom_compare_html.py` (đọc catalog).

---

## 8. Checklist file

| File | Việc |
|------|------|
| `data/hannom/books_catalog.json` | ✅ SSOT cuốn |
| `nlp_family_extractor/tools/build_hannom_catalog.py` | ✅ quét volumes + GPC + PDF → catalog |
| `nlp_family_extractor/tools/build_hannom_compare_html.py` | ✅ đọc catalog, tab danh mục |
| `data/du_lieu_han_nom_moi/thong_ke_han_nom.html` | ✅ sinh lại |
| `data/hannom/index.html` | ✅ redirect sang HTML thống kê |
| `planning/labeling_and_hannom_ocr_plan.md` | Chỉ **trỏ** Phase C — không gộp OCR vào task này |

---

## 9. Việc làm ngay (khi bắt đầu implement)

1. Chốt 19 `book_id` + `source` như bảng trên.
2. Sinh `books_catalog.json` từ `catalog.json` + GPC + 3 PDF.
3. Nâng HTML: tab danh mục cuốn trước, giữ tab so sánh GPC.
4. Đánh `mismatch` cho 208, `missing_pages` cho 855 và 429.

OCR cuốn thứ hai chỉ sau khi catalog HTML đã xem được mọi path.
