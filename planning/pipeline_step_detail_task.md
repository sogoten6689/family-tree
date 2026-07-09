# Task: Pipeline step detail & edit/update

> **URL mẫu:** `http://localhost:5174/admin/gia-pha/vgp-122?tab=pipeline`  
> **Ngày:** 2026-07-10  
> **SSOT tham chiếu:** [CRAWL_PLAN.md § Phần F](../CRAWL_PLAN.md#phần-f--pipeline-7-bước--hiển-thị-step-ssot)

---

## 1. Mục tiêu

Bổ sung trên tab **Pipeline** (`/admin/gia-pha/:treeId?tab=pipeline`):

1. **Xem chi tiết từng step** — artifact, metadata, thời gian, lỗi.
2. **Sửa / cập nhật thông tin step** — admin chỉnh tay trạng thái, ref, lý do skip, ghi chú lỗi (khi cần hiệu đính).

Phạm vi task này **không** triển khai logic chạy step ⑥ `distilled` hay wire OCR tự động (thuộc F3/F4 trong CRAWL_PLAN).

---

## 2. Trạng thái hiện tại (đã có)

### 2.1. Backend

| Thành phần | File | Ghi chú |
|------------|------|---------|
| Model | `nlp_family_extractor/app/pipeline/models.py` | Bảng `genealogy_pipeline_steps`, 7 `step_id`, 5 `status` |
| Service | `nlp_family_extractor/app/pipeline/service.py` | `sync_from_tree_state`, `run_step`, `skip_step`, `run_all` |
| Router | `nlp_family_extractor/app/pipeline/router.py` | GET list + POST run/skip/run-all |
| Schema | `nlp_family_extractor/app/pipeline/schemas.py` | `PipelineStepResponse`, `PipelineSkipRequest` |

**API đã triển khai:**

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/api/family-trees/{tree_id}/pipeline` | Public |
| `POST` | `/api/family-trees/{tree_id}/pipeline/{step_id}/run` | Admin |
| `POST` | `/api/family-trees/{tree_id}/pipeline/{step_id}/skip` | Admin |
| `POST` | `/api/family-trees/{tree_id}/pipeline/run-all` | Admin |

**Chưa có:** `GET .../pipeline/{step_id}`, `PATCH .../pipeline/{step_id}`, endpoint resolve artifact preview.

### 2.2. Frontend

| Thành phần | File | Ghi chú |
|------------|------|---------|
| Tab Pipeline | `family-saga-io/src/pages/admin/FamilyTreeDetailPage.tsx` | `?tab=pipeline` → `<GenealogyPipelineSteps />` |
| UI steps | `family-saga-io/src/components/pipeline/GenealogyPipelineSteps.tsx` | Ant Design `<Steps>` vertical |
| API client | `family-saga-io/src/lib/pipelineApi.ts` | Types + GET/run/skip/run-all |

**UI hiện tại chỉ hiển thị:**

- Label step + tag `status`
- `output_ref`, `skipped_reason`, `error_message` (plain text)
- Nút Refresh, Run all, Run / Skip (khi `pending` hoặc `error`)

**UI chưa hiển thị:** `input_ref`, `content_hash`, `document_id`, `started_at`, `finished_at`, `updated_at`, preview artifact, form edit.

### 2.3. Ví dụ `vgp-122`

Từ `nlp_family_extractor/data/vietnamgiapha/sync-report.json`:

| Field | Giá trị |
|-------|---------|
| `store_id` | `vgp-122` |
| `tree_id` | 122 |
| `node_count` | 74 |

Sau `sync_from_tree_state`, pipeline VGP thường như sau:

| Step | Status dự kiến | `skipped_reason` / `output_ref` |
|------|----------------|----------------------------------|
| ① `name` | `done` | `output_ref` = tên dòng họ |
| ② `hannom_image` | `skipped` | `vgp_entry` |
| ③ `ocr` | `skipped` | `vgp_entry` |
| ④ `han_chars` | `skipped` | `vgp_entry` |
| ⑤ `quoc_ngu` | `done` | `documents:{id}` (nếu đã attach `full_text.txt`) |
| ⑥ `distilled` | `skipped` | `vgp_entry` |
| ⑦ `output` | `done` | `nodes:74` |

---

## 3. Gap so với CRAWL_PLAN F.4

| Yêu cầu F.4 | Hiện trạng |
|-------------|------------|
| Collapse / Drawer mỗi step | ❌ Chưa có |
| Artifact: link file / preview ảnh / text ≤ 200 ký tự | ❌ Chỉ string `output_ref` |
| Thời gian `started_at`, `finished_at` | ❌ API trả về nhưng UI không render |
| Nút Chạy / Bỏ qua / Thử lại | ✅ Cơ bản (thiếu Thử lại riêng cho `error`) |
| Gating step ⑦ khi ⑥ chưa xong (trừ VGP) | ❌ Chưa có |
| Edit thủ công metadata step | ❌ Chưa có API/UI |

---

## 4. Thiết kế đề xuất

### 4.1. API mới (backend)

#### 4.1.1. GET một step + artifact detail

```
GET /api/family-trees/{tree_id}/pipeline/{step_id}
```

**Response:** `PipelineStepDetailResponse` = `PipelineStepResponse` + `artifact`:

```json
{
  "step_id": "quoc_ngu",
  "status": "done",
  "output_ref": "documents:42",
  "document_id": 42,
  "started_at": "2026-07-09T10:00:00Z",
  "finished_at": "2026-07-09T10:00:05Z",
  "updated_at": "2026-07-09T10:00:05Z",
  "artifact": {
    "kind": "document",
    "document_id": 42,
    "title": "VGP full_text — vgp-122",
    "type": "van_ban",
    "preview_text": "Đời thứ nhất...",
    "files": [
      { "id": 1, "filename": "full_text.txt", "mime_type": "text/plain", "url": "/api/documents/42/files/1/download" }
    ]
  }
}
```

**Quy tắc resolve `output_ref`:**

| Pattern | `artifact.kind` | Hành động |
|---------|-----------------|-----------|
| `documents:{id}` | `document` | Load document + files; preview text từ file `.txt` đầu tiên |
| `nodes:{count}` | `family_tree` | Trả `node_count`, link tab Visual |
| Tên thuần (step `name`) | `text` | `preview_text` = `output_ref` |
| `null` / empty | `none` | Không artifact |

Giới hạn `preview_text`: **200 ký tự** (theo F.4).

#### 4.1.2. PATCH cập nhật step (admin)

```
PATCH /api/family-trees/{tree_id}/pipeline/{step_id}
```

**Body** (`PipelineStepUpdateRequest`):

```json
{
  "status": "skipped",
  "skipped_reason": "user_skip",
  "input_ref": "documents:41",
  "output_ref": "documents:42",
  "error_message": null,
  "document_id": 42
}
```

| Field | Rule |
|-------|------|
| `status` | Optional; enum `pending\|running\|done\|skipped\|error` |
| `skipped_reason` | Bắt buộc nếu `status=skipped`; max 64; values: `already_exists`, `not_applicable`, `user_skip`, `source_has_later_step`, `vgp_entry` |
| `input_ref`, `output_ref` | Optional; max 512 |
| `error_message` | Optional; clear khi set `status=done` |
| `document_id` | Optional int ≥ 0 |

**Không cho PATCH khi `status=running`** (trả 409).

**Side effects:**

- Set `done` / `skipped` / `error` → cập nhật `finished_at`, `updated_at`
- Set `pending` → clear `finished_at`, `error_message` (tuỳ chọn)
- Không tự gọi `sync_from_tree_state` sau PATCH (admin override có ý nghĩa)

Auth: **Admin** (giống run/skip).

### 4.2. UI mới (frontend)

#### 4.2.1. Cấu trúc component

```
GenealogyPipelineSteps.tsx          # giữ list + actions global
└── PipelineStepPanel.tsx           # Collapse.Panel hoặc mở Drawer
    ├── PipelineStepSummary.tsx     # title, status tag, output_ref ngắn
    ├── PipelineStepDetail.tsx      # load GET detail khi expand
    └── PipelineStepEditForm.tsx    # Modal/Drawer form PATCH
```

**Interaction:**

1. Mỗi step trong `<Steps>` có nút **「Chi tiết」** hoặc click expand Collapse.
2. Expand → gọi `GET .../pipeline/{step_id}` (lazy, cache theo `step_id`).
3. Panel detail hiển thị:
   - Metadata: `input_ref`, `output_ref`, `content_hash`, `document_id`
   - Timestamps: `started_at`, `finished_at`, `updated_at` (format locale vi/en)
   - Artifact preview (text truncate, ảnh thumbnail, link tài liệu)
   - Actions: Chạy / Bỏ qua / Thử lại / **Sửa**
4. Nút **Sửa** → `PipelineStepEditForm` với các field PATCH ở §4.1.2.

#### 4.2.2. Artifact preview theo step

| Step | Preview UI |
|------|------------|
| ① `name` | Text + link tab thông tin cây |
| ② `hannom_image` | Grid thumbnail ảnh từ document files |
| ③ `ocr`, ④ `han_chars` | Text snippet OCR + link `/admin/documents/{id}/edit` |
| ⑤ `quoc_ngu` | Text snippet ≤200 ký tự + link document |
| ⑥ `distilled` | Text snippet hoặc placeholder "Chưa triển khai" |
| ⑦ `output` | `node_count` + link `?tab=visual` |

#### 4.2.3. i18n

Thêm block `pipeline` trong `family-saga-io/src/locales/vi.json` và `en.json`:

- `pipeline.detail`, `pipeline.edit`, `pipeline.artifact`, `pipeline.timestamps`
- `pipeline.fields.*`, `pipeline.skippedReasons.*`

Hiện component dùng `defaultValue` fallback — chuyển sang key i18n khi làm task.

#### 4.2.4. Dependency gating (optional — phase 2 nhỏ)

Trong `GenealogyPipelineSteps`, disable nút **Chạy** step `output` khi:

- `distilled` = `pending` hoặc `error`
- **Và** tree **không** phải VGP (`!treeId.startsWith('vgp-')`)

VGP như `vgp-122` vẫn cho chạy ⑦ khi đã có nodes.

---

## 5. Kế hoạch triển khai

| Phase | Việc | Effort |
|-------|------|--------|
| **D1** | Schema `PipelineStepDetailResponse`, `PipelineStepUpdateRequest`; service `get_step_detail`, `update_step`, resolve artifact | 0.5 ngày |
| **D2** | Router: `GET /pipeline/{step_id}`, `PATCH /pipeline/{step_id}` + tests | 0.5 ngày |
| **D3** | `pipelineApi.ts`: `getPipelineStepDetail`, `updatePipelineStep` | 0.25 ngày |
| **D4** | `PipelineStepPanel` + detail view (Collapse/Drawer, preview, timestamps) | 1 ngày |
| **D5** | `PipelineStepEditForm` + validation + refresh list | 0.5 ngày |
| **D6** | i18n + cập nhật `FEATURES.md` (thêm tab Pipeline) | 0.25 ngày |

**Tổng:** ~3 ngày.

---

## 6. Acceptance criteria

### 6.1. View detail

- [ ] Mở `http://localhost:5174/admin/gia-pha/vgp-122?tab=pipeline`, expand step ⑤ → thấy preview text (nếu có document VGP).
- [ ] Step ⑦ hiển thị `nodes:74` và link sang tab Visual.
- [ ] Step ②③④⑥ `skipped` hiển thị `vgp_entry` + không có artifact (hoặc message "Không áp dụng — nguồn VGP").
- [ ] Timestamps hiển thị đúng timezone khi step đã `done`/`skipped`/`error`.
- [ ] Link artifact `documents:{id}` mở `/admin/documents/{id}/edit`.

### 6.2. Edit / update

- [ ] Admin đổi step ⑥ từ `skipped` → `pending` + `skipped_reason` null qua form Sửa.
- [ ] Admin set `output_ref` thủ công (ví dụ `documents:99`) và status `done`.
- [ ] PATCH trả 409 khi step đang `running`.
- [ ] Sau PATCH, list pipeline refresh và hiển thị giá trị mới (không bị `sync_from_tree_state` ghi đè ngay — cần quyết định: **sync chỉ auto-promote, không downgrade admin override**).

### 6.3. Sync vs admin override (quan trọng)

`get_pipeline` hiện luôn gọi `sync_from_tree_state`, có thể **ghi đè** PATCH admin.

**Đề xuất:** Thêm cờ `manual_override` (bool, default false) trên `genealogy_pipeline_steps`:

- PATCH set `manual_override=true`
- `sync_from_tree_state` **bỏ qua** step có `manual_override=true`
- Nút "Đồng bộ lại từ cây" trên UI (optional) reset `manual_override=false` rồi sync

Nếu không muốn migration ngay: phase 1 chỉ PATCH + warning trong UI "Làm mới có thể ghi đè"; phase 2 thêm `manual_override`.

---

## 7. File cần sửa / tạo

### Backend

| File | Thay đổi |
|------|----------|
| `nlp_family_extractor/app/pipeline/schemas.py` | +`PipelineStepDetailResponse`, `PipelineStepUpdateRequest`, `PipelineArtifact` |
| `nlp_family_extractor/app/pipeline/service.py` | +`get_step_detail`, `update_step`, `_resolve_artifact` |
| `nlp_family_extractor/app/pipeline/router.py` | +GET/PATCH endpoints |
| `nlp_family_extractor/app/pipeline/models.py` | (optional) +`manual_override` column |

### Frontend

| File | Thay đổi |
|------|----------|
| `family-saga-io/src/lib/pipelineApi.ts` | +detail/update types & functions |
| `family-saga-io/src/components/pipeline/GenealogyPipelineSteps.tsx` | Tích hợp panel/detail |
| `family-saga-io/src/components/pipeline/PipelineStepPanel.tsx` | **Mới** |
| `family-saga-io/src/components/pipeline/PipelineStepDetail.tsx` | **Mới** |
| `family-saga-io/src/components/pipeline/PipelineStepEditForm.tsx` | **Mới** |
| `family-saga-io/src/locales/vi.json`, `en.json` | Keys `pipeline.*` |

### Docs

| File | Thay đổi |
|------|----------|
| `CRAWL_PLAN.md` | Cập nhật F.8: đánh dấu F2 done, thêm phase D (detail/edit) |
| `FEATURES.md` | Thêm mục tab Pipeline admin |

---

## 8. Test plan

### API (manual / pytest)

```bash
# List pipeline
curl -s http://localhost:8000/api/family-trees/vgp-122/pipeline | jq .

# Detail step quoc_ngu
curl -s http://localhost:8000/api/family-trees/vgp-122/pipeline/quoc_ngu | jq .

# PATCH (cần admin token)
curl -s -X PATCH http://localhost:8000/api/family-trees/vgp-122/pipeline/distilled \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"pending","skipped_reason":null}'
```

### UI

1. Login admin → mở `vgp-122?tab=pipeline`.
2. Expand từng step, kiểm tra preview và link.
3. Sửa step ⑥ → pending → refresh trang → xác nhận persist.
4. Tree không VGP (upload ảnh): step ② có thumbnail; step ③ link OCR panel.

---

## 9. Liên kết tài liệu

| Tài liệu | Nội dung liên quan |
|----------|-------------------|
| [CRAWL_PLAN.md § F](../CRAWL_PLAN.md#phần-f--pipeline-7-bước--hiển-thị-step-ssot) | 7 bước, skip rules, UX spec |
| [RESEARCH_SOURCES.md](../RESEARCH_SOURCES.md) | ID `vgp-{n}`, nguồn VGP |
| [FEATURES.md](../FEATURES.md) | Tab admin (cần bổ sung Pipeline) |
| [rule_based_genealogy_extraction_steps.md](./rule_based_genealogy_extraction_steps.md) | NLP extraction — liên quan step ⑥⑦ tương lai |
| `nlp_family_extractor/ARCHITECTURE.md` | Kiến trúc backend |

---

## 10. Ghi chú triển khai nhanh (checklist dev)

```
[ ] Đọc service.sync_from_tree_state — hiểu VGP skip logic
[ ] Implement _resolve_artifact(output_ref, tree_id)
[ ] GET detail endpoint
[ ] PATCH endpoint + validation skipped_reason
[ ] Quyết định manual_override (migration hoặc defer)
[ ] PipelineStepPanel lazy load detail
[ ] Edit form Ant Design Form + Modal
[ ] Link documents → /admin/documents/:id/edit
[ ] Link output → ?tab=visual
[ ] Cập nhật CRAWL_PLAN + FEATURES
```
