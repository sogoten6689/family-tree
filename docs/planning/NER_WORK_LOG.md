# Nhật ký công việc: NER gia phả bằng model thật (PhoBERT / SikuBERT)

Cập nhật lần cuối: 11/10/2026. Kế hoạch tổng thể: `model_integration_and_data_quality_plan.md`. PR: sogoten6689/family-tree#12.
Quy ước: mục nào ghi "đã đo" là có số liệu chạy thật; "ước tính" là suy đoán chưa kiểm chứng.

## 1. Quyết định của anh Lâm
- 09/10: tập trung model NER/RE + pipeline; **không dùng regex**, dùng model thật.
- 10/10: huấn luyện **PhoBERT (Việt) và SikuBERT (Hán) song song**; chạy trên **Google Colab**, không chạy trên máy cá nhân.
- 11/10: cho phép em thao tác Drive/Colab qua Chrome, push và mở PR.

## 2. Đã làm (theo thứ tự)
| # | Việc | Kết quả / bằng chứng |
|---|---|---|
| 1 | Sửa `/api/genealogy/extract` | Trước: luôn lỗi + gắn nhãn model giả. Nay: báo rõ "chưa có model"; có test (5 qua). Chưa deploy. |
| 2 | `analyze_data_quality.py` | Nhãn Gemini so với người soát: strict F1 0,34; LOC 0,10 (đã đo) |
| 3 | `clean_gold.py` (không phá huỷ) | 139 tài liệu: 35 thực thể cắt mép, 1 bỏ, 28 chứa xuống dòng (gắn cờ), 1 cặp trùng văn bản; 9 test |
| 4 | `export_conll.py` (IOB2, kiểm tra offset) | 144 tài liệu tiếng Việt, 0 lệch offset |
| 5 | `train_ner.py` (dùng chung 2 model) | Chặn PhoBERT-v2 (AGPL); F1 mức thực thể, bootstrap CI; 8 test |
| 6 | Colab lần 1: train trộn (nhãn Gemini chưa soát) | test 5 cây người soát: F1 **0,357** (CI 0,29–0,42) |
| 7 | `export_cv_folds.py` + Colab kiểm chéo 5 lượt, chỉ nhãn người soát | gộp 25 cây: F1 **0,538** (P 0,50/R 0,59); từng lượt 0,40–0,64 |
| 8 | Bản cuối (22 cây train / 3 dev) + xuất ONNX | int8 135 MB, khớp bản gốc 98,4%; 35 ms/câu (Colab, 1 luồng CPU) |

### F1 theo nhãn (kiểm chéo 25 cây)
DATE 0,78 · GENERATION 0,68 · LOC 0,49 · PER_NAME 0,39 · ORDER 0,15 (chỉ 11 mẫu).

## 3. Nhận định (có mức tin cậy)
- Nhãn người soát tốt hơn nhãn máy dù ít hơn nhiều (tin cậy vừa: hai test không cùng tập cây; gold người soát tạo từ sửa nhãn Gemini nên có thể bị neo).
- PER_NAME recall thấp (0,38) là điểm yếu lớn nhất ảnh hưởng dựng cây.
- F1 0,54 chỉ đủ làm **gợi ý nhãn cho người soát**, chưa đủ trích xuất tự động.

## 4. Vị trí tệp
- Mã: `research/label_studio_pipeline/{analyze_data_quality,clean_gold,export_conll,export_cv_folds,train_ner,export_onnx}.py`, `research/notebooks/*.ipynb`
- Drive của anh: `family_tree_ner/` (`out_final/`, `onnx_final.zip`, `cv_results/`); dữ liệu: `data/03_derived/conll/` (gitignore)

## 5. Chưa làm / đang làm
Xem mục "Tiến độ tiếp theo" bên dưới (cập nhật theo từng bước).

## 6. Tiến độ tiếp theo

### 11/10/2026 (tiếp) — tích hợp backend + đo trên VPS
| Việc | Kết quả (đã đo) |
|---|---|
| Tải `onnx_final.zip` (525 MB) từ Drive; lấy bản int8 | khớp từng byte với Drive |
| `app/ner/phobert_onnx.py`: tokenizer BPE thuần Python + onnxruntime | đối chiếu với `PhobertTokenizer` HF trên **2.259 từ thật: 0 khác biệt** |
| Chạy thử model thật trên máy dev | đoạn ví dụ ra đúng PER_NAME/LOC/GENERATION; 25 ms |
| Endpoint `/api/genealogy/extract` `model_version=phobert` | trả `entities` (nhãn, nội dung, offset, độ tin cậy); chưa có quan hệ; thiếu model → "chưa sẵn sàng" |
| UI: nút "PhoBERT NER (thử nghiệm)" + tab "Thực thể" | frontend 118 test qua; build qua |
| Backend test | 259 qua |
| **Đo trên VPS** (container tạm từ image backend, 1.701 ký tự = 490 từ) | **1 luồng: 1,49 s; 4 luồng: 0,73 s** (trung vị 10 lần). Thư mục tạm đã xoá. |

Ước tính (chưa đo): văn bản 2.400 ký tự ≈ 1–2 s với 4 luồng. VPS còn chạy dịch vụ khác nên có thể dao động.

### Cách triển khai bản thử (chưa thực hiện — cần anh Lâm cho phép merge/deploy)
1. Chép 5 tệp (`model.int8.onnx`, `vocab.txt`, `bpe.codes`, `label_list.json`, `model_card.json`) vào `<repo trên VPS>/models/ner_vi/`.
2. Merge PR #12 → Jenkins build lại backend (image sẽ có `onnxruntime`); compose đã mount `./models:/app/models:ro` và đặt `NER_MODEL_DIR_VI`.
3. Kiểm tra: chọn nút "PhoBERT NER (thử nghiệm)" trên /genealogy-extractor.
Hoàn tác: gỡ thư mục `models/ner_vi` → endpoint tự trả "chưa sẵn sàng", các chức năng khác không đổi.

### 11/10/2026 (tiếp) — thử huấn luyện 2 giai đoạn (nhãn Gemini → nhãn người)
Giai đoạn 1: học trước trên 103 cây nhãn Gemini (không gồm 25 cây người soát, để tránh rò rỉ), dev F1 ≈ 0,59 (trên nhãn Gemini).
Giai đoạn 2: tinh chỉnh bằng nhãn người, cùng 5 lượt kiểm chéo với lần trước (so sánh trực tiếp).

| | Gộp 25 cây | PER_NAME | LOC | DATE | GENERATION | ORDER | Từng lượt |
|---|---|---|---|---|---|---|---|
| Chỉ nhãn người | **0,538** | 0,39 | **0,49** | 0,78 | 0,68 | 0,15 | 0,56 / 0,54 / 0,40 / 0,64 / 0,48 |
| 2 giai đoạn | 0,526 | **0,46** | 0,40 | **0,80** | **0,71** | 0,30 | 0,54 / 0,57 / 0,36 / 0,65 / 0,43 |

**Kết luận (tin cậy vừa):** không có cải thiện tổng thể (0,526 so với 0,538, chênh nhỏ hơn dao động giữa các lượt). Học trước trên nhãn máy làm PER_NAME khá hơn (+0,07) nhưng LOC tệ hơn (−0,09): đúng với phát hiện nhãn Gemini nhiễu nặng ở LOC. Không đáng đổi quy trình; **bản dùng vẫn là huấn luyện chỉ trên nhãn người**.
Gợi ý nếu muốn tăng tiếp: (1) thêm gold người soát, nhất là PER_NAME/LOC; (2) lọc nhãn LOC của Gemini trước khi học trước (chỉ giữ PER_NAME/DATE/GENERATION); (3) chạy nhiều seed để biết dao động thật.
Kết quả thô trên Drive: `family_tree_ner/cv_results/` và `cv_results_2stage/`.

### 11/10/2026 — ĐÃ DEPLOY bản thử lên production (theo đồng ý của anh Lâm)
- PR #12 merge 14:54 UTC; Jenkins build backend + frontend; chỉ có 1 lần 502 thoáng qua lúc thay container.
- Model int8 (5 tệp, 135 MB) đặt ở `/var/jenkins_home/workspace/family-tree/models/ner_vi/` trên VPS (ghi qua container tạm vì thư mục thuộc root); compose mount `./models:/app/models:ro`.
- Kiểm tra sau deploy: `POST /api/genealogy/extract` `model_version=phobert` → 200, 0,16 s cho đoạn ~130 ký tự, nhận đúng PER_NAME/GENERATION/DATE/LOC; `regex` vẫn chạy; `/health` 200; bundle giao diện có nút "PhoBERT NER".
- Phát hiện sau deploy: model_info trả `f1_reported` = dev F1 (0,6458) lạc quan → PR #13 bỏ trường này.
- CI: test `PageViewer.test.tsx` chập chờn (lần đầu lỗi, chạy lại qua; commit chỉ đổi tài liệu) → đã tạo việc riêng để sửa.
- Hoàn tác: đổi tên/xoá `models/ner_vi` trên VPS → endpoint tự trả "chưa sẵn sàng".

### 11/10/2026 — hướng (a): model gợi ý nhãn cho cây chưa soát
Công cụ `research/label_studio_pipeline/prelabel_with_model.py` (chạy model cục bộ, không tốn tiền, không gọi mạng) → `tasks.json` (task Label Studio có predictions, mỗi vùng có điểm tin cậy) + `priority.csv` (cây nên soát trước).
Chạy trên 114 cây chưa người soát (bỏ 25 cây đã soát): **4.200 thực thể** (LOC 2.132 · DATE 957 · PER_NAME 723 · GENERATION 379 · ORDER 9); độ tin cậy ≥0,9: 2.575 · 0,6–0,9: 1.296 · <0,6: 329; 4 cây không ra thực thể nào.
So với nhãn Gemini hiện có (6.379 thực thể): trùng khớp tuyệt đối 1.292 (P 0,31 / R 0,20) — thấp là điều dự kiến vì nhãn Gemini nhiễu và nhiều hơn (precision của Gemini so với người chỉ ≈0,30). Model chưa soát nên cần người xem, nhất là PER_NAME (model ít hơn nhiều so với Gemini: 723 vs LOC 2.132 — có thể bỏ sót tên).
Đầu ra nằm ở `data/03_derived/prelabel_phobert_v1/` (gitignore). Cách dùng: Import `tasks.json` vào project Label Studio mới, mở `priority.csv` để chọn thứ tự soát.

### 12/10/2026 — tối ưu kết quả: đổi sang XLM-RoBERTa-base
Cùng 5 lượt kiểm chéo theo cây, 25 cây người soát, F1 gộp mức thực thể (strict). Mọi lần chạy lưu xác suất (`probs.json`) để phân tích ngoại tuyến (`analyze_probs.py`, không tốn GPU).

| Cấu hình | F1 gộp | PER_NAME | GENERATION | DATE | LOC | ORDER |
|---|---|---|---|---|---|---|
| PhoBERT-base (chạy lại, trùng khít lần trước → tái lập được) | 0,539 | 0,39 | 0,69 | 0,78 | 0,48 | 0,15 |
| **XLM-R-base** seed 42 / 1 / 2 | 0,614 / 0,621 / 0,593 → **TB 0,609 ± 0,012** | 0,40 | 0,67 | 0,80–0,86 | **0,62** | 0–0,15 |
| XLM-R-base, gộp 3 seed (trung bình xác suất) | 0,630 | 0,39 | 0,65 | 0,86 | 0,64 | 0,17 |
| XLM-R-base + PhoBERT gộp | 0,585–0,621 (không hơn XLM-R riêng) | | | | | |
| XLM-R-large (lượt 0 duy nhất) | 0,563 (< base 0,667; 22 phút/lượt) → bỏ | | | | | |

- XLM-R-base hơn PhoBERT-base **+0,074 F1, khoảng tin cậy 95% bootstrap theo câu [+0,042; +0,106]**, thắng ở cả 5 lượt; phần tăng nằm chủ yếu ở **LOC (0,48 → 0,62)**; PER_NAME vẫn yếu (~0,40) ở mọi cấu hình.
- Chỉnh ngưỡng tin cậy (chọn trên 4 lượt, đánh giá lượt còn lại): +0,005–0,013 → không đáng. Gộp 3 seed +0,02 nhưng chậm gấp 3 → chưa dùng.
- Giả thuyết (chưa kiểm chứng): PhoBERT được huấn luyện trên văn bản đã tách từ, trong khi dữ liệu ở đây là mức âm tiết → bất lợi; XLM-R dùng sentencepiece nên không bị ảnh hưởng.
- Lưu ý: trên 1 câu ví dụ tự soạn XLM-R bỏ sót "Đời thứ 3" và cắt tên ("Văn An") — một mẫu không đổi kết luận từ 25 cây, nhưng nên theo dõi.

**Bản cuối** (22 cây train / 3 dev, 20 epoch, seed 42): ONNX int8 **278 MB** (đã lượng tử hoá cả bảng embedding; fp32 là 1,1 GB), khớp bản gốc 99,0%. Tốc độ trên **VPS** (1.701 ký tự): **1 luồng 1,70 s; 4 luồng 0,63 s** (PhoBERT: 1,49 s / 0,73 s). Tệp: `data/03_derived/models/xlmr_ner_v1/` (model.int8.onnx, tokenizer.json, label_list.json, model_card.json, onnx_report.json). Backend hỗ trợ `tokenizer.json` (thư viện `tokenizers`; khớp `AutoTokenizer` trên 2.259 từ thật, 0 khác biệt).

**Triển khai (CHƯA làm — cần anh Lâm cho phép):** (1) merge PR chứa mã backend mới (đọc `tokenizer.json`) → Jenkins build; (2) đổi tên `models/ner_vi` → `models/ner_vi.bak` trên VPS, chép 4 tệp XLM-R vào `models/ner_vi/`; (3) `docker restart family-tree-backend` (model nạp một lần khi chạy). Hoàn tác: trả `ner_vi.bak` về và restart.
