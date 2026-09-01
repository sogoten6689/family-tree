# Bảng mã họ — 25 chữ A–Y, Z = họ còn lại

> Gửi thầy · 2026-08-29  
> **Đơn vị:** 1 cây gia phả = 1 `tree_id` trên VietnamGiaPha (không đếm người).  
> **Mẫu:** **2.152** cây đã crawl (`data/00_raw/vgp_corpus/`).  
> **Cách gán chữ:** A = họ nhiều cây nhất → Y = họ thứ 25; **Z** = mọi họ không thuộc 25 họ này.

Công thức ID tài liệu:

```text
F - {A…Y|Z} - {NNN}
│        │        └── số thứ tự trong mã họ (001, 002, …)
│        └────────── 1 chữ: họ (A–Y) hoặc phần còn lại (Z)
└─────────────────── Domain: Family / Gia phả
```

Ví dụ: `F-A-001` = gia phả họ Nguyễn, tài liệu 01.  
`F-Z-004` = gia phả họ không nằm trong 25 họ dưới (Hồ, Lý, Tạ, Thái, Thân, Phùng, Doãn, Văn Đình, …).

---

## Bảng 25 họ (A–Y)

Họ lấy từ `lineage_name` (tựa cây), khớp đầu chuỗi sau khi bỏ tiền tố *Họ / Dòng họ / Chi tộc*. Không gộp Hoàng↔Huỳnh, Vũ↔Võ (đúng chữ viết trên phả).

| Mã | Họ | Số cây | % / 2.152 | Cộng dồn |
|----|-----|-------:|----------:|---------:|
| **A** | Nguyễn | 574 | 26,7% | 26,7% |
| **B** | Trần | 177 | 8,2% | 34,9% |
| **C** | Lê | 154 | 7,2% | 42,1% |
| **D** | Phạm | 114 | 5,3% | 47,4% |
| **E** | Vũ | 73 | 3,4% | 50,7% |
| **F** | Phan | 70 | 3,3% | 54,0% |
| **G** | Hoàng | 66 | 3,1% | 57,1% |
| **H** | Bùi | 66 | 3,1% | 60,1% |
| **I** | Ngô | 53 | 2,5% | 62,6% |
| **J** | Đỗ | 53 | 2,5% | 65,1% |
| **K** | Đặng | 49 | 2,3% | 67,3% |
| **L** | Trương | 46 | 2,1% | 69,5% |
| **M** | Huỳnh | 41 | 1,9% | 71,4% |
| **N** | Đoàn | 36 | 1,7% | 73,0% |
| **O** | Đinh | 36 | 1,7% | 74,7% |
| **P** | Võ | 32 | 1,5% | 76,2% |
| **Q** | Dương | 25 | 1,2% | 77,4% |
| **R** | Mai | 20 | 0,9% | 78,3% |
| **S** | Đào | 19 | 0,9% | 79,2% |
| **T** | Hà | 17 | 0,8% | 80,0% |
| **U** | Lương | 16 | 0,7% | 80,7% |
| **V** | Trịnh | 14 | 0,7% | 81,4% |
| **W** | Lưu | 12 | 0,6% | 81,9% |
| **X** | Lâm | 12 | 0,6% | 82,5% |
| **Y** | Hồ | 12 | 0,6% | 83,0% |
| **Z** | *các họ còn lại* | 365 | 17,0% | 100% |

**A–Y phủ 83%** số cây crawl (≈ 1.787 / 2.152). **Z ≈ 17%**.

Hàng **Y = Hồ**: bốn họ cùng ~12 cây (Lưu, Lâm, Cao, Hồ). Chọn Hồ vào Y vì nằm trong list 9 họ thầy đưa ban đầu; **Cao** (cũng 12 cây) vào Z. Thầy có thể đổi Y ↔ Cao nếu muốn thuần tần suất không tie-break.

---

## Z — họ ngoài 25 (thường gặp hơn trong Z)

Không đủ suất A–Y, vào Z. Số cây / 2.152 (làm tròn):

| Họ | n | Họ | n |
|----|--:|----|--:|
| Cao | 12 | Lý | 11 |
| Tạ | 10 | Chu, Tô | 9 |
| Kiều, Thái | 7 | Thân, Vương, Phùng | 6 |
| Doãn, Văn Đình, Tôn Thất, Ông, Nghiêm, … | ≤ 5 | *(tựa trống / không parse được)* | một phần của 200 cây |

---

## Không nhầm hai «25»

| | 25 họ A–Y (bảng này) | 25 cây stratified (gold NER) |
|--|----------------------|------------------------------|
| Đơn vị | Họ (mã kho tài liệu) | `tree_id` (mẫu gán nhãn) |
| Mục đích | Taxonomy Domain F | Train/test Label Studio |
| Ví dụ ngoài A–Y | Thái, Tạ, Thân, Phùng, Văn Đình → **Z** | Vẫn nằm trong 25 cây gold |

Mã A–Y **không** thay schema NER (`PER_NAME`, `FATHER_OF`, …).

---

## Ghi chú phương pháp (ngắn)

- **Fact:** đếm `lineage_name` trên 2.152 `meta.json`.  
- **Không** đếm số người trong cây (một phả Nguyễn 5.000 node = 1 cây).  
- Tỷ lệ Nguyễn trên *sách gia phả* (26,7%) thấp hơn tỷ lệ Nguyễn trên *dân số* (~38%) — khác đơn vị, không mâu thuẫn.  
- 342 cây «hợp lệ» NLP (phả ký ≥ 200 ký tự) xếp hạng gần giống; Ngô/Đinh cao hơn một chút vì mẫu NER lệch. Bảng gửi thầy dùng **toàn bộ 2.152**.  
- Catalog Hán-Nôm hiện 27 cuốn — quá nhỏ để xếp hạng họ; không trộn vào bảng này.
