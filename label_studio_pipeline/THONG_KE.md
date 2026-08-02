# Thống kê — Label Studio pipeline (VGP corpus)

> **Cập nhật:** 2026-08-02  
> **Nguồn:** `data/vgp_corpus/`, `data/gemini_labels/`  
> **Plan:** [label_studio_pipeline_plan.md](../planning/label_studio_pipeline_plan.md)

---

## 1. Tổng quan

| Chỉ số | Giá trị |
|--------|---------|
| Dải crawl lần 1 | `tree_id` **100 – 200** |
| Dải crawl lần 2 | `tree_id` **201 – 1500** |
| Thư mục đã crawl (có artifact) | **1.263** |
| Gia phả hợp lệ trong corpus* | **189** |
| Đã gán nhãn Gemini + import LS | **38** |
| — Pilot (lần 1) | **8** |
| — Batch 2 (lần 2) | **30** |
| Label Studio project | **Family Tree NER+RE** (id **3**) |

**Hướng dẫn gán nhãn:** [HUONG_DAN_GAN_NHAN.md](./HUONG_DAN_GAN_NHAN.md)

\* Hợp lệ = `pha_ky.txt` ≥ 200 ký tự **và** `pha_he.json` có `node_count > 0`.

---

## 2a. Schema gán nhãn (tóm tắt)

| Loại | Nhãn | Mô tả ngắn |
|------|------|------------|
| Entity | `PER_NAME` | Tên người |
| Entity | `GENERATION` | Đời / thế hệ |
| Entity | `DATE` | Năm, mốc thời gian |
| Entity | `ORDER` | Thứ tự con |
| Entity | `LOC` | Địa danh |
| Relation | `FATHER_OF` | Cha → con |
| Relation | `MOTHER_OF` | Mẹ → con |
| Relation | `SPOUSE` | Vợ / chồng |

Quy trình: Gemini pre-annotate → mở task trên LS → sửa span/relation → **Submit**. Chi tiết + ví dụ: [HUONG_DAN_GAN_NHAN.md](./HUONG_DAN_GAN_NHAN.md).

---

## 2. Tổng hợp nội dung (38 task đã label)

| Chỉ số | Tổng | Trung bình / task |
|--------|------|-------------------|
| Ký tự Phả ký | **196.316** | ~5.166 |
| Entity (Gemini) | **971** | ~25,6 |
| Relation (Gemini) | **214** | ~5,6 |
| Tỷ lệ khớp tên vs sơ đồ** | **~31%** | — |

\** `cross_check`: tên `PER_NAME` từ Gemini có trong danh sách node `pha_he` (exact/fuzzy).

---

## 3. Pilot — 8 gia phả (dải 100–200)

| tree_id | Dòng họ | Phả ký (chars) | Sơ đồ (nodes) | Entity | Relation | Khớp sơ đồ |
|---------|---------|----------------|---------------|--------|----------|------------|
| 101 | Dòng họ Vũ — Thái Bình | 1.635 | 95 | 15 | 1 | 6/6 |
| 102 | Đinh Tộc Kiên Lao — Nam Định | 863 | 1 | 12 | 1 | 0/2 |
| 105 | VŨ — Ninh Bình | 442 | 29 | 6 | 0 | 2/2 |
| 120 | NGUYỄN — Long An | 1.091 | 142 | 1 | 0 | 1/1 |
| 122 | Họ Võ — Nghệ An | 4.044 | 74 | 69 | 33 | 12/40 |
| 145 | Lê Đình — Bến Tre | 468 | 339 | 0 | 0 | — |
| 166 | Thân — Bắc Giang | 287 | 20 | 2 | 0 | — |
| 185 | PHAN — Khánh Hòa | 233 | 1 | 6 | 0 | — |

---

## 4. Batch 2 — 30 gia phả (dải 201–1500)

| tree_id | Dòng họ | Phả ký (chars) | Sơ đồ (nodes) | Entity | Relation | Khớp sơ đồ |
|---------|---------|----------------|---------------|--------|----------|------------|
| 229 | Ông 翁 — Đà Nẵng | 5.485 | 1.436 | 30 | 1 | 7/8 |
| 231 | Ngô Hữu Thôn Gang — Thái Bình | 18.165 | 126 | 42 | 9 | 8/15 |
| 232 | Ngô, Phan Ngô — Thái Bình | 25.719 | 52 | 43 | 22 | 5/32 |
| 243 | Võ (Tuy Phước) — Bình Định | 1.884 | 333 | 8 | 0 | 2/2 |
| 245 | Chi tộc họ Ngô — Bắc Giang | 201 | 1 | 5 | 0 | 0/1 |
| 255 | NGUYỄN XUYẾN — Quảng Ngãi | 2.411 | 144 | 10 | 1 | 3/4 |
| 263 | Lê Công — Quảng Trị | 659 | 12 | 0 | 0 | — |
| 266 | Nguyễn Thành — Đà Nẵng | 2.753 | 1.034 | 27 | 0 | 5/7 |
| 277 | NGUYỄN CẢNH — Nghệ An | 4.941 | 9 | 62 | 0 | 7/20 |
| 281 | LÊ LỆNH — Thanh Hóa | 587 | 777 | 7 | 1 | 0/2 |
| 286 | ĐẶNG — Thanh Hóa | 574 | 168 | 4 | 0 | 0/1 |
| 293 | LÊ NGUYỄN (CỦ CHI) — Sài Gòn | 18.587 | 111 | 65 | 5 | 1/41 |
| 303 | VÕ VĂN — Quảng Nam | 1.987 | 54 | 12 | 0 | 3/3 |
| 310 | Nguyễn Văn Lai Xá — Hà Tây | 1.701 | 1.183 | 44 | 6 | 17/20 |
| 321 | Thái — Đồng Tháp | 619 | 1 | 18 | 10 | 0/13 |
| 364 | Phan tộc — Quảng Ngãi | 2.841 | 144 | 16 | 0 | 4/5 |
| 367 | Trần Phước — Quảng Nam | 4.814 | 1.028 | 37 | 12 | 7/12 |
| 369 | HUỲNH TỘC (PHÁI II) — Quảng Nam | 1.286 | 46 | 15 | 0 | 1/3 |
| 373 | Trần Minh — Cần Thơ | 768 | 5 | 0 | 0 | — |
| 383 | NGUYỄN_HÀ TRỮ_PHÚ VANG — Huế | 13.107 | 378 | 82 | 20 | 6/35 |
| 386 | NGUYỄN ĐỨC — Bình Định | 3.030 | 618 | 45 | 0 | 1/19 |
| 391 | LÊ PHƯỚC — Quảng Nam | **47.571** | **5.485** | **104** | **80** | 12/75 |
| 392 | Nguyễn Tộc Phú Triêm — Quảng Nam | 2.408 | 892 | 20 | 1 | 1/9 |
| 396 | Nguyễn Phúc — Hải Dương | 2.734 | 1 | 40 | 2 | 0/16 |
| 410 | TRẦN TỘC ĐAI TÔN — Nghệ An | 442 | 597 | 19 | 1 | 2/4 |
| 422 | NGÔ-LÊ (CỦ CHI) — Sài Gòn | 17.288 | 1.045 | 56 | 7 | 19/34 |
| 423 | TẠ ĐĂNG — Hà Tây | 3.538 | 45 | 29 | 1 | 7/14 |
| 425 | Lý Trần — Hà Nam | 387 | 1 | 3 | 0 | 0/2 |
| 430 | Họ Thân làng Khê Thượng — Hà Tây | 220 | 1 | 8 | 0 | — |
| 433 | NGUYỄN TỘC ĐIỆN DƯƠNG — Quảng Nam | 546 | 1 | 9 | 0 | 0/1 |

---

## 5. Top 5 — Phả ký dài nhất (đã label)

| # | tree_id | Dòng họ | Ký tự |
|---|---------|---------|-------|
| 1 | 391 | LÊ PHƯỚC — Quảng Nam | 47.571 |
| 2 | 232 | Ngô, Phan Ngô — Thái Bình | 25.719 |
| 3 | 231 | Ngô Hữu Thôn Gang — Thái Bình | 18.165 |
| 4 | 293 | LÊ NGUYỄN (CỦ CHI) | 18.587 |
| 5 | 422 | NGÔ-LÊ (CỦ CHI) | 17.288 |

---

## 6. Top 5 — Sơ đồ lớn nhất (đã label)

| # | tree_id | Dòng họ | Nodes |
|---|---------|---------|-------|
| 1 | 391 | LÊ PHƯỚC — Quảng Nam | 5.485 |
| 2 | 229 | Ông 翁 — Đà Nẵng | 1.436 |
| 3 | 266 | Nguyễn Thành — Đà Nẵng | 1.034 |
| 4 | 367 | Trần Phước — Quảng Nam | 1.028 |
| 5 | 422 | NGÔ-LÊ (CỦ CHI) | 1.045 |

---

## 7. Artifact trên disk

```
data/vgp_corpus/
├── pilot_trees.json      # (đã ghi đè lần crawl 2 — xem batch_trees.json)
├── batch_trees.json      # 30 tree_id batch 2
├── summary.json          # log crawl 201–1500
└── {tree_id}/
    ├── meta.json
    ├── pha_ky.txt
    ├── pha_he.json
    └── pha_he.txt

data/gemini_labels/{tree_id}/
├── pha_ky.entities.json
├── pha_ky.ls_task.json
└── cross_check.json      # nếu chạy --cross-check
```

---

## 8. Lệnh tái tạo / mở rộng

```bash
# Crawl thêm + chọn N bộ mới
python -m label_studio_pipeline.crawl_corpus \
  --start 1501 --end 2500 --pilot-limit 0 \
  --batch-limit 30 --batch-min-tree-id 1501

# Gemini + import
python -m label_studio_pipeline.label_and_import \
  --pilot-file data/vgp_corpus/batch_trees.json --cross-check
```

---

## 9. Ghi chú chất lượng

- Một số cây có **sơ đồ 1 node** nhưng vẫn đủ điều kiện pilot (pha_ky ≥ 200 chars).
- **Tree 391** (Lê Phước) là outlier lớn nhất: ~48k chars Phả ký, ~5,5k nodes — task LS rất dài.
- Tỷ lệ khớp tên Gemini ↔ sơ đồ thấp (~31%) là bình thường ở giai đoạn pre-annotation: tên trong phả ký narrative không trùng hoàn toàn format tên trên sơ đồ.
- **Tree 145, 263, 373, 430**: Gemini trả 0 entity — cần review prompt hoặc annotate thủ công.

---

*File tự động tổng hợp từ corpus local. Cập nhật lại sau mỗi lần crawl/label batch mới.*
