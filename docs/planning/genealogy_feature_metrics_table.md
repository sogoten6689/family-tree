# Bảng metrics đặc trưng F0–F6 — phân tích & chỉnh sửa

> **Ngày:** 2026-07-20  
> **Mục đích:** Bảng tra cứu để phân tích, chỉnh sửa, bổ sung từng đặc trưng trước khi implement / gán nhãn gold  
> **Tham chiếu:**  
> - Ngôn ngữ trước: [genealogy_language_features_analysis.md](./genealogy_language_features_analysis.md)  
> - IR F0–F6: [genealogy_feature_layers_deep_dive.md](./genealogy_feature_layers_deep_dive.md)

---

## Cách dùng file này

1. Cột **Chỉnh sửa / ghi chú** — ghi ý kiến, thay đổi, câu hỏi GVHD.
2. Cột **Trạng thái** — cập nhật khi triển khai: `planned` → `annotating` → `implemented` → `validated`.
3. Thang **1–5** (tự chấm, có thể sửa):
   - **Quan trọng LUẬN VĂN:** mức cần có trong mô hình / chương lý thuyết
   - **Khó trích xuất:** 1 = dễ, 5 = rất khó
   - **Có trong corpus 855:** 0 = không, 1 = có mẫu rõ
4. Copy bảng sang Excel/Google Sheets: chọn bảng markdown → paste hoặc export CSV từ § cuối.

---

## Chú giải cột (legend)

| Cột | Ý nghĩa |
|-----|---------|
| **ID** | Mã đặc trưng duy nhất (để trace trong gold JSON / code) |
| **Field** | Đường dẫn field trong IR |
| **Kiểu** | string, int, enum, ref, array… |
| **BB** | Bắt buộc: ✅ bắt buộc · ○ nên có · — tùy chọn |
| **Nguồn** | metadata Nom, OCR Hán, phiên âm QN, rule, thủ công… |
| **Phương pháp** | parse, regex, NER, lookup, LLM, human |
| **Map ra** | BalkanNode, edge, node_meta, research_source… |
| **Hỗ trợ quan hệ** | Có tham gia suy luận edge không (✅/—) |
| **Ưu tiên** | P0 MVP luận văn · P1 · P2 · P3 |
| **Trạng thái** | planned / partial / gap / done |
| **Quan trọng (1–5)** | Điền / chỉnh |
| **Khó (1–5)** | Điền / chỉnh |
| **Có 855 (0–1)** | Có ví dụ trong vol. 855 |
| **Metric trích xuất** | Đề xuất đo khi có gold: Precision / Recall / F1 — để trống ban đầu |
| **Chỉnh sửa / ghi chú** | *Bạn điền* |

---

## A. Tổng hợp theo lớp (dashboard)

| Lớp | Số field | P0 | P1 | Trạng thái tổng | Quan trọng TB | Khó TB | Ghi chú luận văn |
|-----|----------|----|----|-----------------|---------------|--------|------------------|
| **F0** doc.* | 18 | 8 | 6 | gap | 4 | 2 | Ngữ cảnh cuốn — chương mô hình IR |
| **F1** person.* | 24 | 10 | 8 | partial | 5 | 3 | Trung tâm entity |
| **F2** rel.* | 12 + 12 cue | 8 | 10 | partial | 5 | 3 | Cue ≠ edge |
| **F3** event.* | 14 | 4 | 6 | gap | 3 | 4 | Xác minh + disambiguation |
| **F4** lineage.* | 11 | 6 | 4 | gap | 4 | 3 | Đặc thù Hán-Nôm |
| **F5** geo.* | 10 | 3 | 4 | gap | 2 | 3 | Meta + vùng miền |
| **F6** prov.* | 11 | 5 | 4 | partial | 4 | 2 | Reproducibility |
| **Edge** (output) | 6 loại | 4 | 2 | partial | 5 | 4 | parent/spouse/sibling… |

*Cập nhật cột "Trạng thái tổng" khi hoàn thành từng nhóm.*

---

## B. F0 — Document context (`doc.*`)

| ID | Field | Kiểu | BB | Nguồn | Phương pháp | Ví dụ (855) | Map ra | Hỗ trợ QH | Ưu tiên | Trạng thái | Q(1–5) | Khó(1–5) | 855 | Metric P/R/F1 | Chỉnh sửa / ghi chú |
|----|-------|------|----|-------|-------------|-------------|--------|-----------|---------|------------|--------|---------|-----|---------------|---------------------|
| F0-01 | `doc.id` | string | ✅ | hệ thống | auto | `nom-855` | tree.id | — | P0 | done | 5 | 1 | 1 | — | |
| F0-02 | `doc.source_type` | enum | ✅ | crawl | auto | `nomfoundation` | research_source | — | P0 | done | 4 | 1 | 1 | — | |
| F0-03 | `doc.external_url` | url | ✅ | metadata | parse | lib.nom…/855/ | external_url | — | P0 | done | 3 | 1 | 1 | — | |
| F0-04 | `doc.title_han` | string | ○ | metadata | parse | 阮族家譜 | tree meta | — | P1 | partial | 3 | 1 | 1 | — | |
| F0-05 | `doc.title_vn` | string | ✅ | metadata | parse | Nguyễn tộc gia phả | tree.name | — | P0 | done | 5 | 1 | 1 | — | |
| F0-06 | `doc.catalog_code` | string | ○ | metadata | parse | NLVNPF-0686 | metadata_json | — | P1 | partial | 3 | 1 | 1 | — | |
| F0-07 | `doc.local_code` | string | — | metadata | parse | R.217 | metadata_json | — | P2 | gap | 2 | 1 | 1 | — | |
| F0-08 | `doc.creator` | string | ○ | fields.Creator | parse | Nguyễn Văn Lý | metadata_json | — | P1 | gap | 2 | 2 | 1 | — | |
| F0-09 | `doc.source_library` | string | ○ | fields.Source | parse | Thư viện QG VN | metadata_json | — | P2 | gap | 2 | 1 | 1 | — | |
| F0-10 | `doc.place_raw` | string | ○ | fields.Place | parse | 河内 • Hà Nội | description | ✅ F5 | P0 | gap | 4 | 2 | 1 | — | |
| F0-11 | `doc.date_raw` | string | ○ | fields.Date | parse | 保大七年 • 1932 | description | ✅ F3 | P0 | gap | 4 | 3 | 1 | — | |
| F0-12 | `doc.date_gregorian` | int | ○ | lookup | era table | 1932 | description | ✅ | P0 | gap | 4 | 3 | 1 | — | |
| F0-13 | `doc.language_primary` | enum | ○ | fields.Language | parse | han | rule pack | ✅ | P0 | partial | 4 | 2 | 1 | — | |
| F0-14 | `doc.script_notes` | string[] | — | OCR sample | detect | han | — | ✅ | P2 | gap | 3 | 4 | 1 | — | |
| F0-15 | `doc.page_count` | int | ○ | metadata | parse | 101 | metadata_json | — | P1 | done | 2 | 1 | 1 | — | |
| F0-16 | `doc.print_type` | enum | — | fields | parse | handwritten | meta | — | P2 | gap | 1 | 1 | 1 | — | |
| F0-17 | `doc.summary` | text | ○ | fields.Description | parse/LLM | đoạn mô tả dài | description | ✅ F1/F2/F4 | P0 | gap | 5 | 3 | 1 | — | **Gold G1** |
| F0-18 | `doc.imaging_date` | date | — | fields | parse | 2009-03-24 | meta | — | P3 | gap | 1 | 1 | 1 | — | |
| F0-19 | `doc.era_document.raw` | string | ○ | F0-11 | parse | Bảo Đại 7 | sub-struct | ✅ | P1 | gap | 3 | 3 | 1 | — | ≠ năm sinh person |
| F0-20 | `doc.era_document.gregorian_year` | int | ○ | lookup | era table | 1932 | sub-struct | — | P1 | gap | 3 | 3 | 1 | — | |
| F0-21 | `doc.genre` | enum | ○ | heuristic | classify | pha_ky | rule select | ✅ | P1 | gap | 4 | 3 | 1 | — | pha_ky / bi_ky |

---

## C. F1 — Person entity (`person.*`)

| ID | Field | Kiểu | BB | Nguồn | Phương pháp | Ví dụ (855) | Map ra | Hỗ trợ QH | Ưu tiên | Trạng thái | Q(1–5) | Khó(1–5) | 855 | Metric P/R/F1 | Chỉnh sửa / ghi chú |
|----|-------|------|----|-------|-------------|-------------|--------|-----------|---------|------------|--------|---------|-----|---------------|---------------------|
| F1-01 | `person.id` | string | ✅ | internal | assign | P007 | graph id | ✅ | P0 | partial | 5 | 1 | 1 | — | |
| F1-02 | `person.full_name` | string | ✅ | phiên âm/OCR | NER, regex | Nguyễn Trù | name | ✅ | P0 | partial | 5 | 2 | 1 | — | NAME_CAPS hiện có |
| F1-03 | `person.full_name_han` | string | ○ | OCR Hán | OCR | 阮惆 | node_meta | ✅ merge | P1 | gap | 4 | 4 | 1 | — | |
| F1-04 | `person.surname` | string | ○ | parse name | rule | Nguyễn | meta | — | P2 | gap | 2 | 2 | 1 | — | |
| F1-05 | `person.given_name` | string | ○ | parse name | rule | Trù | meta | — | P2 | gap | 2 | 2 | 1 | — | |
| F1-06 | `person.middle_name` | string | — | parse name | rule | Văn | meta | — | P3 | gap | 1 | 2 | 1 | — | |
| F1-07 | `person.taboo_name` | string | — | text | regex | Thạch (huý) | node_meta | — | P2 | gap | 2 | 3 | 1 | — | |
| F1-08 | `person.courtesy_name` | string | ○ | text | regex | Trung Lượng, Hữu Tự | node_meta | ✅ merge | P1 | gap | 3 | 2 | 1 | — | `tự X` |
| F1-09 | `person.pseudonym` | string | ○ | text | regex | Loại Am | title/meta | ✅ merge | P1 | gap | 3 | 2 | 1 | — | `hiệu X` |
| F1-10 | `person.posthumous_name` | string | — | text | regex | … công | meta | — | P2 | gap | 2 | 3 | 1 | — | |
| F1-11 | `person.alias[]` | array | — | text | collect | — | meta | ✅ | P2 | gap | 2 | 3 | 0 | — | |
| F1-12 | `person.gender` | enum | ○ | cue/rule | infer | male | gender | ✅ spouse | P0 | partial | 4 | 3 | 0 | — | 子/女, ông/bà |
| F1-13 | `person.social_title` | string | — | text | regex | Thanh Nhàn công | bio/meta | — | P2 | gap | 2 | 3 | 1 | — | |
| F1-14 | `person.office` | string | — | text | regex | tri huyện | bio/meta | — | P2 | gap | 2 | 3 | 1 | — | |
| F1-15 | `person.birth_year` | int | ○ | F3/text | regex, lookup | 1697 | birthYear | ✅ validate | P0 | partial | 4 | 3 | 1 | — | `(1697)` |
| F1-16 | `person.death_year` | int | — | F3/text | regex | — | deathYear | ✅ | P1 | partial | 3 | 3 | 0 | — | |
| F1-17 | `person.age_at_death` | int | — | F3 | regex | 87 | meta | — | P2 | gap | 1 | 2 | 1 | — | Thọ 87 tuổi |
| F1-18 | `person.generation` | int | ○ | F4 | regex | 7, 8 | node_meta | ✅ core | P0 | gap | 5 | 2 | 1 | — | Đời thứ N |
| F1-19 | `person.order_among_siblings` | int | — | F2/F3 | regex | trưởng | meta | ✅ sibling | P2 | gap | 2 | 3 | 0 | — | |
| F1-20 | `person.branch_id` | ref | ○ | F4 | assign | chi Nguyễn Trù | meta | ✅ | P1 | gap | 3 | 3 | 1 | — | |
| F1-21 | `person.residence` | ref F5 | — | text | NER geo | Trung Tự | meta | — | P2 | gap | 2 | 3 | 1 | — | |
| F1-22 | `person.burial_place` | ref F5 | — | text | NER | — | burialPlace | — | P3 | gap | 1 | 3 | 0 | — | VGP có |
| F1-23 | `person.parent_ref_text` | string | ○ | text | regex | con Nguyễn Trù | → F2 | ✅ | P0 | gap | 5 | 2 | 1 | — | |
| F1-24 | `person.spouse_ref_text` | string | — | text | regex | phối | → F2 | ✅ | P1 | gap | 4 | 2 | 0 | — | |
| F1-25 | `person.mentions[]` | span[] | ○ | all | index | — | F6 | ✅ | P1 | gap | 4 | 2 | 1 | — | |
| F1-26 | `person.state` | enum | ○ | pipeline | FSM | resolved | — | ✅ | P1 | gap | 3 | 2 | — | — | candidate/linked |

---

## D. F2 — Relation cue (`rel.*`) — field meta

| ID | Field | Kiểu | BB | Nguồn | Phương pháp | Ví dụ | Map ra | Hỗ trợ QH | Ưu tiên | Trạng thái | Q | Khó | 855 | Metric | Ghi chú |
|----|-------|------|----|-------|-------------|-------|--------|-----------|---------|------------|---|-----|-----|--------|---------|
| F2-01 | `rel.id` | string | ✅ | internal | auto | R-001 | — | ✅ | P0 | planned | 4 | 1 | 1 | — | |
| F2-02 | `rel.cue_type` | enum | ✅ | text | classify | child_of_phrase | edge type | ✅ | P0 | partial | 5 | 2 | 1 | — | xem bảng D2 |
| F2-03 | `rel.cue_text` | string | ✅ | text | match | con | evidence | ✅ | P0 | partial | 5 | 2 | 1 | — | |
| F2-04 | `rel.evidence` | string | ✅ | text | span | …con Nguyễn Trù | audit | ✅ | P0 | partial | 5 | 1 | 1 | — | |
| F2-05 | `rel.lang_layer` | enum | ○ | detect | rule | quoc_ngu_trans | pack | ✅ | P0 | partial | 4 | 2 | 1 | — | |
| F2-06 | `rel.direction` | enum | ○ | parse | logic | reverse | chiều edge | ✅ | P1 | gap | 4 | 3 | 1 | — | |
| F2-07 | `rel.source_mention` | ref F1 | ○ | parse | NER | Nguyễn Ngoạn | source node | ✅ | P0 | gap | 5 | 3 | 1 | — | |
| F2-08 | `rel.target_mention` | ref F1 | ○ | parse | NER | Nguyễn Trù | target node | ✅ | P0 | gap | 5 | 3 | 1 | — | |
| F2-09 | `rel.confidence` | float | ○ | formula | score | 0.88 | rank | ✅ | P1 | gap | 4 | 3 | — | — | §10 deep dive |
| F2-10 | `rel.rule_id` | string | ○ | rule | tag | VN_CHILD_INLINE | debug | ✅ | P0 | partial | 4 | 1 | 1 | — | |
| F2-11 | `rel.prov` | ref F6 | ○ | pipeline | link | page 3 | trace | ✅ | P1 | gap | 4 | 2 | — | — | |

### D2. F2 — Taxonomy `cue_type` (bảng riêng — metrics theo loại cue)

| ID | cue_type | Ví dụ QN | Ví dụ Hán | Edge gợi ý | Rule MVP | Trạng thái code | Q(1–5) | Khó(1–5) | 855 | Recall mục tiêu | Precision mục tiêu | Ghi chú |
|----|----------|----------|-----------|------------|----------|-----------------|--------|---------|-----|-----------------|-------------------|---------|
| CUE-01 | `child_of_phrase` | con Nguyễn Trù | 之子 | parent_of | VN_CHILD_INLINE | gap | 5 | 2 | 1 | | | |
| CUE-02 | `parent_label` | cha là X | 考 | parent_of | RE_FATHER_LABEL | partial | 5 | 2 | 0 | | | |
| CUE-03 | `mother_label` | mẹ là X | 妣 | mother_of | RE_MOTHER_LABEL | partial | 4 | 2 | 0 | | | |
| CUE-04 | `have_child` | có con là | 生男 | parent_of | RE_HAVE_CHILD | partial | 4 | 2 | 0 | | | |
| CUE-05 | `spouse_marry` | kết hôn, lấy | 娶 | spouse_of | RE_SPOUSE | partial | 4 | 2 | 0 | | | |
| CUE-06 | `spouse_of` | vợ của, phối | 配室 | spouse_of | RE_IS_SPOUSE | partial | 4 | 2 | 0 | | | |
| CUE-07 | `sibling` | anh em, huynh đệ | 兄弟 | sibling_of | RE_SIBLING | partial | 3 | 3 | 0 | | | |
| CUE-08 | `birth_order` | con trưởng | 長子 | order meta | — | gap | 3 | 3 | 0 | | | → F3 |
| CUE-09 | `generation_marker` | Đời thứ N | 世 | F4 not edge | — | gap | 5 | 2 | 1 | | | **Không → edge** |
| CUE-10 | `adoptive` | con nuôi | 嗣子 | parent_of* | — | gap | 2 | 4 | 0 | | | |
| CUE-11 | `clan_wife` | chính thất | 嫡 | spouse meta | — | gap | 2 | 4 | 0 | | | |
| CUE-12 | `child_of_reverse` | A là con của B | — | parent_of | RE_CHILD_OF | partial | 5 | 2 | 0 | | | |

---

## E. F3 — Event / life (`event.*`)

| ID | Field | Kiểu | BB | Nguồn | Phương pháp | Ví dụ (855) | Map ra | Hỗ trợ QH | Ưu tiên | Trạng thái | Q | Khó | 855 | Metric | Ghi chú |
|----|-------|------|----|-------|-------------|-------------|--------|-----------|---------|------------|---|-----|-----|--------|---------|
| F3-01 | `event.id` | string | ✅ | internal | auto | E-001 | — | — | P1 | planned | 3 | 1 | 1 | — | |
| F3-02 | `event.person_ref` | ref F1 | ✅ | parse | link | Nguyễn Trù | — | ✅ validate | P0 | gap | 4 | 2 | 1 | — | |
| F3-03 | `event.type` | enum | ✅ | classify | rule | exam | — | ✅ | P0 | gap | 4 | 3 | 1 | — | xem E2 |
| F3-04 | `event.year_raw` | string | ○ | text | regex | Đinh sửu | — | ✅ | P0 | gap | 4 | 3 | 1 | — | |
| F3-05 | `event.year_gregorian` | int | ○ | lookup | era/can chi | 1697 | birthYear | ✅ | P0 | gap | 4 | 4 | 1 | — | |
| F3-06 | `event.era_name` | string | — | text | regex | Thiệu Trị | meta | — | P1 | gap | 2 | 3 | 1 | — | |
| F3-07 | `event.description` | string | ○ | text | span | Hoàng giáp khoa | bio | — | P1 | gap | 3 | 2 | 1 | — | |
| F3-08 | `event.prov` | ref F6 | ○ | pipeline | link | — | trace | — | P1 | gap | 3 | 2 | — | — | |

### E2. F3 — Taxonomy `event.type`

| ID | event.type | Trigger | Ví dụ 855 | Map F1 | Trạng thái | Q | Khó | 855 | Ghi chú |
|----|------------|---------|-----------|--------|------------|---|-----|-----|---------|
| EVT-01 | `birth` | sinh, 生 | — | birth_year | gap | 3 | 3 | 0 | |
| EVT-02 | `death` | mất, 殁 | — | death_year | gap | 3 | 3 | 0 | |
| EVT-03 | `exam` | đỗ, khoa | Hoàng giáp 1697 | bio | gap | 4 | 3 | 1 | |
| EVT-04 | `office_appointed` | phong, bổ | tri huyện | office | gap | 3 | 3 | 1 | |
| EVT-05 | `honor` | phong công | Thanh Nhàn công | social_title | gap | 2 | 3 | 1 | |
| EVT-06 | `copy_genealogy` | sao chép | Nhâm Thân 1932 | F0 | gap | 2 | 2 | 1 | |
| EVT-07 | `life_span` | Thọ N tuổi | Thọ 87 | age_at_death | gap | 2 | 2 | 1 | |

### E3. F3 — Sub `event.exam`

| ID | Field | Ví dụ 855 | Ghi chú |
|----|-------|-----------|---------|
| EX-01 | `exam.type=hoang_giap` | Hoàng giáp khoa | Nguyễn Trù |
| EX-02 | `exam.type=tien_si` | Tiến sĩ án sát | Nguyễn Văn Lý |
| EX-03 | `exam.type=giam_sinh` | Giám sinh | đời 6 |
| EX-04 | `exam.type=tam_truong` | Tam trường | đời 6 |
| EX-05 | `exam.can_chi` | Đinh sửu | |
| EX-06 | `exam.year` | 1697, 1843 | |

---

## F. F4 — Lineage structure (`lineage.*`)

| ID | Field | Kiểu | BB | Nguồn | Phương pháp | Ví dụ (855) | Map ra | Hỗ trợ QH | Ưu tiên | Trạng thái | Q | Khó | 855 | Metric | Ghi chú |
|----|-------|------|----|-------|-------------|-------------|--------|-----------|---------|------------|---|-----|-----|--------|---------|
| F4-01 | `lineage.thuy_to` | string/ref | ○ | text | regex | Thanh Quốc công | meta | ✅ anchor | P0 | gap | 4 | 2 | 1 | — | node ảo? |
| F4-02 | `lineage.thuy_to_note` | text | — | text | span | Gia Miêu di cư | meta | — | P2 | gap | 2 | 2 | 1 | — | |
| F4-03 | `lineage.branches[]` | array | ○ | text | parse | chi Nguyễn Trù | meta | ✅ | P1 | gap | 4 | 3 | 1 | — | |
| F4-04 | `branch.id` | string | ○ | internal | assign | BR-NTR | — | ✅ | P1 | gap | 3 | 2 | 1 | — | |
| F4-05 | `branch.name` | string | ○ | text | regex | chi Nguyễn Trù | meta | ✅ | P1 | gap | 3 | 2 | 1 | — | |
| F4-06 | `branch.chi_truong` | bool/string | — | text | keyword | chi trưởng | meta | ✅ | P2 | gap | 2 | 2 | 1 | — | |
| F4-07 | `branch.generation_range` | range | — | F4 | infer | 7–8 | — | ✅ | P2 | gap | 3 | 3 | 1 | — | |
| F4-08 | `generation.index` | int | ○ | regex | `Đời thứ N` | 7 | F1.generation | ✅ core | P0 | gap | 5 | 2 | 1 | — | |
| F4-09 | `generation.label_raw` | string | ○ | text | copy | Đời thứ 7 | prov | ✅ | P0 | gap | 4 | 1 | 1 | — | |
| F4-10 | `generation.person_refs[]` | ref[] | ○ | parse | list | [Nguyễn Trù] | F1 | ✅ | P0 | gap | 4 | 2 | 1 | — | |
| F4-11 | `lineage.max_generation` | int | — | aggregate | max | 8 | stats | — | P2 | gap | 2 | 1 | 1 | — | |
| F4-12 | `lineage.generation_base` | int | — | policy | config | 1=thủy tổ? | — | ✅ | P1 | gap | 3 | 4 | — | — | **Câu hỏi mở** |

### F4 — Ràng buộc suy luận (constraint metrics)

| ID | Constraint | Công thức / rule | Vi phạm → | Trạng thái | Ghi chú |
|----|------------|------------------|-----------|------------|---------|
| G-01 | generation_parent | gen(child)=gen(parent)+1 | ↓ confidence | planned | soft |
| G-02 | sibling_same_gen | cùng gen + cùng cha → sibling | suggest edge | planned | |
| G-03 | branch_isolation | khác branch → no merge | block merge | planned | |
| G-04 | thuy_to_no_year | thủy tổ thiếu năm OK | — | planned | |

---

## G. F5 — Spatial (`geo.*`)

| ID | Field | Kiểu | BB | Nguồn | Phương pháp | Ví dụ (855) | Map ra | Hỗ trợ QH | Ưu tiên | Trạng thái | Q | Khó | 855 | Metric | Ghi chú |
|----|-------|------|----|-------|-------------|-------------|--------|-----------|---------|------------|---|-----|-----|--------|---------|
| F5-01 | `geo.id` | string | ○ | internal | auto | G-01 | — | — | P2 | planned | 2 | 1 | 1 | — | |
| F5-02 | `geo.place_raw` | string | ○ | F0/text | copy | 河内 • Hà Nội | — | — | P1 | gap | 3 | 2 | 1 | — | |
| F5-03 | `geo.place_han` | string | — | parse | split | 河内 | meta | — | P2 | gap | 2 | 2 | 1 | — | |
| F5-04 | `geo.place_vn` | string | ○ | parse | split | Hà Nội | meta | — | P1 | gap | 3 | 2 | 1 | — | |
| F5-05 | `geo.locality` | string | ○ | text | NER | làng Trung Tự | meta | — | P1 | gap | 3 | 3 | 1 | — | |
| F5-06 | `geo.district` | string | — | gazetteer | lookup | — | meta | — | P3 | gap | 1 | 3 | 0 | — | |
| F5-07 | `geo.province` | string | ○ | gazetteer | lookup | Hà Nội | meta | — | P1 | gap | 3 | 2 | 1 | — | |
| F5-08 | `geo.region` | enum | ○ | rule/lookup | north | north | rule pack | ✅ F2 | P0 | gap | 4 | 3 | 1 | — | |
| F5-09 | `geo.geo_type` | enum | ○ | classify | residence | clan residence | — | — | P2 | gap | 2 | 2 | 1 | — | |
| F5-10 | `geo.entity_ref` | ref | ○ | link | doc/F1/F4 | F0-10 | — | — | P2 | gap | 2 | 2 | 1 | — | |

---

## H. F6 — Provenance (`prov.*`)

| ID | Field | Kiểu | BB | Nguồn | Phương pháp | Ví dụ | Map ra | Hỗ trợ QH | Ưu tiên | Trạng thái | Q | Khó | 855 | Metric | Ghi chú |
|----|-------|------|----|-------|-------------|-------|--------|-----------|---------|------------|---|-----|-----|--------|---------|
| F6-01 | `prov.document_id` | int | ○ | system | auto | doc #12 | — | — | P1 | done | 3 | 1 | 1 | — | |
| F6-02 | `prov.volume_id` | int | ○ | crawl | auto | 855 | — | — | P1 | done | 2 | 1 | 1 | — | |
| F6-03 | `prov.page_no` | int | ✅ | file | index | 11 | trace | ✅ debug | P0 | partial | 5 | 1 | 1 | — | |
| F6-04 | `prov.line_no` | int | ○ | OCR | index | 12 | trace | ✅ | P1 | gap | 4 | 2 | — | — | |
| F6-05 | `prov.char_start` | int | — | text | offset | 1024 | trace | ✅ | P2 | gap | 3 | 2 | — | — | combined txt |
| F6-06 | `prov.char_end` | int | — | text | offset | 1040 | trace | ✅ | P2 | gap | 3 | 2 | — | — | |
| F6-07 | `prov.source_file` | string | ✅ | MinIO | name | 011.jpg | trace | ✅ | P0 | done | 5 | 1 | 1 | — | |
| F6-08 | `prov.ocr_engine` | string | ○ | config | kim_hannom | kim_hannom | meta | — | P1 | done | 2 | 1 | 1 | — | |
| F6-09 | `prov.ocr_confidence` | float | — | API | score | — | weight | ✅ | P2 | gap | 3 | 3 | — | — | API chưa trả |
| F6-10 | `prov.extraction_method` | enum | ○ | pipeline | tag | rule/manual | audit | — | P0 | partial | 4 | 1 | — | — | |
| F6-11 | `prov.extracted_at` | datetime | — | system | now | — | audit | — | P3 | gap | 1 | 1 | — | — | |

---

## I. Output — Edge canonical (metrics quan hệ)

| ID | Edge type | F1 cần | F2 cue | F3/F4 hỗ trợ | Map Balkan | Trạng thái code | Q | Khó | 855 | Target F1 | Ghi chú |
|----|-----------|--------|--------|--------------|------------|-----------------|---|-----|-----|-----------|---------|
| E-01 | `parent_of` | 2 person | child/parent cue | gen, year | fid | partial | 5 | 3 | 1 | | |
| E-02 | `mother_of` | 2 person | mẹ cue | gender | mid | partial | 4 | 3 | 0 | | |
| E-03 | `spouse_of` | 2 person | spouse cue | gender | pids | partial | 4 | 3 | 0 | | |
| E-04 | `sibling_of` | 2 person | sibling / F4 | same gen | — | partial | 3 | 4 | 0 | | chưa map pids |
| E-05 | `child_of` | inverse E-01 | — | — | inverse | partial | 5 | 3 | 1 | | |
| E-06 | `ancestor_of` | 2+ person | F4 thủy tổ | tree | — | gap | 3 | 4 | 1 | | |

---

## J. Ma trận phụ thuộc feature (✅ = phụ thuộc trực tiếp)

|  | F0 | F1 | F2 | F3 | F4 | F5 | F6 |
|--|----|----|----|----|----|----|-----|
| **F1** | ✅ | — | | | ✅ | | ✅ |
| **F2** | | ✅ | — | | ✅ | | ✅ |
| **F3** | | ✅ | | — | | | ✅ |
| **F4** | ✅ | ✅ | | | — | ✅ | |
| **F5** | ✅ | | | | ✅ | — | |
| **Edge** | | ✅ | ✅ | ✅ | ✅ | | ✅ |

---

## K. Metrics đánh giá trích xuất (điền khi có gold)

### K1. Theo lớp feature

| Metric | Công thức | F0 | F1 | F2 | F3 | F4 | F5 | F6 | Ghi chú |
|--------|-----------|----|----|----|----|----|----|-----|---------|
| **Field Precision** | đúng field / extract field | | | | | | | | so với gold |
| **Field Recall** | extract / gold field | | | | | | | | |
| **Field F1** | harmonic mean | | | | | | | | |
| **Coverage** | % document có field | | | | | | | | |

### K2. Theo quan hệ (edge)

| Metric | Công thức | Giá trị mục tiêu LUẬN VĂN | Thực tế | Corpus |
|--------|-----------|---------------------------|---------|--------|
| Edge Precision | TP/(TP+FP) | ≥ 0.80 (MVP) | | 855 G1 |
| Edge Recall | TP/(TP+FN) | ≥ 0.70 | | |
| Edge F1 | | ≥ 0.75 | | |
| Parent F1 | subset parent_of | | | |
| Spouse F1 | subset | | | |

### K3. Ablation (bỏ lớn → đo edge F1)

| Cấu hình | Bỏ lớp | Edge F1 | Δ so baseline | Ghi chú |
|----------|--------|---------|---------------|---------|
| Baseline | — | | | full F0–F6 |
| Abl-1 | F4 | | | |
| Abl-2 | F3 | | | |
| Abl-3 | F0 | | | |
| Abl-4 | F6 | | | không ảnh hưởng F1 edge |

---

## L. Corpus gold — checklist coverage (855)

| Lớp | Field P0 | Đã gán nhãn | % coverage | Annotator | Ngày |
|-----|----------|-------------|------------|-----------|------|
| F0 | 8 | 0 | 0% | | |
| F1 | 10 | 0 | 0% | | |
| F2 | 8 | 0 | 0% | | |
| F3 | 4 | 0 | 0% | | |
| F4 | 6 | 0 | 0% | | |
| F5 | 3 | 0 | 0% | | |
| F6 | 5 | 0 | 0% | | |
| Edge | 4 | 0 | 0% | | |

*Cập nhật sau khi annotate G1 (Description 855).*

---

## M. Bảng trống — bổ sung đặc trưng mới

| ID | Lớp | Field đề xuất | Kiểu | Mô tả | Q | Khó | Ghi chú |
|----|-----|---------------|------|-------|---|-----|---------|
| | | | | | | | |
| | | | | | | | |
| | | | | | | | |

---

## N. Export nhanh (copy → Excel)

Cột CSV gợi ý cho sheet master:

```text
ID,Layer,Field,Type,Required,Source,Method,Example_855,MapsTo,SupportsRelation,Priority,Status,Importance_1_5,Difficulty_1_5,In855_0_1,Metric_P,Metric_R,Metric_F1,Notes
```

---

## Liên kết

| File | Nội dung |
|------|----------|
| [genealogy_feature_layers_deep_dive.md](./genealogy_feature_layers_deep_dive.md) | Định nghĩa chi tiết từng lớp |
| [genealogy_extraction_feature_set_plan.md](./genealogy_extraction_feature_set_plan.md) | Plan tổng + ngôn ngữ/vùng/thời kỳ |

---

*Cập nhật lần cuối: 2026-07-20 — chỉnh sửa trực tiếp trong repo hoặc export sang Sheets.*
