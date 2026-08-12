# Danh sách Entity & Relationship — Family Tree NER+RE

> **SSOT schema Label Studio:** `label_studio_pipeline/ls_importer.py` → `LABEL_STUDIO_CONFIG`  
> **Hướng dẫn gán:** [HUONG_DAN_GAN_NHAN.md](./HUONG_DAN_GAN_NHAN.md) · [QUY_TRINH_GAN_NHAN_TRONG_TASK.md](./QUY_TRINH_GAN_NHAN_TRONG_TASK.md)  
> **Cập nhật:** 2026-08-10  
> **Phạm vi:** gán nhãn trên văn bản **Phả ký** (Quốc ngữ) trong Label Studio

---

## 1. Tổng quan

| Loại | Số nhãn | Vai trò |
|------|---------|---------|
| **Entity (NER)** | 5 | Span text trên Phả ký |
| **Relationship (RE)** | 3 | Mũi tên giữa hai span `PER_NAME` |

```text
Entity:       PER_NAME | GENERATION | DATE | ORDER | LOC
Relationship: FATHER_OF | MOTHER_OF | SPOUSE
```

---

## 2. Entity (NER)

| # | Nhãn | Màu LS | Định nghĩa | Ví dụ span | Không gán khi… |
|---|------|--------|------------|------------|----------------|
| 1 | **PER_NAME** | Cam `#FFA726` | Tên người xuất hiện trong câu (họ tên, húy, tự, hiệu) | `Võ Đào`, `Nguyễn Thị Đáo`, `Huỳnh Nhơn` | Chỉ là tên làng/xã → dùng `LOC`; danh xưng `ông`/`bà`/`cụ` không gộp vào span (trừ khi không tách được) |
| 2 | **GENERATION** | Xanh lá `#66BB6A` | Chỉ đời / thế hệ | `đời thứ 5`, `Đời thứ 7`, `đời 3` | Số thuần không nói “đời” → cân nhắc `DATE` hoặc bỏ |
| 3 | **DATE** | Xanh dương `#42A5F5` | Năm / mốc thời gian | `1928`, `năm 1872`, `1406` | Số đếm hộ khẩu, số vị trí liệt kê (không phải năm) |
| 4 | **ORDER** | Tím `#AB47BC` | Thứ tự con trong nhánh | `con thứ nhất`, `Người con thứ 5`, `con trai trưởng` | “thứ N” không liên quan thứ tự con |
| 5 | **LOC** | Đỏ `#EF5350` | Địa danh (quê, thôn, xã, huyện, tỉnh…) | `Thái Bình`, `Quảng Nam`, `xã Duy Châu` | Biệt danh người trùng địa danh → `PER_NAME` |

### Quy tắc Entity chung

- Một vị trí text = **một** nhãn entity (không overlap).
- Bôi **đúng chuỗi** trong văn bản (không thêm/bớt khoảng trắng).
- Entity phục vụ RE: quan hệ chỉ nối giữa các `PER_NAME`.

### Map sang feature luận văn (tham chiếu)

| Nhãn LS | Lớp feature (`genealogy_extraction_feature_set_plan`) |
|---------|--------------------------------------------------------|
| `PER_NAME` | F1 `person.*` |
| `GENERATION` | F4 `lineage.generation` |
| `DATE` | F3 `event.*` / niên đại |
| `ORDER` | F1 `person.order` |
| `LOC` | F5 `geo.*` |

---

## 3. Relationship (RE)

| # | Nhãn | Hướng (head → tail) | Định nghĩa | Cue ngôn ngữ (gợi ý) | Ví dụ |
|---|------|---------------------|------------|----------------------|-------|
| 1 | **FATHER_OF** | Cha → Con | Quan hệ cha–con (nam) | *sinh*, *có con*, *con của* (ngữ cảnh cha) | `Huỳnh Phổ` → `Huỳnh Nhơn` |
| 2 | **MOTHER_OF** | Mẹ → Con | Quan hệ mẹ–con | *hạ sinh*, *mẹ*, ngữ cảnh nữ | `Nguyễn Thị Yên` → `Huỳnh Nhơn` |
| 3 | **SPOUSE** | Vợ ↔ Chồng | Hôn phối | *lập gia thất*, *kết duyên*, *lấy vợ/chồng*, *hôn phối* | `Huỳnh Cừ` ↔ `Nguyễn Thị Đáo` |

### Quy tắc Relationship chung

- Head và tail **bắt buộc** là span `PER_NAME` đã gán.
- Chỉ gán khi **câu Phả ký nói rõ** (không bịa từ sơ đồ `pha_he` nếu text không nêu).
- `SPOUSE` không phân `husband_of` / `wife_of` — một nhãn hai chiều về mặt nghĩa.
- Không đảo thành `child_of`: nếu câu nói “A là con của B” → gán `B FATHER_OF/MOTHER_OF A`.

### Map ý tưởng generic → schema dự án

| Generic / tài liệu ngoài | Dùng trong project |
|--------------------------|--------------------|
| `Person` | `PER_NAME` |
| `Location` | `LOC` |
| `Date` | `DATE` |
| `husband_of` / `wife_of` | `SPOUSE` |
| `parent_of` (cha) | `FATHER_OF` |
| `parent_of` (mẹ) | `MOTHER_OF` |
| `child_of` | Đảo hướng → `FATHER_OF` / `MOTHER_OF` |

### Map sang feature luận văn

| Nhãn LS | Lớp feature |
|---------|-------------|
| `FATHER_OF` / `MOTHER_OF` | F2 `rel.parent_of` (+ side) |
| `SPOUSE` | F2 `rel.spouse_of` |

---

## 4. Ngoài phạm vi (chưa có trên Label Studio)

Không gán tùy ý; ghi note nếu gặp thường xuyên:

| Ý tưởng | Trạng thái |
|---------|------------|
| Anh/em (`SIBLING`) | Chưa có |
| Chú/bác/cậu/dì | Chưa có |
| Ông/cháu, cụ/chắt | Chưa có |
| Nuôi / kế / con nuôi | Chưa có |
| `TITLE` / chức tước phong kiến | Chưa có (có thể nằm trong prose) |
| `ALIAS` (tự / hiệu tách riêng) | Gộp trong `PER_NAME` hoặc note |

---

## 5. JSON training (sau export)

```json
{
  "entities": [
    { "start": 10, "end": 17, "label": "PER_NAME", "text": "Võ Đào" },
    { "start": 40, "end": 49, "label": "LOC", "text": "Thái Bình" }
  ],
  "relations": [
    { "type": "SPOUSE", "head": 0, "tail": 1 }
  ]
}
```

- `entities[].label` ∈ {`PER_NAME`, `GENERATION`, `DATE`, `ORDER`, `LOC`}
- `relations[].type` ∈ {`FATHER_OF`, `MOTHER_OF`, `SPOUSE`}
- `head` / `tail` = **index** trong mảng `entities` (sau `export_ls_gold` / `to_training_record`)

---

## 6. Checklist nhanh khi đổi schema

Khi thêm/sửa nhãn, cập nhật đồng bộ:

- [ ] `LABEL_STUDIO_CONFIG` trong `ls_importer.py`
- [ ] File này (`ENTITY_RELATIONSHIP_LIST.md`)
- [ ] `HUONG_DAN_GAN_NHAN.md` + `QUY_TRINH_GAN_NHAN_TRONG_TASK.md`
- [ ] Prompt Gemini / `prose_annotator` / `gold_builder` nếu còn dùng
- [ ] Re-validate project Label Studio (`validate_label_config`)

---

*Danh sách này là bảng tra cứu nhãn cho annotator và pipeline. Không mở rộng schema trên UI cho đến khi cập nhật `ls_importer.py`.*
