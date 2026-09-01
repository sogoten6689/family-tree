# Task — Lộ trình tổ chức hệ thống, dữ liệu, tài liệu

> **Ngày:** 2026-08-26  
> **Trạng thái:** OPEN — chưa implement  
> **SSOT tư duy:** [REPO_MAP.md](../REPO_MAP.md)  
> **SSOT format:** [output_formats_and_ui_plan.md](./output_formats_and_ui_plan.md)  
> **SSOT luận văn (khoa học):** [luan_van_phan_tich_va_ke_hoach.md](./luan_van_phan_tich_va_ke_hoach.md)

File này là **kế hoạch thực hiện** sau phân tích senior + giáo sư.  
Không thay đề cương. Không bắt đầu bằng chuyển folder corpus.

---

## Mục tiêu

Sau khi xong lộ trình này, bạn (và Cursor) trả lời được bốn câu không cần mở Developer:

1. Đang đứng **tầng dữ liệu nào** (raw / interim / gold / canonical)?  
2. Đang đi **đường nào** (A ảnh · B chữ · C cây VGP)?  
3. Việc này thuộc **lab** hay **sản phẩm**?  
4. File markdown này **còn sống** hay đã superseded?

**Không phải mục tiêu:** redesign UI, fine-tune model, đổi tên `BalkanNode`, copy 2000 thư mục `data/`.

---

## Hai đường — đừng trộn lịch

| Đường | Việc | File chủ |
|-------|------|----------|
| **H** Hygiene | Nhãn, tài liệu, một chỗ ghi, IA demo | *file này* |
| **K** Khoa học | Baseline rule, gold, số liệu | `luan_van_…` + `rule_based_genealogy_extraction_steps.md` |

H0–H2 **trước** khi đụng NLP lớn. K có thể chạy song song từ H2 (freeze 1 bộ test), nhưng **không** fine-tune trước khi gold có version.

```text
H0 nhãn           ──► H1 triage plan ──► H2 freeze demo
                                              │
                                              ├──► H3 khép User journey (nếu lỗ)
                                              ├──► K1 evaluator + baseline   (khoa học)
                                              └──► H4 DRY extractor          (chỉ khi K1 cần)
                                                       │
                                                       ▼
                                              H5 (tuỳ chọn) đổi tên folder data/
```

---

## Phase H0 — Nhãn, không chuyển file (2–3 ngày)

**Mục đích:** não và script cùng nói một ngôn ngữ. Zero rủi ro dữ liệu.

### Việc

| # | Việc | File | Xong khi |
|---|------|------|----------|
| H0.1 | Bảng map folder hiện tại → 4 tầng | `data/README.md` | Mỗi path `vgp_corpus`, `gia_pha`, `gemini_labels`, `gold_labels`, `hannom/` ghi rõ: raw / interim / gold / (không phải canonical) |
| H0.2 | Một dòng: canonical = MySQL `nodes_json`, không nằm trong `data/` | `data/README.md` + `REPO_MAP.md` § nếu thiếu | Không còn câu “SSOT” cho 2 chỗ khác nhau mà không ghi tầng |
| H0.3 | `pha_he.json` = benchmark cấu trúc, không phải gold NER | `data/README.md` | Có 1 câu in đậm |
| H0.4 | `nlp_family_extractor/data/` = runtime mirror, không phải corpus | `nlp_family_extractor/readme.md` (đoạn ngắn) | Contributor không crawl vào đây |

### Không làm

- `mv` / `git mv` corpus  
- Sửa script crawl  

### Acceptance

- Người mới đọc `data/README.md` chỉ ra được gold đang ở folder nào trong 30 giây.

---

## Phase H1 — Kim tự tháp tài liệu (3–5 ngày)

**Mục đích:** `planning/` hết đóng vai trò vừa plan vừa báo cáo.

### H1.1 Triage 24 file `planning/`

Thêm **3 dòng đầu** mỗi file (không viết lại nội dung):

```markdown
> **Trạng thái:** OPEN | DONE | SUPERSEDED
> **Đường:** H (hệ thống) | K (khoa học) | L3 (UI demo)
> **Sống tại:** (nếu SUPERSEDED: trỏ file còn dùng)
```

Gợi ý phân loại ban đầu (chốt khi làm H1, được sửa):

| Trạng thái | File |
|------------|------|
| **OPEN — H** | `repo_organization_execution_plan.md` (file này), `output_formats_and_ui_plan.md` (taxonomy còn ràng buộc) |
| **OPEN — K** | `luan_van_phan_tich_va_ke_hoach.md`, `rule_based_genealogy_extraction_steps.md`, `labeled_corpus_collection_plan.md`, `labeling_and_hannom_ocr_plan.md` |
| **OPEN — L3** | `visual_tree_ui_info_task.md` (backlog P7/P8), `pipeline_step_detail_task.md` nếu step UI còn thiếu |
| **DONE / archive** | `hannom_credentials_db_plan.md` (đã có DB), `consolidated_session_report_08_2026.md` → coi như báo cáo, chuyển `planning/archive/` hoặc giữ + SUPERSEDED |
| **SUPERSEDED một SSOT crawl** | Root `CRAWL_PLAN.md` **hoặc** `vietnamgiapha_crawl_v2_plan.md` — **giữ một**, file kia 5 dòng trỏ sang |
| **Tham khảo, không OPEN** | `vietnamgiapha_122_data_flow.md`, `genealogy_language_features_analysis.md`, deep-dive F0–F6 — đóng băng, không thêm chapter mới trừ khi K yêu cầu |

### H1.2 Root markdown

| File | Vai trò sau H1 |
|------|----------------|
| `REPO_MAP.md` | Hướng (đã có) |
| `business.md` | Claim đề tài |
| `PROJECT.md` | Chạy hệ thống |
| `FEATURES.md` | Spec role |
| `RESEARCH_SOURCES.md` | Corpus |
| `readme.md` | Docker / env |
| `CRAWL_PLAN.md` | Chỉ pointer hoặc nội dung SSOT — không hai bản |

### H1.3 Họp tuần

`note_meeting_weekly/` không chuyển. Thêm 1 dòng vào `REPO_MAP.md` (nếu chưa): họp ≠ phương pháp luận văn.

### Acceptance

- Có `planning/README.md` (≤ 40 dòng): bảng OPEN / DONE / SUPERSEDED.  
- Không mở **plan thứ 25** cho đề tài đã có file.

---

## Phase H2 — Freeze demo + 1–2 tư liệu mẫu (2–4 ngày)

**Mục đích:** luận văn và demo cùng một mũi tên. Phụ thuộc H0 (biết tầng).

Bám `luan_van_phan_tich_va_ke_hoach.md` §4.2 và §5.2 Phase 0.

### Việc

| # | Việc | Xong khi |
|---|------|----------|
| H2.1 | Chốt **1 câu đóng góp** (dán vào `luan_van` §0 hoặc 1 trang phạm vi) | 1 câu, không có “và crawl và UI và fine-tune” |
| H2.2 | Chốt **1 happy path** 6 bước: tư liệu → (OCR) → extract → canonical → xem → export | Script demo 5–7 phút, **không** vào `/admin/developer/*` |
| H2.3 | Chốt **1–2 bộ mẫu** có tên: ví dụ 1 Phả ký Quốc ngữ (đường B) + 1 trang/volume Nom (đường A) **hoặc** 1 cây `vpg-*` công khai (đường C, nêu rõ *không phải NLP*) | Path file trong `data/` hoặc `tree_id` MySQL |
| H2.4 | Out-of-scope list (fine-tune, vis-network, gộp folder data) | Nằm cùng trang phạm vi |

### Acceptance

- Slide “90 giây” vẽ được bằng flowchart `REPO_MAP.md` §2.  
- Người ngoài làm theo Guide **không** cần tài khoản developer.

---

## Phase H3 — Khép chỗ thủng sản phẩm (1–2 tuần, chỉ lỗ thật)

**Mục đích:** User đi hết happy path trên **cùng store** với cây xem lại được. Không redesign menu.

### Audit trước khi code (nửa ngày)

Ghi vào checklist dưới đây — tick theo **code hiện tại**, đừng đoán:

| Lỗ đã biết (2026-08) | Việc H3 | Không làm |
|----------------------|---------|-----------|
| Tab OCR User = placeholder | Nối sang OCR thật **hoặc** demo đi Admin OCR + User chỉ extract chữ | Xây OCR engine mới |
| Export User = hint | Nút gọi API export đã có (`/export?format=`) | Format mới |
| User vs Admin “hai zone” | Xác nhận `createUserFamilyTree` ghi `family_tree` + `user_id` | Bảng cây thứ hai |
| Pipeline `distilled` chưa làm | Luận văn **không** demo bước này; ghi hạn chế | Implement distilled |
| Rule class `extract() → []` | Thuộc đường **K**, không phải H3 | Refactor rules trong H3 |

### Thứ tự implement (nếu audit xác nhận lỗ)

1. Export trên màn User tree detail (mỏng).  
2. OCR User: **một** quyết định — (A) deep-link sang luồng document admin nếu user là admin demo, hoặc (B) gọi `ocr-transliterate` trên `user_scans` nếu đã có file trên MinIO.  
3. Guide page: 6 bước = route thật (`genealogyFlow.ts`).

### Acceptance

- Từ upload chữ (đường B) → analyze → lưu → `/user/family-trees/:id` xem lại → export JSON.  
- Không bắt buộc OCR trên User nếu H2 chọn mẫu đã phiên âm.

---

## Phase K1 — Baseline đo được (song song H3, 1–2 tuần)

**Đây là đường khoa học.** Chi tiết kỹ thuật rule: `rule_based_genealogy_extraction_steps.md`. File này chỉ **lịch và cổng**.

| # | Việc | Cổng |
|---|------|------|
| K1.1 | Freeze **tập đánh giá nhỏ**: 30–50 câu/đoạn **hoặc** stratified gold đã có (`data/02_gold/gold_labels/`) — ghi version + ngày | 1 manifest JSON (tree_id / file list) |
| K1.2 | Script evaluator: rule output vs gold (P/R cho `FATHER_OF`, `MOTHER_OF`, `SPOUSE`) | Chạy 1 lệnh, in bảng |
| K1.3 | Ghi failure cases (20 dòng) | Phụ lục luận văn |
| K1.4 | Hybrid: rule chắc + Gemini normalize — **đo** trên cùng manifest, chưa fine-tune | 3 cột: rule / Gemini / hybrid |

**Không làm trong K1:** train Qwen, gộp `gemini_extractor.py` vào API (đó là H4).

### Acceptance

- Có **một bảng số** dù nhỏ — `luan_van` §6 checklist.

---

## Phase H4 — Một extractor (chỉ khi K1 vướng)

**Trigger:** lab và `/analyze` ra schema khác nhau, hoặc sửa prompt phải sửa 2 chỗ.

| Việc | Cách an toàn |
|------|----------------|
| H4.1 | Adapter: `label_studio_pipeline` gọi `app.gemini_service` **hoặc** ngược lại — một hướng, không rewrite | Test analyze + 1 script prelabel |
| H4.2 | `FamilyExtractor` giữ public API; class `*Rule` placeholder: **không** xóa trong H4 trừ khi K1 cần test unit từng rule | |

**Không làm:** crawl VGP v1 xóa khi v2 chạy — tách task ingest, không gói vào H4.

---

## Phase H5 — Đổi layout `data/` (tuỳ chọn, sau bảo vệ hoặc sau K1 ổn)

Chỉ khi H0 đã dùng **vài tuần** mà người vẫn nhầm folder.

```text
data/raw/          ← vgp_corpus, hannom/nomfoundation/volumes
data/interim/      ← gemini_labels, OCR json catalog
data/gold/         ← gold_labels (human only)
data/derived/      ← gia_pha export (nếu coi là xuất, không phải gold)
```

Cách làm: `git mv` + sửa path trong `corpus_store.py`, `label_studio_pipeline`, `tools/build_hannom_catalog.py` — **một PR**, có checklist lệnh chạy lại crawl **không** bắt buộc.

Canonical vẫn **không** vào đây.

---

## Lịch gợi ý (6 tuần, có thể co)

Giả sử làm song song luận văn, ~8–12 giờ/tuần. Co theo deadline GVHD.

| Tuần | Phase | Kết quả nhìn thấy |
|------|-------|-------------------|
| 1 | H0 + H1.1 | `data/README` 4 tầng; `planning/README` triage |
| 2 | H1.2 + H2 | 1 trang phạm vi + 2 tư liệu mẫu + script demo |
| 3 | H3 audit + export/Guide | Happy path B chạy được |
| 4–5 | K1 | Bảng P/R |
| 5–6 | H3 OCR (nếu H2 cần đường A) hoặc H4 | Demo A hoặc prompt một chỗ |
| Sau | H5 | Chỉ nếu vẫn rối folder |

Nếu thời gian hẹp: **dừng sau tuần 2 + K1.1–K1.2**. UI sâu và H5 bỏ.

Khớp `luan_van` §5.3: phạm vi → số liệu → demo sạch → mới UI toàn cục → crawl chỉ phụ lục.

---

## Việc *không* đưa vào lịch này

- Thêm renderer (`vis-network`).  
- Fine-tune / Qwen.  
- Implement pipeline step `distilled`.  
- Đổi tên schema `BalkanNode`.  
- Gộp menu Admin thành “một sản phẩm mới”.  
- Firecrawl mở nguồn mới (`source_discovery`) trừ khi corpus đánh giá thiếu.

---

## Checklist file (khi implement, tick tại đây)

**H0:** `data/README.md` · `nlp_family_extractor/readme.md` · (tuỳ) `REPO_MAP.md`  
**H1:** `planning/README.md` · header 24 file · `CRAWL_PLAN.md` pointer  
**H2:** `planning/luan_van_phan_tich_va_ke_hoach.md` §0  
**H3:** `family-saga-io/src/pages/user/*` · `GuidePage` · `documentApi` / export  
**K1:** script mới dưới `label_studio_pipeline/` hoặc `nlp_family_extractor/tests/` + manifest  
**H4:** `gemini_service.py` / `gemini_extractor.py`  
**H5:** `data/` + path constants  

---

## Rủi ro

| Rủi ro | Giảm |
|--------|------|
| Làm H5 trước H0 | Cấm — plan này ghi thứ tự |
| H3 nở thành redesign IA | Chỉ 3 lỗ trong bảng audit |
| K1 chờ gold “đủ lớn” | 30–50 đơn vị đã freeze vẫn ra số |
| Viết plan mới thay vì triage | H1 cấm plan thứ 25 trùng đề tài |
| Demo nhảy Developer | H2.2: script cấm URL developer |

---

## Bước bạn làm **ngay** (không cần agent sửa code)

1. Đọc file này + `REPO_MAP.md` §2.  
2. Chốt với GVHD: happy path là **B** (chữ) hay **A+B** (có OCR).  
3. Bảo agent: **chạy H0** (chỉ markdown `data/README.md`) — khi bạn nói “làm H0”.
