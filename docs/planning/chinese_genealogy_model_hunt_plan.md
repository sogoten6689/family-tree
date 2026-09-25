# Task — Săn mô hình gia phả Hán (Trung Quốc) có sẵn: chạy thử, đánh giá, đề xuất nâng cấp

> **Nguồn:** họp thầy 14/9/2026 mục 5 (`../lab/note_meeting_weekly/14_09_2026/phan_tich_hop_14_09_2026.md`) + yêu cầu 25/9/2026 (`../lab/note_meeting_weekly/25_09_2026/25_09_2026.md`)
> **Ngày tạo:** 2026-09-25 · **Trạng thái:** Sẵn sàng thực thi (T1–T3 không cần chờ thầy)
> **Người thực thi dự kiến:** Cursor Agent/Composer · **SSOT liên quan:** `nlp_family_extractor/ARCHITECTURE.md`, `genealogy_extraction_feature_set_plan.md`, `genealogy_feature_layers_deep_dive.md`

---

## 0. Cách dùng file này (đọc trước khi làm)

1. Thực thi **T1 → T2 → T3** tuần tự. **T4** chỉ làm nếu T3 kết luận có ứng viên khả thi (xem điều kiện ở T4).
2. Mọi output của T1–T3 nằm trong `research/model_survey/` (thư mục mới, tạo nếu chưa có). **Không sửa** bất kỳ file nào trong `nlp_family_extractor/app/` cho tới khi T4 được người dùng duyệt tường minh.
3. Ràng buộc license: candidate model/tool phải MIT / Apache-2.0 / BSD hoặc ghi rõ nếu không — tinh thần free-only của `.cursor/rules/free-only-visualization.mdc` áp dụng cho mọi dependency mới, không riêng visualization.
4. Phạm vi dữ liệu test: chỉ dùng câu tự viết dạng gia phả (tên, quan hệ cha/con/anh em, chức tước) — theo `.cursor/rules/gia-pha-only-analysis.mdc`, không dùng văn khế/tế văn/sắc phong.
5. Không bịa URL, không bịa số liệu. Nếu một bước thất bại, ghi lại lỗi thật thay vì bỏ qua bước.

---

## 1. Câu hỏi nghiên cứu (Question)

Có tồn tại mô hình/dataset/tool NLP mã nguồn mở, chạy được ngay hoặc fine-tune khả thi trong thời gian ngắn, xử lý gia phả chữ Hán (族谱/家谱 Trung Quốc) mà có thể tái sử dụng (transfer) cho pipeline Hán-Nôm Việt hiện tại không?

## 2. Trạng thái hiện tại (fact — đối chiếu code, không suy đoán)

| Quan sát | Bằng chứng |
|----------|-----------|
| Trích xuất quan hệ hiện là **rule-based regex** (`spouse_of`, `parent_of`, `sibling_of`), chưa dùng model NER/RE đã huấn luyện | `nlp_family_extractor/ARCHITECTURE.md` §3.2, đọc trực tiếp 2026-09-25 |
| Dịch nghĩa Hán-Nôm → Quốc ngữ dùng Gemini API (`gemini-3.5-flash-lite`), không có model dịch/NER cổ văn Hán riêng | `phan_tich_hop_14_09_2026.md` mục 4 |
| Chưa có tích hợp/khảo sát nào về mô hình gia phả Hán Trung Quốc trong repo | `grep -rn "族谱\|家谱" .` (2026-09-25) không có kết quả ngoài ghi chú họp |

**Suy ra (inference, không phải fact):** gap thật của pipeline là ở bước NER/RE (trích xuất tên + quan hệ), không phải OCR (đã có 5 engine vote) hay dịch nghĩa (đã dùng Gemini). → T1 nên ưu tiên khảo sát nhóm NER/RE trước.

## 3. Giả thuyết (phải kiểm chứng được bằng chạy thử thật, không chỉ đọc mô tả)

- **H1** — Tồn tại mô hình NER huấn luyện trên Hán cổ/Hán văn ngôn (ví dụ GuwenBERT, SikuBERT, hoặc tương tự) nhận diện được tên người + chức tước mà không cần fine-tune, đạt ≥50% recall tên người trên câu gia phả mẫu tự viết.
  - *Dự đoán nếu đúng:* chạy inference trực tiếp cho ra ≥50% tên/chức tước gắn nhãn đúng trên bộ mẫu T2.
  - *Dự đoán nếu sai:* model không chạy được (weight 404, dependency chết) hoặc miss phần lớn do domain gap (huấn luyện trên văn bia/sách khác gia phả).
- **H2** — Tồn tại tool/dataset chuyên biệt số hóa 家谱 có pipeline OCR→cây quan hệ hoàn chỉnh, đủ trưởng thành để tham khảo kiến trúc (không nhất thiết dùng lại weight).
  - *Dự đoán nếu đúng:* tìm được ≥1 repo có code chạy được, mô tả rõ input/output, cập nhật trong 3 năm gần đây.
  - *Dự đoán nếu sai:* chỉ có paper không code, hoặc code không chạy được.
- **H3 (null hypothesis)** — Không có mô hình/tool nào đủ trưởng thành để tái sử dụng trực tiếp; giá trị lớn nhất chỉ là tham khảo ý tưởng/feature engineering.
  - Đây là kết luận **mặc định** nếu H1 và H2 đều bị bác bỏ bằng bằng chứng chạy thử thật — không phải kết luận vì "khó tìm" hay hết thời gian.

---

## T1 — Khảo sát & lập danh sách ứng viên

**Mục tiêu:** ≥5 ứng viên (model/dataset/tool), chia 3 nhóm: (a) OCR cổ văn Hán, (b) NER/RE thân tộc/quan hệ, (c) dựng cây gia phả từ text.

**Từ khoá tìm kiếm gợi ý:** `族谱 NER`, `家谱 知识图谱`, `kinship extraction classical Chinese`, `GuwenBERT`, `SikuBERT genealogy`, `古文命名实体识别`, `genealogy chart generation NLP`, `Classical Chinese named entity recognition`.

**Output:** `research/model_survey/candidates.md` — bảng: | Tên | Link | Nhóm (a/b/c) | Có code chạy được? | License | Cập nhật gần nhất |

**Acceptance criteria**
- [ ] ≥5 ứng viên, mỗi dòng có link kiểm chứng được thật (không placeholder).
- [ ] Phân đúng 3 nhóm a/b/c.
- [ ] Ứng viên không có code bị đánh dấu rõ "loại khỏi T2".

## T2 — Chạy thử ứng viên tốt nhất (thực nghiệm thật, không đọc README rồi kết luận)

**Mục tiêu:** Chọn 1 ứng viên có code từ T1 (ưu tiên nhóm (b) NER/RE trước — đây là gap thật theo mục 2), clone và chạy inference thật.

```bash
mkdir -p research/model_survey/trial && cd research/model_survey/trial
git clone <candidate_url> <name>
python -m venv .venv && source .venv/bin/activate   # venv riêng, KHÔNG đụng venv chính
pip install -r requirements.txt   # hoặc theo hướng dẫn repo ứng viên
```

- Viết 10–20 câu test **tự soạn** bằng chữ Hán, dạng gia phả (vd. "某, 字某, 父某之子, 官某职, 生於某年") → lưu `research/model_survey/trial/sample_input.txt`.
- Chạy inference, lưu nguyên output tại `research/model_survey/trial/output_raw.json` (hoặc định dạng gốc của model).

**Acceptance criteria**
- [ ] Có bằng chứng chạy thật: lệnh đã chạy + file output tồn tại trên đĩa.
- [ ] Nếu **thất bại** (lỗi dependency/model không tải được/thiếu GPU...): ghi nguyên văn lỗi vào `research/model_survey/trial/ERROR.md`, không bỏ qua — chuyển sang ứng viên #2 trong T1.
- [ ] Tối đa 2 ứng viên trong T2. Nếu cả 2 fail → nghiêng về H3, ghi rõ lý do cụ thể (không viết chung chung "không chạy được") trong T3.

## T3 — Đánh giá bằng chứng (định lượng, không kết luận cảm tính)

**Cách làm:**
- Đếm thủ công trên `output_raw.json` đối chiếu `sample_input.txt`: số tên người nhận đúng / tổng số tên thật có → tỷ lệ %; số quan hệ thân tộc gắn đúng / tổng số quan hệ thật có → tỷ lệ %.
- Kiểm tra license: MIT/Apache/BSD = ok cho production; GPL/research-only/không ghi license = ghi rõ rủi ro, **không đề xuất tích hợp** vào production ở T4.
- Ước lượng effort tích hợp: Thấp (chạy ngay, license ok) / Trung bình (cần fine-tune) / Cao (viết lại phần lớn hoặc license chặn).

**Output:** `research/model_survey/EVALUATION.md` — bảng bắt buộc:

| Ứng viên | % tên đúng | % quan hệ đúng | License | Effort | Giả thuyết được ủng hộ | Độ tin cậy |
|----------|-----------|-----------------|---------|--------|------------------------|------------|

**Acceptance criteria**
- [ ] Mọi con số dẫn nguồn cụ thể (đếm tay trên `output_raw.json`, không phải ước lượng).
- [ ] Không có câu kết luận thiếu %/link bằng chứng.
- [ ] Nêu rõ giả thuyết nào bị bác bỏ, giả thuyết nào được ủng hộ.
- [ ] Nêu **một quan sát** có thể làm sai kết luận này nếu xuất hiện (falsification check) — vd. "nếu ứng viên #2 chạy được và đạt >70% thì đảo ngược kết luận".

## T4 — Đề xuất phương án nâng cấp (chỉ khi T3 ủng hộ H1 hoặc H2 với effort Thấp/Trung bình)

**Điều kiện bắt buộc trước khi bắt đầu T4:** T3 đã hoàn tất và tìm ra ≥1 ứng viên effort Thấp/Trung bình. Nếu T3 kết luận H3, **dừng ở T3**, không viết proposal cho có.

**Output:** `docs/planning/hannom_ner_model_upgrade_proposal.md`:
- Sơ đồ mermaid pipeline trước/sau.
- Điểm chèn cụ thể vào `nlp_family_extractor/app/extractor.py` (bước nào bị thay/bổ sung).
- Rủi ro (license, ToS nếu gọi API bên thứ ba, chi phí compute).
- Ước lượng effort theo giờ.

**Acceptance criteria**
- [ ] Có sơ đồ mermaid trước/sau.
- [ ] Có ≥1 rủi ro cụ thể nếu license ứng viên không rõ ràng.
- [ ] Không sửa code production trong bước này — chỉ file proposal.
- [ ] Ghi rõ dòng: "Chờ thầy duyệt trước khi implement."

---

## 5. Việc liên quan đã có kế hoạch riêng (không lặp lại nội dung ở đây)

| Việc | Xem tại |
|------|---------|
| Tìm thêm dữ liệu gia phả lâu năm (ưu tiên gốc Hán Nôm) | [firecrawl_genealogy_source_discovery_plan.md](./firecrawl_genealogy_source_discovery_plan.md) — đã cập nhật trạng thái blocked (thiếu `FIRECRAWL_API_KEY` thật), 2026-09-25 |
| Làm sạch/phân tích dữ liệu OCR đã vote (`runs/*.vote.json`) | Dataset nằm ở repo riêng `hannom-bilingual-dataset`, ngoài phạm vi repo `family-tree` — cần thêm repo vào scope trước khi làm |

## 6. Bảng tiến độ (cập nhật khi thực thi — không sửa số liệu tay, chỉ cập nhật khi có bằng chứng mới)

| Task | Trạng thái | Người/agent làm | Ngày cập nhật |
|------|-----------|-----------------|----------------|
| T1 | Đang chạy (agent nghiên cứu Claude, phiên 25/9) | Claude (background) | 2026-09-25 |
| T2 | Đang chạy song song với T1 | Claude (background) | 2026-09-25 |
| T3 | Chưa bắt đầu | | |
| T4 | Chờ T3 | | |

> Ghi chú: một agent Claude đã được giao chạy song song T1+T2 trong phiên 25/9 (kết quả sẽ nối vào `research/model_survey/` khi hoàn tất). Nếu Cursor bắt đầu làm T1 độc lập, kiểm tra `research/model_survey/` trước để tránh làm trùng — cập nhật bảng này thay vì tạo file trùng, theo `.cursor/rules/planning-tasks.mdc`.

## 7. Câu hỏi cần thầy xác nhận (không block T1–T3)

Xem đầy đủ tại `../lab/note_meeting_weekly/25_09_2026/25_09_2026.md`. Liên quan trực tiếp file này: "Ưu tiên loại mô hình gia phả Hán TQ nào — OCR / NER / dựng cây?" T1 mặc định khảo sát cả 3 nhóm để không phải chờ; T4 sẽ ưu tiên theo câu trả lời của thầy nếu có trước khi T4 bắt đầu.
