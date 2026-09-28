# Định hướng nghiên cứu đề tài — tổng hợp chỉ đạo của thầy (đến 14/09/2026)

> **Vai trò file:** ghi lại quá trình suy luận từ ghi chú họp (evidence) → giả thuyết về đề tài đích mà thầy đang dẫn tới → đề xuất hướng đi cụ thể, có thể kiểm định. Không thay thế đề cương chính thức. Theo khung khoa học của repo: fact / inference / hypothesis được tách rõ, độ tin cậy được ghi kèm.
>
> **Cập nhật:** 2026-09-28 · **Nguồn:** `docs/lab/note_meeting_weekly/*` (20/07 → 14/09/2026), `docs/thesis/business.md`, `docs/thesis/RESEARCH_SOURCES.md`.

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

**Kết luận của mục này:** phần OCR-ensemble + voting (đã làm) và phần phân loại corpus (đã có sơ đồ mã hoá) là **chắc chắn**, có thể viết vào luận văn ngay. Phần "mô hình gia phả Hán TQ" và "song song" là **chưa đủ bằng chứng để triển khai** — nguy cơ làm sai hướng nếu tự suy diễn.

---

## 4. Đề xuất hướng đi cụ thể (đề tài đích, khung 3 lớp đóng góp)

Kế thừa khung "3 lớp đóng góp" đã có trong `docs/planning/luan_van_phan_tich_va_ke_hoach.md` (§5.1), cập nhật theo chỉ đạo mới:

| Lớp | Nội dung cập nhật theo thầy | Vai trò luận văn |
|-----|------------------------------|-------------------|
| **L0 — Corpus (mới, nay là xương sống)** | Thu thập có phân loại (tông/tộc/chi phả × bộ/đồ/ký/điệp), ưu tiên bản gốc Hán Nôm còn tồn; OCR ensemble 5 engine + vote cấp câu bằng Levenshtein MED (đã làm, đo được); alignment song ngữ Hán–Việt | **Đóng góp về phương pháp thu thập & đánh giá corpus** — có thể viết thành 1 chương độc lập, có số liệu (mean OCR theo loại chữ, tỉ lệ thắng vote theo engine) |
| **L1 — Mô hình dịch nghĩa** | Fine-tune Qwen 3.6 37B trên domain gia phả (khác domain của các LV khác dùng chung model) | So sánh baseline (Qwen chưa fine-tune / Gemini) vs. fine-tuned trên tập test gia phả — đây là thực nghiệm có số liệu rõ, làm được sớm |
| **L2 — Mô hình trích xuất & dựng cây** | NER + quan hệ + đồ thị tri thức học trên kho tiếng Việt (đã dịch), dùng để hiệu đính bản dịch thô và sinh cây; khảo sát transfer từ mô hình gia phả Hán TQ nếu tìm được (§3.2-a/b) | **Core khoa học** của riêng đề tài — khác biệt với các LV domain khác đang chỉ dừng ở dịch nghĩa |
| **L3 — Sản phẩm minh họa** | Hệ thống web hiện có (`family-saga-io` + `nlp_family_extractor`) dùng để **demo** happy path, không phải nơi đặt đóng góp khoa học | Minh họa & kiểm chứng sử dụng, giữ nguyên vai trò như plan cũ |

**Câu đóng góp đề xuất (1 câu, để chốt với thầy):**

> *"Xây dựng và đánh giá một corpus song ngữ Hán Nôm–Việt lĩnh vực gia phả (thu thập có phân loại, OCR ensemble có kiểm định thống kê), dùng làm nền fine-tune mô hình dịch nghĩa chuyên biệt và huấn luyện mô hình trích xuất thực thể–quan hệ để tự động sinh cây gia phả, có so sánh với hướng kế thừa từ mô hình gia phả Hán hiện có."*

Câu này **giữ được** phần đã làm chắc (OCR/vote/phân loại — đã có số liệu), **nối được** với yêu cầu chung của lab (fine-tune Qwen), và **để ngỏ đúng chỗ** cho phần transfer-learning Hán TQ mà thầy gợi ý nhưng chưa xác nhận rõ.

---

## 5. Kế hoạch tối thiểu để kiểm định hướng đi (trước khi viết dày)

Theo tinh thần "thực nghiệm nhỏ nhất phân biệt được giả thuyết":

1. **Kiểm định L0 đã đủ chưa để viết chương corpus:** tổng hợp lại số liệu vote OCR đã có (win-rate theo engine, theo loại chữ in/thảo) thành 1 bảng — đã có dữ liệu thô trong `hannom-bilingual-dataset` (repo khác), chỉ cần tổng hợp.
2. **Kiểm định L1 khả thi trong thời gian còn lại:** chạy fine-tune Qwen trên **một tập nhỏ đã hiệu đính** (không phải toàn bộ), so BLEU/human-eval với Qwen gốc và Gemini — nếu chưa có API Qwen thì đây là **blocker cần thầy giải quyết trước** (đã ghi trong `bao_cao_thay.md:34-40`).
3. **Kiểm định L2 (transfer Hán TQ):** trước khi code, chỉ cần 1 vòng khảo sát (papers/HuggingFace/GitHub) mô hình NER/RE cho gia phả/văn bản cổ Hán Trung Quốc — nếu không có gì transfer được, L2 vẫn đứng độc lập được bằng train-from-scratch trên corpus tiếng Việt đã dịch (không phụ thuộc kết quả khảo sát).
4. **Không làm trước khi thầy xác nhận:** bất kỳ việc "tự động hoá UI Gemini/ChatGPT để né quota" — đã có rủi ro vi phạm ToS được ghi nhận (`phan_tich_hop_14_09_2026.md:174-180`), không nên đưa vào pipeline chính thức của luận văn dù có sẵn code thử nghiệm.

---

## 6. Câu hỏi cần thầy xác nhận trước khi chốt đề cương

(Giữ nguyên danh sách đã tổng hợp ở `docs/lab/note_meeting_weekly/14_09_2026/phan_tich_hop_14_09_2026.md`, không lặp lại phân tích — chỉ trích các câu **ảnh hưởng trực tiếp đến phạm vi đề tài**, không phải chi tiết kỹ thuật đã xử lý xong):

1. Ưu tiên loại mô hình gia phả Hán TQ nào (OCR / NER-RE / dựng cây) — quyết định phạm vi L2.
2. Ý đầy đủ của "gia phả xoay quanh nó... tự động hình [thành cây]" — có thể là mô tả chính xác cho L2, cần nguyên văn.
3. "Bài toán song song" = dữ liệu song ngữ, xử lý đa luồng, hay cả hai — quyết định có đưa hệ thống-hoá (parallel compute) vào luận văn hay không.
4. Timeline tiếp cận gia phả Nguyễn Phước — quyết định có dùng làm case study chính thức hay chỉ phụ lục.
5. Câu đóng góp 1-câu ở §4 có đúng ý thầy không, hay cần điều chỉnh trọng số giữa L1 (dịch nghĩa, việc chung cả nhóm LV) và L2 (trích xuất/dựng cây, phần riêng của đề tài này)?

---

## 7. Độ tin cậy tổng thể

- **Cao:** §2 (timeline chỉ đạo — trích trực tiếp), §3.1 (pattern nhất quán qua 3 buổi họp độc lập), phần "đã làm" của L0 (có code, có số liệu).
- **Trung bình:** câu đóng góp ở §4 — suy luận hợp lý từ bằng chứng nhưng **chưa được thầy xác nhận bằng lời**, cần chốt ở buổi họp tới.
- **Thấp — không nên hành động khi chưa rõ:** mọi suy đoán về ý nghĩa "tự động hình" và "song song" (§3.2 b, c) — ghi nhận là chưa biết, không lấp đầy bằng giả định.
