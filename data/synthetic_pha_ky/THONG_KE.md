# Thống kê — Phả ký bổ sung (synthetic từ sơ đồ)

> **Nguồn:** `data/synthetic_pha_ky/` · **Tag:** `synthetic_from_pha_he` · **Không dùng Gemini**
> **Cập nhật:** 2026-08-02

## 1. Tổng quan

| Chỉ số | Giá trị |
|--------|---------|
| Số gia phả | **31** |
| Tổng ký tự | **936,177** |
| Entity (gold) | **44,779** |
| Relation (gold) | **12,038** |
| TB ký tự / gia phả | **30,199** |
| TB relation / gia phả | **388.3** |
| Median relation | **447** |

### Phân loại relation

| Loại | Số lượng |
|------|----------|
| FATHER_OF | 12,033 |
| MOTHER_OF | 0 |
| SPOUSE | 5 |

> **Lưu ý:** Sơ đồ VGP chủ yếu suy luận `parent_of` qua `generation_stack` (cha), hiếm mẹ/vợ. Một số cây bị **cap 500 node/relation** (`--max-nodes`).

## 2. Cách xem & đánh giá

1. Mở **`data/synthetic_pha_ky/index.html`** trong trình duyệt (double-click hoặc `open data/synthetic_pha_ky/index.html`)
2. Chọn `tree_id` → đọc `synthetic_pha_ky.txt` kèm số liệu gold
3. So sánh với Phả ký thật: link VGP trong bảng dưới
4. Tiêu chí đánh giá:
   - [ ] Tên người khớp sơ đồ gốc?
   - [ ] Quan hệ cha-con đúng thứ tự đời?
   - [ ] Văn phong template có chấp nhận được cho pre-train?
   - [ ] Có tên lỗi / placeholder (`....`, `vô danh`)?

## 3. Danh sách 31 gia phả

| tree_id | Dòng họ | Nodes | Ký tự | Entity | Relation | FATHER | File |
|---------|---------|-------|-------|--------|----------|--------|------|
| 814 | PHAN ĐẮC TỘC PHẢ - Nam Định | 500 | 35,338 | 1762 | 505 | 500 | `814/synthetic_pha_ky.txt` |
| 397 | Nguyễn Công (Giáng Đông) - Đà Nẵng | 500 | 41,614 | 1838 | 500 | 500 | `397/synthetic_pha_ky.txt` |
| 604 | họ LÊ LỆNH - Thanh Hóa | 500 | 45,421 | 1868 | 500 | 500 | `604/synthetic_pha_ky.txt` |
| 1480 | Nguyễn Bá Vân Hải - Hà Tĩnh | 500 | 37,891 | 1824 | 500 | 500 | `1480/synthetic_pha_ky.txt` |
| 1481 | Trần Văn - Phú Lãnh - Điện Trung - Quảng | 500 | 38,805 | 1917 | 500 | 500 | `1481/synthetic_pha_ky.txt` |
| 1564 | họ Nguyễn Đình - Hưng Yên | 500 | 40,335 | 1723 | 500 | 500 | `1564/synthetic_pha_ky.txt` |
| 1941 | NGUYỄN VĂN - GIAO THỦY - Quảng Nam | 500 | 50,377 | 1941 | 500 | 500 | `1941/synthetic_pha_ky.txt` |
| 1974 | TÁN (BỒ BẢN) - Đà Nẵng | 500 | 37,087 | 1926 | 500 | 500 | `1974/synthetic_pha_ky.txt` |
| 2071 | Huỳnh Bá (Điện Nam - Điện Bàn) - Quảng N | 500 | 38,014 | 1861 | 500 | 500 | `2071/synthetic_pha_ky.txt` |
| 2152 | LÊ SĨ 1868 - 2009 (Cổ định, Nông cống,Th | 500 | 35,154 | 1852 | 500 | 500 | `2152/synthetic_pha_ky.txt` |
| 2175 | TRẦN VĂN (Văn Khúc - Cẩm Khê) - Phú Thọ | 500 | 28,542 | 1475 | 500 | 500 | `2175/synthetic_pha_ky.txt` |
| 2196 | HỌ LÊ - Bình Định | 500 | 38,904 | 1977 | 500 | 500 | `2196/synthetic_pha_ky.txt` |
| 2306 | LÊ VĂN - Nghệ An | 500 | 30,480 | 1700 | 500 | 500 | `2306/synthetic_pha_ky.txt` |
| 2340 | Trần-Đằng (陳 滕) Thuận Bài - Quảng Bình | 500 | 39,928 | 1939 | 500 | 500 | `2340/synthetic_pha_ky.txt` |
| 1567 | Hà Văn - Nghệ An | 461 | 30,589 | 1611 | 459 | 459 | `1567/synthetic_pha_ky.txt` |
| 1339 | Đặng Hữu - Hành Thiện - Nam Định | 448 | 33,893 | 1674 | 447 | 447 | `1339/synthetic_pha_ky.txt` |
| 141 | Họ Vũ ở Hà Ngoại, An Ðổ - Hà Nam | 382 | 28,796 | 1512 | 381 | 381 | `141/synthetic_pha_ky.txt` |
| 1794 | LÊ VĂN (Làng Hiền Sỹ,Phong Điền,TTH) - T | 355 | 24,794 | 1336 | 354 | 354 | `1794/synthetic_pha_ky.txt` |
| 145 | Lê Đình - Bến Tre | 339 | 31,116 | 1338 | 338 | 338 | `145/synthetic_pha_ky.txt` |
| 486 | NGUYỄN-LÊ (LÀO-TÁO--CỦ-CHI) - Sài Gòn | 325 | 25,681 | 1289 | 324 | 324 | `486/synthetic_pha_ky.txt` |
| 2292 | NGUYỄN CÔNG - Hưng Nguyên - Nghệ An | 329 | 34,120 | 1276 | 322 | 322 | `2292/synthetic_pha_ky.txt` |
| 2061 | Vũ Tộc - Bắc Ninh | 312 | 22,898 | 1204 | 311 | 311 | `2061/synthetic_pha_ky.txt` |
| 491 | Đặng Xuân - Nghệ An | 290 | 17,436 | 883 | 288 | 288 | `491/synthetic_pha_ky.txt` |
| 477 | Nguyễn Hoàng - Hà Nam | 279 | 23,115 | 1061 | 278 | 278 | `477/synthetic_pha_ky.txt` |
| 1742 | Dòng Họ Phan Văn - Hà Nội | 262 | 19,906 | 982 | 261 | 261 | `1742/synthetic_pha_ky.txt` |
| 1578 | Họ Lê Văn - Thanh Hóa | 261 | 18,406 | 981 | 260 | 260 | `1578/synthetic_pha_ky.txt` |
| 2035 | Trần Tộc Gia Phả Phái Nhì - Quảng Ngãi | 266 | 22,067 | 1040 | 260 | 260 | `2035/synthetic_pha_ky.txt` |
| 1586 | Nguyễn Bá Hán - Nguyễn Văn Dụ (Đời thứ 9 | 229 | 20,083 | 909 | 228 | 228 | `1586/synthetic_pha_ky.txt` |
| 1731 | NGUYỄN THANH - phái Nhất - Đà Nẵng | 226 | 20,654 | 897 | 225 | 225 | `1731/synthetic_pha_ky.txt` |
| 1181 | Vũ Đình làng Tiên Xá - Hải Dương | 211 | 16,926 | 827 | 210 | 210 | `1181/synthetic_pha_ky.txt` |
| 1065 | HOÀNG GIỮ - Ái Tử - Quảng Trị | 88 | 7,807 | 356 | 87 | 87 | `1065/synthetic_pha_ky.txt` |

## 4. Ví dụ tree 1065 (HOÀNG GIỮ)

- **Synthetic:** `1065/synthetic_pha_ky.txt` — 88 node, 87 relation
- **Phả ký thật:** `data/gia_pha/1065/pha_ky_fix.txt` — lời nói đầu, gần không có quan hệ
- **Sơ đồ:** `data/gia_pha/1065/pha_he.json`

## 5. Lệnh tái tạo

```bash
python -m label_studio_pipeline.generate_synthetic --limit 30
python -m label_studio_pipeline.generate_synthetic --tree-id 1065
```
