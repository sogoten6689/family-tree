# Định hướng nghiên cứu đề tài — tổng hợp chỉ đạo của thầy (đến 14/09/2026)

> **Vai trò file:** ghi lại quá trình suy luận từ ghi chú họp (evidence) → giả thuyết về đề tài đích mà thầy đang dẫn tới → đề xuất hướng đi cụ thể, có thể kiểm định. Không thay thế đề cương chính thức. Theo khung khoa học của repo: fact / inference / hypothesis được tách rõ, độ tin cậy được ghi kèm.
>
> **Cập nhật:** 2026-09-28 (bổ sung 21/09) · **Nguồn:** `docs/lab/note_meeting_weekly/*` (20/07 → 21/09/2026), `docs/thesis/business.md`, `docs/thesis/RESEARCH_SOURCES.md`.
>
> **Lưu ý về nguồn 21/09:** hai file `21_09_2026/21_09_2026.md` và `21_09_2026/phan_tich_hop_21_09_2026.md`, cùng với `research/model_survey/{candidates.md,EVALUATION.md,BAO_CAO_DANH_GIA_CHAT_MODELS.md}` và `docs/planning/chinese_genealogy_model_hunt_plan.md`, **chưa có trên nhánh làm việc hiện tại** (`claude/busy-planck-bb0lwd`) — chúng nằm trên nhánh song song `origin/claude/meeting-project-evaluation-eui68s` (phiên Claude khác, session khác). Nội dung dưới đây được đọc trực tiếp từ nhánh đó (`git show origin/...:<path>`) để tổng hợp, nhưng **chưa merge** vào nhánh này — nếu cần dùng lại các file gốc, phải merge/checkout nhánh đó trước.

---

## 1. Câu hỏi nghiên cứu (Research Question)

Đề tài gốc (`business.md`, 2026) đặt câu hỏi hẹp: *"Làm sao tự động dựng cây gia phả từ văn bản gia phả Hán Nôm?"* — một pipeline OCR → trích xuất thực thể/quan hệ → cây.

Bằng chứng từ các buổi họp (§2 dưới) cho thấy thầy đã **mở rộng** câu hỏi này thành một bài toán hai tầng, không mâu thuẫn với đề tài gốc nhưng đổi trọng tâm khoa học:

> **RQ đích (suy luận, độ tin cậy cao):** *Làm sao xây dựng một corpus song ngữ Hán Nôm–Việt (gia phả) đủ lớn và đủ đại diện, dùng ensemble OCR + voting có kiểm chứng thống kê, để (a) fine-tune một mô hình dịch nghĩa chuyên biệt lĩnh vực gia phả, và (b) làm nền dữ liệu cho một mô hình trích xuất thực thể/quan hệ/đồ thị tri thức, từ đó tự động sinh cây gia phả — có đối chiếu với mô hình/dataset gia phả Hán (Trung Quốc) đã có để đánh giá khả năng kế thừa (transfer)?*

Đây là **giả thuyết**, không phải đề cương đã thầy xác nhận bằng lời — cần thầy chốt (xem §6).

---

## 2. Bằng chứng — timeline chỉ đạo của thầy (fact, có trích dẫn)

| Ngày | Chỉ đạo (nguyên văn/tóm tắt) | Nguồn |
|------|------------------------------|-------|
| 24/08–31/08 | "OCR → dịch âm → dịch nghĩa → hình thành cây gia phả!"; mixing 5 engine OCR (paddle v6, deepseek, clc, google vision, gemini); dịch nghĩa dùng Qwen 3.6 37B, **sau này fine-tuning**; các LV khác (lịch sử, Phật học, YHDT, văn bia, sắc phong...) cũng được giao thử fine-tune Qwen trên dataset riêng | `31_08_2026/31_08_2026.md:8-14` |
| 31/08–07/09 | Cần tiêu chí phân loại lớn hơn (tông phả/tộc phả/chi phả × bộ/đồ/ký/điệp) để **thu thập có tính đại diện, cân bằng**, không lệch mẫu; "từ kho data tiếng việt, xây dựng mô hình trên **văn phong, NER và đồ thị tri thức**"; "khi có bản hán nôm, có bản dịch việt (còn lủng củng), dùng mô hình trên **chỉnh**" (mô hình NER/văn phong dùng để hiệu đính bản dịch thô) | `31_08_2026/31_08_2026.md:19-83` |
| 14/09 | Sửa vote OCR sang cấp câu/dòng bằng Levenshtein MED (đã làm 15/09); tìm mô hình gia phả Hán **Trung Quốc** có sẵn, "đi săn" bằng Claude rồi chạy thử; ưu tiên gia phả **lâu năm** (gốc có Hán Nôm); gợi ý nguồn mới — gia phả **Nguyễn Phước**; "hướng tới bài toán **song song**, dịch và song song" | `14_09_2026/14_09_2026.md`, `14_09_2026/phan_tich_hop_14_09_2026.md` |
| 21/09 | Tổng hợp báo cáo nhiều thành viên khác trong nhóm (không chỉ mình): kết quả "đi săn" mô hình gia phả Hán TQ — FastHan chết (cần acc Baidu); Chinese Open RE (DSNF, ACM 2018, rule-based dependency parsing, unsupervised); bài **CBDB kinship normalization** (chuẩn hoá quan hệ thân tộc Hán tiền-hiện-đại về 3 quan hệ cơ bản cha-con/mẹ-con/chồng-vợ — khớp trực tiếp thiết kế rule hiện tại); **XunziLLM** (7B, fine-tune từ Qwen, làm được IE người/sự kiện/địa điểm, host ModelScope, license chưa rõ); benchmark **EvaHan**/`daizhigev20`/ACLUE; đo được `guwen-punc` overfitting (F1 0.195); có thành viên khác tự fine-tune GuwenBERT (seg+punc) nhưng một bài báo ngoài đo được **GuwenBERT thua SikuBERT/SikuRoBERTa**; 2 nguồn gia phả Nguyễn mới (Lịch sử họ Nguyễn VN; Phả hệ Tộc họ Nguyễn Bặc) | `21_09_2026/21_09_2026.md`, `21_09_2026/phan_tich_hop_21_09_2026.md` (nhánh `claude/meeting-project-evaluation-eui68s`) |

**Quan sát bổ sung (fact, không phải chỉ đạo trực tiếp nhưng liên quan):** báo cáo 15/09 (`phan_tich_hop_14_09_2026.md:136-172`) cho thấy việc đo win-rate OCR theo "khớp đa số" từng có lỗ hổng phương pháp (2 engine cùng sai vẫn thắng vote) — đã được phát hiện và sửa bằng xếp hạng động theo độ giống nhau thật (`rank_by_similarity`). Đây là một ví dụ cụ thể trong repo về đúng tinh thần "tìm bằng chứng phản bác giả thuyết ưu tiên" mà khung khoa học của repo yêu cầu — nên giữ làm mẫu cho phần đánh giá (evaluation) của luận văn.

---

## 3. Phân tích: sợi chỉ xuyên suốt vs. điểm còn mơ hồ

### 3.1. Sợi chỉ xuyên suốt (pattern nhất quán qua 3 buổi họp — độ tin cậy cao)

1. **Trọng tâm đã dịch chuyển từ "demo cây gia phả" sang "hạ tầng dữ liệu + mô hình dùng lại được"**: corpus song ngữ có phân loại, có OCR ensemble đo được, có fine-tuning — không chỉ gọi Gemini một lần rồi vẽ cây.
2. **Kiến trúc 2 mô hình, không phải 1**: (i) mô hình dịch nghĩa (Qwen, fine-tune theo domain gia phả) và (ii) mô hình trích xuất tri thức (NER + quan hệ + graph, học trên kho tiếng Việt) dùng để **hiệu đính** bản dịch thô — hai việc khác nhau, dễ nhầm là một.
3. **Tiêu chí thu thập dữ liệu ưu tiên bản gốc Hán Nôm còn tồn**, có phân loại tông/tộc/chi phả để tránh lệch mẫu — đúng phương pháp lấy mẫu có kiểm soát (stratified sampling), không phải "vơ càng nhiều càng tốt".
4. **Định vị trong nhóm lớn hơn**: nhiều LV khác đang làm cùng bài toán dịch nghĩa Hán cho các domain khác (Phật học, YHDT, văn bia...) trên cùng model Qwen — nghĩa là **đóng góp riêng của đề tài này nằm ở domain gia phả + phần trích xuất quan hệ/dựng cây**, không phải ở việc "có dùng Qwen hay không" (phần đó là hạ tầng chung).

### 3.2. Điểm mơ hồ — **không nên tự suy đoán tiếp**, cần thầy xác nhận

Bốn điểm này *(mục 5, 6, 7-liên-quan, 9 trong `phan_tich_hop_14_09_2026.md`)* ảnh hưởng trực tiếp đến việc chốt đề tài, nên liệt lại ở đây làm điều kiện tiên quyết trước khi viết đề cương chính thức:

- **(a)** Mô hình gia phả Hán Trung Quốc cần tìm: OCR chữ Hán cổ, hay NER/RE quan hệ gia đình, hay mô hình sinh cây trực tiếp? → quyết định phạm vi "đi săn" khác nhau rất nhiều.
- **(b)** "Gia phả xoay quanh nó, gần với mình để kế thừa, tự động hình [thành cây]" — câu bị cắt, chưa rõ ý đầy đủ. Đây có thể là chìa khóa cho **đóng góp chính** (transfer learning từ mô hình Hán TQ → gia phả Việt), nên **không được đoán và triển khai** trước khi thầy xác nhận lại nguyên văn.
- **(c)** "Bài toán song song" — dữ liệu song ngữ (parallel corpus) hay xử lý đa luồng (parallelization)? Hai hướng này tốn công rất khác nhau (một là NLP/data, một là kỹ thuật hệ thống) — cần biết trước khi phân bổ thời gian.
- **(d)** Gia phả Nguyễn Phước — nguồn mới qua quan hệ cá nhân của thầy; cần biết mốc thời gian tiếp cận được để đưa vào kế hoạch corpus (nếu đến muộn, không nên đặt làm case study chính).

**Kết luận của mục này:** phần OCR-ensemble + voting (đã làm) và phần phân loại corpus (đã có sơ đồ mã hoá) là **chắc chắn**, có thể viết vào luận văn ngay. Phần "song song" (điểm c) vẫn **chưa đủ bằng chứng**. Điểm (a) — loại mô hình Hán TQ cần tìm — nay đã có bằng chứng thực nghiệm đáng kể, xem §3.3.

### 3.3. Cập nhật 21/09 — kết quả "đi săn" mô hình gia phả Hán TQ (T1–T3, trả lời một phần câu hỏi 3.2-a)

Một phiên Claude khác (nhánh `claude/meeting-project-evaluation-eui68s`) đã thực hiện có hệ thống `docs/planning/chinese_genealogy_model_hunt_plan.md` (T1 khảo sát → T2/T3 chạy thử + tái lập độc lập 27/09). Đây là **fact có log/kết quả chạy thật**, không phải suy đoán:

**Phát hiện quan trọng nhất (High confidence):** *không tồn tại mô hình/dataset mã nguồn mở nào giải quyết trực tiếp bài toán "gia phả Hán TQ → cây gia phả có cấu trúc"* — khảo sát có hệ thống trên nhiều từ khoá, không tìm được. Đây **không phải tin xấu cho luận văn** — nó là bằng chứng củng cố khoảng trống học thuật (research gap) mà câu đóng góp ở §4 nhắm tới: nếu đã có sẵn, luận văn mất giá trị mới; vì chưa có, việc tự xây (L2) có cơ sở đóng góp thật.

**Bảng ứng viên đã chạy thử (rút gọn, xem `research/model_survey/EVALUATION.md` trên nhánh kia để đủ chi tiết):**

| Ứng viên | Việc làm được | Kết quả trên chữ **phồn thể** (đúng dạng Hán-Nôm thật) | License | Vai trò khả thi trong pipeline |
|---|---|---|---|---|
| **Jiayan** (甲言) | Tách từ, POS cổ văn | Tách đúng `知府`, `阮氏` — **không nhạy phồn/giản thể** | MIT | Bước tiền xử lý (word segmentation) trước NER — đáng dùng |
| **guwen-ner** (GuwenBERT) | NER cổ văn | **0/4 thực thể** trên phồn thể (chỉ được 3/4 nếu ép về giản thể — rủi ro sai nghĩa với chữ Nôm) | Apache-2.0 | Gần như vô dụng nếu không tiền xử lý phồn→giản có kiểm soát; có bằng chứng ngoài (bài *Spring and Autumn Annals*) cho thấy cả họ GuwenBERT thua SikuBERT/SikuRoBERTa |
| **CHAT_models** (kraken OCR) | OCR Hán cổ dọc | Đọc được phần lớn văn bản có nghĩa **nếu ghim `kraken<5`** (bug tương thích version, đã tái lập 27/9) | **CC BY-NC 4.0 — cấm thương mại** | Baseline OCR khả thi cho mục đích luận văn (phi thương mại) |
| **XunziLLM** | Tách câu, chấm câu, **IE người/sự kiện/địa điểm**, dịch | Chưa chạy thử được (host ModelScope, bị chặn egress trong sandbox cloud) | Chưa rõ — cần xác nhận trước khi dùng | Ứng viên **tiềm năng nhất** cho đúng việc L2 (trích xuất), nhưng chưa kiểm chứng |
| **DSNF** (Chinese Open RE, ACM 2018) | Trích quan hệ không cần nhãn (dựa dependency parsing) | Chưa chạy thử (chỉ đọc abstract, bài đầy đủ bị chặn) | — | Hướng rule-based nâng cao, bổ sung cho rule hiện tại thay vì thay bằng deep model |
| **CBDB kinship normalization** (bài, Harvard) | Chuẩn hoá quan hệ thân tộc Hán tiền-hiện-đại | Chuẩn hoá về **3 quan hệ cơ bản: cha–con, mẹ–con, chồng–vợ** | — (bài báo, không phải code) | **Khớp trực tiếp** với thiết kế rule hiện tại của `nlp_family_extractor` (`spouse_of`/`parent_of`/`sibling_of`) — nên trích dẫn làm cơ sở lý thuyết cho chương thiết kế quan hệ |

**Kiến trúc pipeline gợi ý cho L2 (suy luận từ bảng trên, độ tin cậy trung bình — chưa test end-to-end):** Jiayan (tách từ) → guwen-ner hoặc XunziLLM (NER/IE, cần xác nhận license/chạy thử XunziLLM ở máy không bị chặn ModelScope) → rule chuẩn hoá quan hệ theo khung CBDB (3 quan hệ cơ bản, khớp code hiện tại) → graph/cây. Đây **không phải transfer learning trực tiếp một mô hình có sẵn** như câu hỏi 3.2-b có thể ngụ ý — mà là **ghép nhiều thành phần mã nguồn mở** (tiền xử lý + NER) với **rule tự thiết kế** — nên câu hỏi 3.2-b (thầy có ý gì khác không) vẫn cần xác nhận, không nên coi đã trả lời xong.

**Hạn chế cần nêu trung thực:** phần lớn kết quả trên chạy trên **câu mẫu tự tạo** (1 câu, không phải corpus gia phả Hán-Nôm thật), và môi trường sandbox cloud bị chặn egress tới HuggingFace/ModelScope/Google Drive — nhiều ứng viên (SikuBERT, XunziLLM) **chưa chạy thử được**, chỉ mới đọc README/paper. Không nên trích số liệu này như benchmark cuối cùng.

**Phát hiện phụ cần thầy xác nhận (ưu tiên cao, ảnh hưởng cách tiếp cận nhóm):** ghi chú 21/09 gợi ý tài khoản `ethanyt` (tác giả `guwen-ner`/`guwen-seg`/`guwen-punc` trên HuggingFace/GitHub) **có thể là một thành viên trong nhóm nghiên cứu của thầy** (trùng câu tường thuật "em có fine-tuning 2 model... dựa trên GuwenBERT"). Nếu đúng, nên hỏi trực tiếp người đó thay vì tiếp tục suy luận từ bên ngoài — xem §6 câu hỏi mới.

---

## 4. Đề xuất hướng đi cụ thể (đề tài đích, khung 3 lớp đóng góp)

Kế thừa khung "3 lớp đóng góp" đã có trong `docs/planning/luan_van_phan_tich_va_ke_hoach.md` (§5.1), cập nhật theo chỉ đạo mới:

| Lớp | Nội dung cập nhật theo thầy | Vai trò luận văn |
|-----|------------------------------|-------------------|
| **L0 — Corpus (mới, nay là xương sống)** | Thu thập có phân loại (tông/tộc/chi phả × bộ/đồ/ký/điệp), ưu tiên bản gốc Hán Nôm còn tồn; OCR ensemble 5 engine + vote cấp câu bằng Levenshtein MED (đã làm, đo được); alignment song ngữ Hán–Việt | **Đóng góp về phương pháp thu thập & đánh giá corpus** — có thể viết thành 1 chương độc lập, có số liệu (mean OCR theo loại chữ, tỉ lệ thắng vote theo engine) |
| **L1 — Mô hình dịch nghĩa** | Fine-tune Qwen 3.6 37B trên domain gia phả (khác domain của các LV khác dùng chung model) | So sánh baseline (Qwen chưa fine-tune / Gemini) vs. fine-tuned trên tập test gia phả — đây là thực nghiệm có số liệu rõ, làm được sớm |
| **L2 — Mô hình trích xuất & dựng cây** | NER + quan hệ + đồ thị tri thức học trên kho tiếng Việt (đã dịch), dùng để hiệu đính bản dịch thô và sinh cây; đã xác nhận (21/09, §3.3) **không có mô hình mã nguồn mở nào giải quyết trực tiếp** bài toán này — khoảng trống này chính là chỗ đóng góp; kiến trúc ghép linh kiện (Jiayan + guwen-ner/XunziLLM + rule chuẩn hoá theo khung CBDB) là hướng khả thi nhất hiện có, chưa kiểm chứng end-to-end | **Core khoa học** của riêng đề tài — khác biệt với các LV domain khác đang chỉ dừng ở dịch nghĩa |
| **L3 — Sản phẩm minh họa** | Hệ thống web hiện có (`family-saga-io` + `nlp_family_extractor`) dùng để **demo** happy path, không phải nơi đặt đóng góp khoa học | Minh họa & kiểm chứng sử dụng, giữ nguyên vai trò như plan cũ |

**Câu đóng góp đề xuất (1 câu, để chốt với thầy):**

> *"Xây dựng và đánh giá một corpus song ngữ Hán Nôm–Việt lĩnh vực gia phả (thu thập có phân loại, OCR ensemble có kiểm định thống kê), dùng làm nền fine-tune mô hình dịch nghĩa chuyên biệt và huấn luyện mô hình trích xuất thực thể–quan hệ để tự động sinh cây gia phả, có so sánh với hướng kế thừa từ mô hình gia phả Hán hiện có."*

Câu này **giữ được** phần đã làm chắc (OCR/vote/phân loại — đã có số liệu), **nối được** với yêu cầu chung của lab (fine-tune Qwen), và **để ngỏ đúng chỗ** cho phần transfer-learning Hán TQ mà thầy gợi ý nhưng chưa xác nhận rõ.

---

## 5. Kế hoạch tối thiểu để kiểm định hướng đi (trước khi viết dày)

Theo tinh thần "thực nghiệm nhỏ nhất phân biệt được giả thuyết":

1. **Kiểm định L0 đã đủ chưa để viết chương corpus:** tổng hợp lại số liệu vote OCR đã có (win-rate theo engine, theo loại chữ in/thảo) thành 1 bảng — đã có dữ liệu thô trong `hannom-bilingual-dataset` (repo khác), chỉ cần tổng hợp.
2. **Kiểm định L1 khả thi trong thời gian còn lại:** chạy fine-tune Qwen trên **một tập nhỏ đã hiệu đính** (không phải toàn bộ), so BLEU/human-eval với Qwen gốc và Gemini — nếu chưa có API Qwen thì đây là **blocker cần thầy giải quyết trước** (đã ghi trong `bao_cao_thay.md:34-40`).
3. **Kiểm định L2 (transfer Hán TQ) — đã có kết quả vòng 1 (§3.3):** khảo sát + chạy thử đã xong (T1–T3, nhánh song song) — kết luận không có mô hình end-to-end sẵn, có vài linh kiện dùng được (Jiayan, guwen-ner có điều kiện, CHAT_models phi thương mại). **Việc tiếp theo:** (i) merge hoặc đọc lại đầy đủ nhánh `claude/meeting-project-evaluation-eui68s` để không lặp lại khảo sát; (ii) test XunziLLM ở máy không bị chặn ModelScope trước khi quyết định dùng; (iii) nếu không dùng được linh kiện ngoài, L2 vẫn đứng độc lập bằng train-from-scratch trên corpus tiếng Việt đã dịch, theo khung 3-quan-hệ của CBDB.
4. **Không làm trước khi thầy xác nhận:** bất kỳ việc "tự động hoá UI Gemini/ChatGPT để né quota" — đã có rủi ro vi phạm ToS được ghi nhận (`phan_tich_hop_14_09_2026.md:174-180`), không nên đưa vào pipeline chính thức của luận văn dù có sẵn code thử nghiệm.

---

## 6. Câu hỏi cần thầy xác nhận trước khi chốt đề cương

(Giữ nguyên danh sách đã tổng hợp ở `docs/lab/note_meeting_weekly/14_09_2026/phan_tich_hop_14_09_2026.md`, không lặp lại phân tích — chỉ trích các câu **ảnh hưởng trực tiếp đến phạm vi đề tài**, không phải chi tiết kỹ thuật đã xử lý xong):

1. ~~Ưu tiên loại mô hình gia phả Hán TQ nào~~ — **đã có dữ liệu vòng 1** (§3.3): không có mô hình end-to-end sẵn; câu hỏi còn lại là thầy có đồng ý hướng "ghép linh kiện mã nguồn mở + rule tự thiết kế" (Jiayan + guwen-ner/XunziLLM + khung CBDB) thay vì chờ tìm một mô hình transfer trực tiếp không.
2. Ý đầy đủ của "gia phả xoay quanh nó... tự động hình [thành cây]" — vẫn cần nguyên văn; §3.3 cho thấy đây khó là transfer 1 mô hình có sẵn (vì không tồn tại), nên có thể ý thầy khác với suy đoán ban đầu — **ưu tiên hỏi lại, không giả định tiếp**.
3. "Bài toán song song" = dữ liệu song ngữ, xử lý đa luồng, hay cả hai — quyết định có đưa hệ thống-hoá (parallel compute) vào luận văn hay không.
4. Timeline tiếp cận gia phả Nguyễn Phước — quyết định có dùng làm case study chính thức hay chỉ phụ lục. (21/09 đã có thêm 2 nguồn Nguyễn khác qua khảo sát web, có thể dùng tạm trong lúc chờ.)
5. Câu đóng góp 1-câu ở §4 có đúng ý thầy không, hay cần điều chỉnh trọng số giữa L1 (dịch nghĩa, việc chung cả nhóm LV) và L2 (trích xuất/dựng cây, phần riêng của đề tài này)?
6. **Mới (21/09):** tài khoản `ethanyt` (tác giả các model `guwen-*`) có phải một thành viên trong nhóm nghiên cứu của thầy không? Nếu đúng, nên hỏi trực tiếp về hiệu năng thật trên phồn thể thay vì chỉ suy luận từ benchmark ngoài — xem §3.3.
7. **Mới:** nhánh `claude/meeting-project-evaluation-eui68s` đang chạy song song với nhánh này (`claude/busy-planck-bb0lwd`) — có nên hợp nhất (merge) hai luồng công việc lại, hay chủ đích giữ tách (một nhánh lo định hướng/tổng hợp, một nhánh lo khảo sát mô hình kỹ thuật)?

---

## 7. Độ tin cậy tổng thể

- **Cao:** §2 (timeline chỉ đạo — trích trực tiếp), §3.1 (pattern nhất quán qua 4 buổi họp độc lập), phần "đã làm" của L0 (có code, có số liệu), phát hiện "không có mô hình end-to-end sẵn" ở §3.3 (khảo sát có hệ thống + chạy thử/tái lập được).
- **Trung bình:** câu đóng góp ở §4 — suy luận hợp lý từ bằng chứng nhưng **chưa được thầy xác nhận bằng lời**, cần chốt ở buổi họp tới; kiến trúc ghép linh kiện L2 ở §3.3 — hợp lý từ bảng bằng chứng nhưng chưa test end-to-end trên corpus thật.
- **Thấp — không nên hành động khi chưa rõ:** mọi suy đoán về ý nghĩa "tự động hình" và "song song" (§3.2 b, c); danh tính `ethanyt` (§3.3, §6-6) — ghi nhận là chưa biết, không lấp đầy bằng giả định.
