# Phân tích vấn đề & Kế hoạch làm luận văn

> **Ngày:** 2026-07-25  
> **Đề tài gốc (business.md):** *Mô hình xây dựng tự động cây gia phả từ văn bản gia phả Hán-Nôm*  
> **Repo tham chiếu:** HCMUS Family Tree / Gia Phả Việt  
> **Mục đích file:** Phân tích rối loạn hiện tại (đặc biệt UI & flow tổ chức) + khung kế hoạch luận văn.  
> **Đề cương chi tiết:** bạn dán vào [§0](#0-đề-cương-của-bạn--điền-sau) khi sẵn sàng.

---

## 0. Đề cương của bạn — điền sau

> Dán đề cương chính thức (khoa/GVHD) vào đây. Các mục §1–§6 bên dưới dùng để **map** đề cương → công việc repo, không thay thế đề cương.

```text
[DÁN ĐỀ CƯƠNG TẠI ĐÂY]

Ví dụ cấu trúc thường gặp:
1. Mở đầu
2. Cơ sở lý thuyết / khảo sát
3. Phân tích yêu cầu & thiết kế
4. Xây dựng / triển khai
5. Thực nghiệm & đánh giá
6. Kết luận & hướng phát triển
```

| Chương đề cương | Map sang phần plan này | Ghi chú |
|-----------------|------------------------|---------|
| … | §2 / §3 / §4 | điền sau khi có đề cương |
| … | … | … |

---

## 1. Tóm tắt tình trạng (chẩn đoán ngắn)

Bạn đang có **một hệ thống thật đã chạy khá nhiều**, nhưng **câu chuyện luận văn và trải nghiệm người dùng đang bị phân mảnh**:

| Lớp | Hiện tượng | Hệ quả với luận văn |
|-----|------------|---------------------|
| **Nghiệp vụ** | Đề tài rõ (Hán-Nôm → cây), nhưng có thêm crawl VGP, Nom Foundation, admin tools | Phạm vi dễ phình; khó kể một luồng “end-to-end” gọn |
| **Dữ liệu** | SSOT đang hướng về `BalkanNode[]`, nhưng còn extract thô, VGP raw, localStorage user | Dễ lẫn “format trung gian” với “kết quả cuối” khi viết luận văn |
| **NLP** | Rule-based MVP + Gemini normalize; module rule còn placeholder | Phần khoa học cần **một baseline đo được**, không chỉ demo |
| **UI / flow** | Guest / User / Admin / Developer chồng chéo; xem cây nhiều kiểu; User ≠ Admin về lưu trữ | Người ngoài (và cả bạn) khó trả lời: *“Dùng hệ thống thế nào từ A → Z?”* |

**Vấn đề bạn nêu — “giao diện và flow tổ chức bị rối” — là triệu chứng trung tâm.** Nó không chỉ là “UI xấu”, mà là **chưa có một mô hình tổ chức sản phẩm thống nhất** quanh một pipeline nghiệp vụ.

---

## 2. Phân tích vấn đề chi tiết

### 2.1. Giao diện & flow tổ chức bị rối

#### A. Ba (bốn) “thế giới” song song

```text
GUEST          USER                    ADMIN                 DEVELOPER
xem mẫu        upload/local/analyze    MySQL + MinIO CRUD    crawl, OCR config
/gia-pha       localStorage / tạm      /admin/gia-pha        /admin/developer/*
```

Theo `FEATURES.md`, mục tiêu dài hạn là **hợp nhất** User vào cùng pipeline lưu trữ với Admin; hiện tại vẫn là **hai zone**:

- **Admin zone:** dữ liệu bền (MySQL `family_tree`, MinIO documents, OCR server, pipeline 7 bước).
- **User zone:** nhiều bước còn local / analyze tạm / chưa persist đầy đủ như spec.

→ Flow tổ chức rối vì **cùng một ý niệm “tạo gia phả” lại có hai đường đi khác nhau**.

#### B. Nhiều bề mặt xem cây, chưa một “câu chuyện UI”

| Bề mặt | Route / chỗ | Ghi chú |
|--------|-------------|---------|
| Public | `/gia-pha`, `/gia-pha/:id` | Guest |
| User xem nhanh | `/user/family-tree` | Lịch sử / demo analyze |
| User danh sách | `/user/family-trees` | Workspace user |
| Admin chi tiết | `/admin/gia-pha/:id` (tab sơ đồ, hồ sơ, tư liệu, pipeline…) | Nặng nhất |
| Document reader | `/user/document-reader` | Upload → analyze |
| History | Admin history → xem cây từ request | Có thể còn gắn view legacy |

Đã có hướng thống nhất renderer (`FamilyTreeVisualPanel`, free-only), nhưng **tổ chức thông tin quanh cây** (tab nào bắt buộc, bước nào trước/sau) chưa thành một narrative rõ cho luận văn / demo.

#### C. Menu & IA (information architecture) chồng chức năng

Ví dụ cảm nhận khi dùng:

- User: Dashboard · Document reader · Documents · Family trees · Profile — **mối quan hệ nhân quả giữa các mục không lộ** (upload xong thì sang đâu? cây sinh ra nằm ở đâu?).
- Admin: Gia phả · Documents edit · Users · History · Developer (crawl VGP, Nom, storage…) — **công cụ nghiên cứu / vận hành lẫn với sản phẩm end-user**.
- Pipeline 7 bước nằm trong chi tiết cây admin — rất đúng cho luận văn kỹ thuật, nhưng **dễ “nuốt” UX** nếu demo không tách lớp.

#### D. Hệ quả cụ thể khi làm luận văn / bảo vệ

1. Slide “quy trình hệ thống” khó vẽ một mũi tên sạch.  
2. Demo dễ nhảy lung tung (admin crawl → user reader → public).  
3. Người hỏi: *Phần nào là đóng góp của em?* — dễ bị lẫn tool crawl với mô hình trích xuất.  
4. Viết chương “Thiết kế giao diện” thiếu **user journey** chuẩn.

---

### 2.2. Các vấn đề liên quan (cùng gốc “phân mảnh”)

#### E. Phạm vi đề tài vs phạm vi repo

| Trong đề tài (`business.md`) | Trong repo (đang có thêm) |
|------------------------------|---------------------------|
| Hán-Nôm → OCR/phiên âm → extract → cây | Crawl vietnamgiapha, Nom Foundation import |
| Mô hình quan hệ + trực quan hóa | Admin IAM, developer ops, multi-renderer |
| Đánh giá chất lượng cây | Nhiều nguồn dữ liệu, nhiều heuristic riêng (vd. `generation_stack`) |

**Không phải mọi thứ trong repo đều phải vào luận văn.** Cần **khoanh core thesis** và đánh dấu phần còn lại là *supporting infrastructure*.

#### F. Tầng dữ liệu chưa “kể chuyện” rõ

Từ `output_formats_and_ui_plan.md`:

```text
Nguồn thô → Trung gian (rule/VGP/OCR) → Canonical BalkanNode[] → Derived UI → Export
```

Rối khi UI / code / bài viết **không nói đang đứng ở tầng nào**.  
Luận văn cần một hình taxonomy này và **bám nó xuyên suốt**.

#### G. Rule-based NLP: đúng hướng khoa học, chưa đủ “đóng gói luận văn”

- Đã có MVP regex quan hệ (`spouse_of`, `parent_of`, `sibling_of`) + Gemini normalize.  
- Plan Phase 1 (`rule_based_genealogy_extraction_steps.md`) chưa thành baseline đo precision/recall.  
- Module rule tách file còn placeholder → dễ cảm giác “code rối” dù ý tưởng hybrid đúng.

**Hướng đã thống nhất trước đó (không sửa code lúc này):** siết rule hẹp + đo được → hybrid với LLM; hoãn fine-tune sớm; VGP cấu trúc ≠ cùng một bộ regex văn xuôi.

#### H. Spec vs hiện trạng User (từ FEATURES)

Nhiều mục User từng ⚠️/❌ (persist, bảng tài liệu, stats…). Dù một phần đã tiến triển theo thời gian, **cảm giác flow rối vẫn đúng** nếu journey User chưa khép kín: *upload → lưu → OCR → extract → cây → xem lại*.

---

## 3. Gốc rễ (root cause) — gói lại 5 điểm

1. **Chưa chốt “một happy path”** cho luận văn (ví dụ: 1 tư liệu Hán-Nôm mẫu → 1 cây → 1 trang xem).  
2. **IA theo vai trò kỹ thuật** (admin/dev) thay vì theo **nhiệm vụ người dùng**.  
3. **Hai zone lưu trữ** (user tạm vs admin bền) phá vỡ mô hình tinh thần “một hệ thống”.  
4. **Nhiều ingest path** (upload, VGP, Nom) chưa được gắn nhãn “core / phụ trợ”.  
5. **SSOT & renderer** đã có nguyên tắc, nhưng **chưa dùng làm xương sống khi kể chuyện UI**.

---

## 4. Hướng xử lý rối UI/flow (ý tưởng — chưa implement)

### 4.1. Nguyên tắc tổ chức lại

| Nguyên tắc | Ý nghĩa |
|------------|---------|
| **One pipeline story** | Mọi màn hình map vào 1 pipeline: Tư liệu → Phiên âm/OCR → Extract → Canonical tree → Xem/Xuất |
| **One canonical tree view** | Mọi role xem cây qua cùng panel (đã có hướng `FamilyTreeVisualPanel`) |
| **Role = quyền, không = sản phẩm khác** | User/Admin khác quyền; cùng mô hình màn hình |
| **Research tools tách lớp** | Crawl VGP/Nom, logs, storage → “Công cụ nghiên cứu / vận hành”, không nằm giữa journey chính |
| **Thesis demo path** | 1 kịch bản cố định, 5–7 click, không nhảy developer giữa chừng |

### 4.2. User journey đề xuất cho luận văn (happy path)

```text
[1] Chọn / upload tư liệu Hán-Nôm (hoặc bản phiên âm)
      → [2] OCR / phiên âm (nếu cần)
      → [3] Trích xuất (rule +/hoặc Gemini) → xem people/edges thô
      → [4] Chuẩn hóa BalkanNode[] → lưu cây
      → [5] Xem sơ đồ + hồ sơ thành viên + (tuỳ chọn) pipeline steps
      → [6] Export / công khai (nếu có)
```

Mỗi bước = **một màn hình hoặc một tab có tên nghiệp vụ**, không phải tên kỹ thuật thuần.

### 4.3. Gợi ý IA (information architecture) tối giản

```text
Công khai
  · Giới thiệu
  · Hướng dẫn (đúng happy path trên)
  · Gia phả mẫu

Không gian làm việc (User)
  · Tư liệu của tôi
  · Quy trình xử lý (wizard hoặc chi tiết doc → các bước)
  · Gia phả của tôi
  · Hồ sơ

Quản trị (Admin)
  · Tổng quan
  · Tất cả gia phả / tư liệu / user
  · (Phụ) Công cụ nghiên cứu: crawl, OCR config, storage
```

### 4.4. Việc *không* nên ưu tiên chỉ để “đỡ rối cảm giác”

- Thêm renderer mới khi journey chưa rõ.  
- Thêm quan hệ NLP mở rộng khi chưa có evaluator.  
- Gộp hết crawl vào demo bảo vệ (trừ khi đề cương yêu cầu thu thập corpus).

---

## 5. Plan làm luận văn (khung làm việc)

> Lịch tuyệt đối (tuần/tháng) để bạn và GVHD chốt. Dưới đây là **gói công việc theo phụ thuộc**, phù hợp agent/tự làm.

### 5.1. Ba lớp đóng góp nên tách trong bài

| Lớp | Nội dung | Vai trò luận văn |
|-----|----------|------------------|
| **L1 — Khoa học / mô hình** | Đặc trưng văn bản gia phả; rule-based (+ hybrid); chuẩn hóa quan hệ → graph/`BalkanNode`; đánh giá | **Core** — chương lý thuyết + thực nghiệm |
| **L2 — Hệ thống** | Pipeline end-to-end, SSOT, API, lưu trữ | **Hiện thực hóa** mô hình |
| **L3 — Sản phẩm / UI** | Happy path, xem cây, phân quyền tối thiểu | **Minh họa & kiểm chứng sử dụng** |

Crawl VGP/Nom = **corpus / ingest hỗ trợ** (thuộc L2 phụ), trừ khi đề cương coi thu thập dữ liệu là mục tiêu chính.

### 5.2. Các phase đề xuất

#### Phase 0 — Khoanh phạm vi (trước khi viết dày)

- [ ] Dán đề cương vào §0  
- [ ] Chốt **1 câu đóng góp chính** (ví dụ: *hybrid rule+LLM chuẩn hóa cây từ văn bản phiên âm Hán-Nôm, có đánh giá và hệ thống demo*)  
- [ ] Chốt **1 happy path demo** + **1–2 bộ dữ liệu mẫu** (tên cụ thể)  
- [ ] Liệt kê cái **không làm** trong luận văn (out of scope)

**Deliverable:** 1 trang “Phạm vi & đóng góp” (có thể tách file sau).

#### Phase 1 — Xương sống khoa học (L1)

- [ ] Khảo sát đặc trưng câu/quan hệ gia phả (hiện đại + cổ/phiên âm)  
- [ ] Khóa schema output trung gian + canonical (`people/relationships` → `BalkanNode`)  
- [ ] Bộ test case nhỏ (30–50 câu hoặc đoạn) + tiêu chí đúng/sai  
- [ ] Baseline rule-based + ghi failure cases  
- [ ] Mô tả hybrid (rule chắc / LLM chuẩn hóa) — đúng hướng đã chọn, chưa cần fine-tune  

**Deliverable:** chương cơ sở + thiết kế mô hình extract; bảng precision/recall sơ bộ.

#### Phase 2 — Hệ thống pipeline (L2) bám taxonomy

- [ ] Vẽ và đóng băng sơ đồ 5 tầng format (thô → trung gian → canonical → derived → export)  
- [ ] Mô tả pipeline 7 bước *ở mức luận văn* (không cần mọi API phụ)  
- [ ] Ràng buộc & validation cây (fid/mid/pids, không self-loop…)  
- [ ] Export tối thiểu phục vụ đánh giá (JSON/CSV/GEDCOM nếu đề cương cần)  

**Deliverable:** chương thiết kế hệ thống + ảnh chụp pipeline trên 1 cây mẫu.

#### Phase 3 — Tổ chức lại UI/flow cho luận văn (L3) — ưu tiên kể chuyện

Không cần redesign toàn app. Cần **đủ sạch để bảo vệ**:

- [ ] Viết user journey 6 bước (§4.2) vào luận văn + Guide page  
- [ ] Một màn hình “xử lý tư liệu → ra cây” đi được hết happy path  
- [ ] Một màn hình xem cây thống nhất (tránh demo 3 loại viewer)  
- [ ] Tách rõ trong slide: *Sản phẩm* vs *Công cụ nghiên cứu (crawl/dev)*  
- [ ] (Tuỳ sức) chỉnh IA menu cho khớp journey — chỉ những gì ảnh hưởng demo/bài  

**Deliverable:** chương giao diện / cài đặt thử nghiệm + kịch bản demo 5–7 phút.

#### Phase 4 — Thực nghiệm & viết

- [ ] Corpus đánh giá (tự gắn nhãn hoặc gold nhỏ)  
- [ ] So sánh: chỉ rule / chỉ LLM / hybrid (nếu đủ thời gian)  
- [ ] Case study 1–2 gia phả thật (Nom hoặc phả ký đã phiên âm)  
- [ ] Thảo luận lỗi (OCR, đồng tham chiếu tên, quan hệ mơ hồ)  
- [ ] Kết luận, hạn chế, hướng phát triển (fine-tune, corpus lớn, UI hợp nhất User–Admin)  

**Deliverable:** bản thảo đủ chương + phụ lục dữ liệu/test.

### 5.3. Thứ tự ưu tiên nếu thời gian hẹp

```text
1) Phạm vi + happy path + dữ liệu mẫu
2) Baseline extract có số liệu
3) Demo pipeline một cây sạch
4) Viết lý thuyết / thiết kế bám taxonomy
5) Chỉ rồi mới chỉnh sâu UI toàn cục
6) Crawl/tooling — chỉ khi phục vụ corpus hoặc phụ lục
```

### 5.4. Rủi ro & cách giảm

| Rủi ro | Cách giảm |
|--------|-----------|
| Phạm vi phình (crawl + NLP + UI đẹp) | Out-of-scope list; L3 chỉ phục vụ demo |
| Không đo được chất lượng extract | Test case nhỏ nhưng có evaluator sớm |
| Demo rối, hỏi đáp lạc đề | Một script demo cố định |
| Hai zone User/Admin | Luận văn mô tả kiến trúc đích; demo đi trên đường đã persist (thường là admin/public cây mẫu) |
| License viz (Balkan trial) | Free-only renderer cho demo chính thức |

---

## 6. Checklist “hết rối” cho chính bạn (cá nhân / luận văn)

Dùng như tiêu chí cảm nhận — khi trả lời được hết thì flow đã đủ rõ để viết & bảo vệ:

- [ ] Tôi giải thích được hệ thống trong **90 giây** không cần mở menu Developer.  
- [ ] Tôi chỉ ra **một** đường từ tư liệu → cây trên slide.  
- [ ] Tôi phân biệt được: extract thô / `BalkanNode` / màn hình xem.  
- [ ] Tôi nêu được **đóng góp** khác gì so với “chỉ gọi Gemini vẽ cây”.  
- [ ] Tôi có **bảng số** dù nhỏ (precision/recall hoặc case đúng/sai).  
- [ ] Tôi biết phần nào repo **không** đưa vào luận văn.

---

## 7. Việc bạn làm tiếp (không cần sửa code ngay)

1. **Dán đề cương** vào §0.  
2. Viết giúp (hoặc nhờ agent sau): bảng map *chương đề cương ↔ phase §5.2*.  
3. Chốt 1 câu đóng góp + 1 happy path + tên 1–2 tư liệu mẫu.  
4. Khi sẵn sàng implement: ưu tiên “làm rõ journey / Guide / demo path”, không refactor NLP lớn trước.

---

## 8. Tài liệu liên quan trong repo

| File | Dùng cho |
|------|----------|
| [business.md](../business.md) | Mục tiêu đề tài, nhóm công việc nghiệp vụ |
| [PROJECT.md](../PROJECT.md) | Kiến trúc, route, API |
| [FEATURES.md](../FEATURES.md) | Spec Guest/User/Admin, hai zone song song |
| [output_formats_and_ui_plan.md](./output_formats_and_ui_plan.md) | Taxonomy format, gap UI |
| [rule_based_genealogy_extraction_steps.md](./rule_based_genealogy_extraction_steps.md) | Plan rule-based Phase 1 |
| [visual_tree_ui_info_task.md](./visual_tree_ui_info_task.md) | Renderer / sơ đồ |
| [pipeline_step_detail_task.md](./pipeline_step_detail_task.md) | Pipeline 7 bước UI |
| [vietnamgiapha_122_data_flow.md](./vietnamgiapha_122_data_flow.md) | Ví dụ luồng dữ liệu VGP |

---

*File này là bản phân tích–kế hoạch làm việc. Chưa phải đề cương chính thức. Cập nhật §0 khi bạn có đề cương từ GVHD.*
