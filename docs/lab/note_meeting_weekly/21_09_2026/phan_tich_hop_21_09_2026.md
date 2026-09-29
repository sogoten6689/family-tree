# Phân tích ghi chú 21/9/2026

> Nguồn: [`21_09_2026.md`](./21_09_2026.md). File này đối chiếu nội dung đó
> với việc đã làm trong tuần 25–28/9 (`research/model_survey/`,
> `docs/planning/chinese_genealogy_model_hunt_plan.md`), nêu phát hiện quan
> trọng và câu hỏi mở. Quy ước: **Fact** = kiểm chứng trực tiếp được ·
> **Suy luận** = đánh giá của tôi, có thể sai, cần xác nhận · **Câu hỏi** =
> cần thầy/nhóm trả lời.

---

## 1. Phát hiện quan trọng nhất — tài khoản `ethanyt` có thể là người trong nhóm

**Nguyên văn (mục 7 ghi chú):** *"Em có finetuning 2 model Segmentation và
Punctuation dựa trên GuwenBERT... (https://huggingface.co/ethanyt/guwen-seg,
https://huggingface.co/ethanyt/guwen-punc)"*

**Đối chiếu hiện trạng (fact):** Toàn bộ `research/model_survey/candidates.md`
và notebook Colab tuần này coi `ethanyt`/`Ethan-yt`
(`github.com/Ethan-yt/guwen-models`, `huggingface.co/ethanyt/guwen-ner`) là
**ứng viên bên thứ ba** tìm được qua tìm kiếm công khai.

**Suy luận (độ tin cậy trung bình — chỉ trùng tên tài khoản, chưa xác minh
danh tính thật):** nếu thành viên viết dòng trên chính là chủ tài khoản
`ethanyt`, thì mô hình tôi đã "đi săn" cả tuần thực ra là sản phẩm của một
thành viên trong nhóm nghiên cứu của thầy, không phải bên thứ ba vô danh.

**Câu hỏi cần xác nhận (ưu tiên cao nhất):** `ethanyt` trên HuggingFace/GitHub
có phải là thành viên nào trong nhóm không? Nếu đúng, nên hỏi trực tiếp về:
(a) vì sao `guwen-ner` gần như không nhận thực thể trên câu phồn thể (0/4 —
xem mục 2 dưới), (b) họ có bản NER nào tốt hơn ngoài `guwen-seg`/`guwen-punc`
không, (c) `guwen-punc` họ tự nhận đã tốt hơn bản mặc định — vậy vì sao một
thành viên khác đo lại vẫn ra F1 chỉ 0.195 (xem mục 2)?

## 2. guwen-punc bị đo là "overfitting" — đối chiếu với guwen-ner tuần này

**Nguyên văn (mục 6):** đo thủ công `guwen-punc` trên 1 mẫu, dùng đúng config
mặc định tác giả, ra **precision 0.195 / recall 0.202 / f1 0.195** → kết
luận overfitting.

**Đối chiếu hiện trạng (fact, từ `research/model_survey/EVALUATION.md` mục
"Tái lập độc lập 27/9"):** `guwen-ner` (cùng họ GuwenBERT, khác tác vụ — NER
thay vì chấm câu) cho 0/4 thực thể trên câu phồn thể, 3/4 trên giản thể.

**Suy luận (Moderate confidence):** hai kết quả kém ở hai tác vụ khác nhau
(chấm câu và NER) trên cùng một họ model (`guwen-*` dựa trên GuwenBERT) là
bằng chứng **hội tụ, không phải trùng hợp** — củng cố nghi ngờ rằng bản thân
nền tảng GuwenBERT (không phải riêng lẻ từng model) có vấn đề về khả năng
tổng quát hoá, đặc biệt trên văn bản/định dạng lệch phân phối huấn luyện.

**Bằng chứng bên ngoài củng cố thêm (mục 7):** một bài báo học thuật
(*Automatic sentence segmentation for classical Chinese: The Spring and
Autumn Annals as an example*, https://doi.org/10.1093/llc/fqad016) đo thực
nghiệm và thấy **GuwenBERT thua SikuBERT/SikuRoBERTa** trên segmentation.

**Kết luận cập nhật cho hướng nghiên cứu:** ưu tiên SikuBERT/SikuRoBERTa hơn
GuwenBERT khi so sánh — đúng hướng Cell B của
`research/model_survey/colab/hannom_model_experiments.ipynb` đã làm (so
`SIKU-BERT/sikubert` với `ethanyt/guwenbert-base`). Khi có kết quả Colab,
nên trích dẫn thêm bài báo trên làm bằng chứng đối chiếu bên ngoài.

## 3. Ứng viên mới — XunziLLM (chưa có trong candidates.md)

**Fact (tôi tự tra README trực tiếp 2026-09-28):** XunziLLM là LLM ~7B, fine-
tune từ Qwen/ChatGLM3/Baichuan2, làm được: tách câu, chấm câu, **trích xuất
thông tin (người/sự kiện/địa điểm)**, dịch, đọc hiểu cổ văn. License **không
ghi rõ trong README**. Model host trên **ModelScope**.

**Fact (kiểm tra egress 2026-09-28):** `link.springer.com`, `emerald.com`,
`projects.iq.harvard.edu` đều bị chặn bởi proxy egress của sandbox này —
cùng nhóm hạn chế đã ghi nhận với HuggingFace/Google Drive/Zenodo tuần
trước. Chưa tự chạy thử được XunziLLM trong môi trường Claude Code cloud.

**Suy luận:** về quy mô (~7B tham số so với ~100–300M của guwen-ner/SikuBERT)
và đúng tác vụ (information extraction), XunziLLM là ứng viên **tiềm năng
hơn hẳn** những gì đã test tuần này — nhưng cần: (1) xác nhận license trước
khi dùng (theo đúng nguyên tắc license-gate đã áp dụng ở Cell B), (2) chạy ở
máy có thể truy cập ModelScope (không phải sandbox này).

## 4. Bài báo CBDB (kinship normalization) — liên quan trực tiếp thiết kế hiện tại

**Fact (đối chiếu code):** `nlp_family_extractor` hiện dùng đúng 3 loại quan
hệ rule-based: `spouse_of`, `parent_of`, `sibling_of` (xem
`app/domains/extraction/rules/`).

**Fact (từ ghi chú, chưa tự đọc được full text — bị chặn egress):** bài
*"Normalization of kinship relations..."* (CBDB) chuẩn hóa mọi quan hệ huyết
thống phức tạp tiếng Hán tiền-hiện-đại về **3 quan hệ cơ bản**: cha-con,
mẹ-con, chồng-vợ.

**Suy luận (High confidence về độ liên quan, chưa đọc được phương pháp chi
tiết):** đây gần như đúng bài toán thiết kế quan hệ hiện tại của dự án —
nên đọc kỹ (nhờ thầy hỗ trợ truy cập nếu link Harvard tiếp tục bị chặn) để
đối chiếu phương pháp chuẩn hóa của họ với luật hiện có trong
`rules/parent_child.py`, `rules/spouse.py`, `rules/sibling.py`.

## 5. DSNF (Chinese Open Relation Extraction, ACM 2018) — hướng rule-based thay vì model

**Nguyên văn (mục 2.2):** đề xuất DSNFs (Dependency Semantic Normal Forms)
— phân tích cấu trúc phụ thuộc ngữ pháp để trích quan hệ **không cần dữ
liệu gán nhãn trước**, giải quyết 3 đặc thù tiếng Hán (không tách từ rõ,
không chia thì, nhiều vị ngữ không liên từ).

**Suy luận:** đây là hướng **rule-based nâng cao**, khác hẳn các model đã
test (guwen-ner, SikuBERT, XunziLLM) — có thể bổ sung/tham khảo cho chính
`entity_extractor.py`/rule-based hiện tại của dự án, không nhất thiết phải
thay bằng model học sâu. Đáng đọc full-text nếu thầy xin giúp được.

## 6. Nguồn dữ liệu gia phả Việt Nam mới — bổ sung vào kế hoạch thu thập

**Fact:** 2 nguồn mới (mục 3 ghi chú) chưa có trong
`docs/planning/firecrawl_genealogy_source_discovery_plan.md`:
- *Lịch sử họ Nguyễn Việt Nam* (sách, dạng tiểu sử — khả năng chỉ Quốc ngữ).
- *Phả hệ – Tộc họ Nguyễn Bặc* (website, đã trực quan hoá).

**Khuyến nghị:** thêm 2 nguồn này vào registry nguồn của
`firecrawl_genealogy_source_discovery_plan.md` khi chạy lại việc tìm dữ
liệu (hiện vẫn blocked do thiếu `FIRECRAWL_API_KEY` thật — xem task #5).

## 7. Việc null/tiêu cực đáng ghi nhận — tránh lặp lại

- **FastHan**: chết, cần tài khoản Baidu (SĐT Trung Quốc) mới tải được model
  — cùng mô thức rào cản như ModelScope/HF bị chặn trong sandbox này.
- **NomNaOCR**: không có nhãn dấu câu → không dùng train chấm câu được.
- **Tích hợp tri thức từ điển vào model**: thử rồi, **không cải thiện** (F1
  0.7 ngang bằng) — không nên thử lại đúng hướng này mà không có ý tưởng mới.

## Tổng hợp câu hỏi cần thầy/nhóm trả lời

1. `ethanyt` (tác giả `guwen-ner`/`guwen-seg`/`guwen-punc`) có phải thành
   viên trong nhóm không? (ưu tiên cao nhất — xem mục 1)
2. Có thể xin giúp 2 bài báo bị chặn không: CBDB kinship normalization
   (Harvard, đã bị chặn cả ở đây) và "framework of genealogy knowledge
   reasoning" (Emerald)?
3. XunziLLM — license thật là gì, nhóm có ai chạy được trên máy truy cập
   được ModelScope chưa?
4. Luận văn "anh Lâm" (K34) về ngắt nhịp — thầy có thể gửi trực tiếp không
   (người đó báo không còn giữ)?

## Việc có thể làm ngay, không cần chờ trả lời

- Thêm XunziLLM, bài CBDB, 2 nguồn gia phả Nguyễn vào
  `research/model_survey/candidates.md` / `firecrawl_genealogy_source_discovery_plan.md`
  (đã đề xuất, chờ xác nhận từ Lâm trước khi ghi — xem hội thoại phiên
  25–28/9).
- Trích dẫn bài báo *Spring and Autumn Annals* (GuwenBERT thua SikuBERT) vào
  `EVALUATION.md` khi viết kết luận cuối từ kết quả Colab.
