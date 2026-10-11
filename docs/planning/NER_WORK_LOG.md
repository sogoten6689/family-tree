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
