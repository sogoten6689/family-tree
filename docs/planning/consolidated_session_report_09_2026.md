# Báo cáo tổng hợp — Săn mô hình gia phả Hán + trao đổi nhóm (09/2026)

> **Vai trò:** Báo cáo SSOT gộp 2 luồng: việc tự làm trong tuần (25–28/9) và
> nội dung trao đổi với thầy/nhóm (14/9, 21/9). **Độc giả:** thầy hướng dẫn ·
> **Ngày:** 2026-09-28
> **Thay thế đọc rời:** [`chinese_genealogy_model_hunt_plan.md`](./chinese_genealogy_model_hunt_plan.md),
> [`hannom_ner_model_upgrade_proposal.md`](./hannom_ner_model_upgrade_proposal.md),
> [`../lab/note_meeting_weekly/14_09_2026/`](../lab/note_meeting_weekly/14_09_2026/),
> [`../lab/note_meeting_weekly/21_09_2026/`](../lab/note_meeting_weekly/21_09_2026/),
> [`../lab/note_meeting_weekly/25_09_2026/25_09_2026.md`](../lab/note_meeting_weekly/25_09_2026/25_09_2026.md)

---

## Tóm tắt điều hành

Thầy giao (14/9): "đi săn" mô hình có sẵn cho gia phả Hán Trung Quốc, chạy
thử, đánh giá. Tuần 25–28/9 đã làm xong việc đó với bằng chứng thực nghiệm
thật (không phải chỉ đọc paper). Song song, nhóm (báo cáo ~21/9, không rõ
ngày chính xác từng lượt) tự khảo sát một hướng rất gần — cổ văn Hán NLP nói
chung — và đã có phát hiện quan trọng: **tài khoản tác giả của chính model
tôi test tuần này (`guwen-ner`) có thể là người trong nhóm**, chưa xác
nhận. Kết luận chung của cả 2 luồng: **chưa có sản phẩm mã nguồn mở nào giải
quyết trực tiếp "gia phả Hán → cây quan hệ có cấu trúc"** — đây là điểm hội
tụ đáng báo thầy như một hướng đóng góp học thuật, không phải một khoảng
trống do tìm chưa đủ.

---

## 1. Công việc tuần qua đã làm (25–28/9, Claude + Lâm + Cursor)

### 1.1 Task backlog & tài liệu quản lý

- Đọc ghi chú họp 14/9, tạo backlog 9 việc (task tracker phiên này).
- Viết task spec chi tiết cho Cursor:
  [`chinese_genealogy_model_hunt_plan.md`](./chinese_genealogy_model_hunt_plan.md)
  — câu hỏi nghiên cứu, 3 giả thuyết H1/H2/H3, T1→T4 có acceptance criteria.

### 1.2 T1 — Khảo sát 12 ứng viên (OCR / NER / KG quan hệ / quản lý cây)

Không tìm được ứng viên nào giải quyết trực tiếp bài toán. Danh sách đầy đủ:
[`research/model_survey/candidates.md`](../../research/model_survey/candidates.md).

### 1.3 T2+T3 — Chạy thử thật + đánh giá

| Ứng viên | Kết quả (fact) | License |
|---|---|---|
| `CHAT_models` (kraken OCR Hán cổ) | 0% đúng với `kraken` mới nhất (7.1.1) → sau khi ghim `kraken<5`, **đọc được văn bản có nghĩa thật** (thơ cổ điển, tên tác giả xác minh được) — **H2 xác nhận**: lỗi do version mismatch, không phải model kém | CC BY-NC 4.0 (cấm thương mại) |
| `guwen-ner` | **[Cập nhật sau Colab]** 0/4 trên 1 câu tự soạn, nhưng **95%/97.5% (phồn/giản)** trên 9 đoạn Sử Ký thật — kết luận ban đầu "yếu trên phồn thể" bị bác bỏ, chỉ đúng cho mẫu n=1 | Apache-2.0 |
| `Jiayan` | Tách từ đúng ranh giới ở cả phồn/giản thể | MIT |

Chi tiết đầy đủ + log thật: [`research/model_survey/EVALUATION.md`](../../research/model_survey/EVALUATION.md).

### 1.4 T4 — Proposal nâng cấp

[`hannom_ner_model_upgrade_proposal.md`](./hannom_ner_model_upgrade_proposal.md)
— đề xuất bổ sung `guwen-ner` (có tiền xử lý phồn→giản) song song với rule-
based hiện tại, không xoá rule-based. Chưa implement, **chờ thầy duyệt**.

### 1.5 Thực nghiệm mở rộng trên Google Colab — hoàn tất, có 1 phát hiện đảo ngược kết luận cũ

Notebook [`research/model_survey/colab/hannom_model_experiments.ipynb`](../../research/model_survey/colab/hannom_model_experiments.ipynb)
đã chạy xong trên GPU Tesla T4 (không bị chặn egress). Kết quả (bằng chứng: [`research/model_survey/colab/results/`](../../research/model_survey/colab/results/)):

- **Nhóm A (falsification check guwen-ner):** trên 9 đoạn Sử Ký thật (Kanripo, pin commit), recall tên người đạt **95% phồn thể / 97.5% giản thể** — gần như ngang nhau. **Kết luận tuần trước "guwen-ner gần như vô dụng trên phồn thể" bị bác bỏ** — kết luận đó chỉ đúng cho đúng 1 câu tự soạn (n=1, không đại diện). Vẫn thiếu: test trên câu/đoạn gia phả Hán-Nôm thật.
- **Nhóm B (SikuBERT vs GuwenBERT):** cả 2 xác nhận license Apache-2.0. SikuBERT có **0% ký tự lỗi (`[UNK]`) trên phồn thể** so với **~20% của GuwenBERT** — xác nhận SikuBERT là nền tảng tốt hơn để fine-tune tiếp.
- **Nhóm C (benchmark GPU):** GPU nhanh hơn CPU **37.8 lần** (601s → 15.9s/trang, cùng máy). Tái lập thành công H2 lần 2 (3 chuỗi mốc từ log 27/9 xuất hiện lại). `ketos train/segtrain` lỗi cú pháp CLI (`-q fixed` sai, phải `-q dumb`) — chưa đo được tốc độ fine-tune.

### 1.6 Hạn chế hạ tầng phát hiện được

Sandbox Claude Code cloud chặn egress tới `huggingface.co`, `modelscope.cn`,
`drive.google.com`, `zenodo.org`, và cả các domain xuất bản học thuật
(`link.springer.com`, `emerald.com`, `projects.iq.harvard.edu`) — chỉ
`github.com`/`pypi.org` truy cập được. Đây là lý do phải chuyển thực nghiệm
sang Google Colab (không bị chặn, có GPU).

---

## 2. Công việc thầy trao đổi

### 2.1 Họp 14/9 — yêu cầu gốc

Chi tiết: [`../lab/note_meeting_weekly/14_09_2026/phan_tich_hop_14_09_2026.md`](../lab/note_meeting_weekly/14_09_2026/phan_tich_hop_14_09_2026.md).

| Mục thầy giao | Trạng thái |
|---|---|
| Sửa vote OCR bắt buộc theo câu (Levenshtein MED) | ✅ Đã làm trước tuần này (`vote_ocr.py`, rapidfuzz) |
| Tìm mô hình có sẵn gia phả Hán TQ, chạy thử | ✅ Làm xong tuần này — xem mục 1 |
| Ưu tiên gia phả lâu năm (gốc Hán Nôm) | ⏸ Blocked — thiếu `FIRECRAWL_API_KEY` thật để chạy `research/source_discovery/` |
| Gia phả Nguyễn Phước (thầy có quen) | ⏳ Chờ thầy kết nối |
| "Fake API" Gemini/ChatGPT | ⚠️ Rủi ro ToS — Claude đã từ chối tích hợp `Fake_ChatGPT_API/`, chờ thầy xác nhận hướng đi hợp lệ |
| "Bài toán song song" (dữ liệu song ngữ hay xử lý đa luồng?) | ❓ Chưa rõ, cần thầy nói lại |

### 2.2 Báo cáo nhóm 21/9 — phát hiện song song, liên quan trực tiếp

Chi tiết: [`../lab/note_meeting_weekly/21_09_2026/`](../lab/note_meeting_weekly/21_09_2026/)
(bản gốc + phân tích đối chiếu).

**Phát hiện nổi bật nhất:** tài khoản `ethanyt` (tác giả `guwen-ner`,
`guwen-seg`, `guwen-punc` mà tuần này coi là "ứng viên bên thứ ba") có thể
là **thành viên trong nhóm** — một bạn tự nhận đã fine-tune `guwen-seg`/
`guwen-punc` dưới đúng tài khoản đó. **Chưa xác nhận** — cần hỏi thầy/nhóm.

**Bằng chứng hội tụ về GuwenBERT yếu hơn SikuBERT (đã xác nhận bằng thực nghiệm Colab, không còn là suy luận):**
- Nhóm đo `guwen-punc` thủ công: F1 = 0.195 → kết luận overfitting.
- Colab (Nhóm B, xem mục 1.5): GuwenBERT ~20% ký tự lỗi (`[UNK]`) trên phồn thể, SikuBERT 0%.
- 1 bài báo ngoài (*Spring and Autumn Annals*, doi:10.1093/llc/fqad016) xác
  nhận GuwenBERT thua SikuBERT/SikuRoBERTa trên segmentation.
→ Cả 3 nguồn độc lập đều chỉ về cùng 1 hướng: **nên ưu tiên SikuBERT hơn
GuwenBERT** làm nền tảng fine-tune. (Lưu ý: đây khác với năng lực NER nói
chung của guwen-ner, thứ mà mục 1.5 vừa xác nhận là tốt trên văn bản thật —
2 phát hiện không mâu thuẫn nhau, chỉ là 2 khía cạnh khác nhau của cùng họ
model GuwenBERT.)

**Ứng viên/tài nguyên mới nhóm tìm được, chưa có trong `candidates.md`:**
- **XunziLLM** — LLM ~7B (fine-tune Qwen/ChatGLM3/Baichuan2), làm được
  information extraction (người/sự kiện/địa điểm) — tiềm năng hơn hẳn các
  model ~100-300M đã test, nhưng license chưa rõ, host ModelScope (bị chặn
  ở sandbox này).
- **Bài CBDB "kinship normalization"** — chuẩn hóa quan hệ huyết thống Hán
  cổ về 3 loại cơ bản (cha-con, mẹ-con, chồng-vợ) — **trùng thiết kế hiện
  tại** của `nlp_family_extractor` (`spouse_of`/`parent_of`/`sibling_of`).
- **DSNF (Dependency Semantic Normal Forms)** — hướng rule-based trích quan
  hệ dựa cấu trúc phụ thuộc ngữ pháp, không cần dữ liệu gán nhãn — có thể bổ
  sung cho rule-based hiện tại thay vì chỉ tìm model học sâu.
- 2 nguồn gia phả Việt Nam mới (sách *Lịch sử họ Nguyễn Việt Nam*, web *Phả
  hệ – Tộc họ Nguyễn Bặc*) — chưa đưa vào `firecrawl_genealogy_source_discovery_plan.md`.

**Việc null nhóm đã thử, khỏi lặp lại:** FastHan chết (cần tài khoản Baidu,
SĐT Trung Quốc); NomNaOCR không có nhãn dấu câu; tích hợp "tri thức từ
điển" vào model không cải thiện (F1 0.7 ngang bằng).

---

## 3. Câu hỏi tổng hợp cần thầy trả lời (gộp cả 2 luồng)

1. `ethanyt` có phải thành viên trong nhóm không? (ưu tiên cao nhất)
2. Xin giúp truy cập 2 bài báo bị chặn: CBDB kinship normalization (Harvard)
   và "framework of genealogy knowledge reasoning" (Emerald).
3. Ưu tiên gia phả Nguyễn Phước — khi nào kết nối được?
4. "Fake API" Gemini/ChatGPT — hướng xử lý hợp lệ thay thế?
5. "Bài toán song song" nghĩa là gì?
6. Cần `FIRECRAWL_API_KEY` thật để tiếp tục tìm nguồn gia phả lâu năm.

## 4. Việc tiếp theo không cần chờ thầy

- Đợi Lâm chạy xong notebook Colab → Claude đọc trực tiếp, cập nhật kết
  luận cuối trong `EVALUATION.md`.
- Gộp XunziLLM + bài CBDB + 2 nguồn gia phả Nguyễn vào `candidates.md` /
  `firecrawl_genealogy_source_discovery_plan.md` (đã đề xuất, chờ Lâm xác
  nhận).
