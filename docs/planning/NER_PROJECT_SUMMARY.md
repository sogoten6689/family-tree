# Tổng kết: đưa model NER thật vào hệ thống gia phả

Cập nhật: 12/10/2026 · Chi tiết số liệu từng bước: `NER_WORK_LOG.md` · Kế hoạch gốc: `model_integration_and_data_quality_plan.md` · Quy trình huấn luyện lại: `RETRAIN_RUNBOOK.md`

## 1. Yêu cầu ban đầu (anh Lâm)

- 09/10: tập trung làm **model NER/RE + pipeline**; web CMS đã đủ.
- "Tập trung nghiên cứu model, cách sử dụng và tích hợp vào hệ thống; dữ liệu phải được làm sạch, đưa vào sử dụng, phân tích."
- "**Regex mình không dùng, muốn dùng model thật.**"
- Huấn luyện **PhoBERT (Việt) và SikuBERT (Hán) song song**; chạy trên **Google Colab**, không chạy trên máy cá nhân.
- 11/10: cấp quyền đầy đủ thao tác Drive/Colab qua Chrome, push, mở PR. 12/10: "tối ưu kết quả rồi báo", đồng ý đổi model prod.
- Cách làm việc: xưng "em"/gọi "anh Lâm", nhẹ nhàng; việc tốn tiền (Colab, API) hoặc đụng production phải xin phép trước.

## 2. Đã làm (theo thứ tự)

| # | Việc | Kết quả |
|---|---|---|
| 1 | Sửa endpoint `/api/genealogy/extract` | Trước: luôn lỗi + gắn nhãn model giả. Nay trả lỗi rõ khi chưa có model. |
| 2 | Phân tích chất lượng dữ liệu (`analyze_data_quality.py`) | Nhãn Gemini so với người soát: F1 0,34; địa danh chỉ 0,10 → nhãn máy không dùng làm gold được. |
| 3 | Làm sạch (`clean_gold.py`) | Không phá huỷ dữ liệu gốc; cắt mép, bỏ chồng/trùng, gắn cờ thực thể xuống dòng. |
| 4 | Xuất CoNLL (`export_conll.py`), chia kiểm chéo theo cây (`export_cv_folds.py`) | 25 cây người soát → 5 lượt, mỗi cây làm test đúng 1 lần. |
| 5 | Huấn luyện (`train_ner.py`) trên Colab | Nhãn người soát tốt hơn nhãn Gemini nhiều: F1 0,36 (nhãn Gemini) → 0,54 (nhãn người, PhoBERT). |
| 6 | Thử huấn luyện 2 giai đoạn (nhãn Gemini rồi nhãn người) | 0,526: không cải thiện (PER_NAME tốt hơn nhưng địa danh kém hơn). |
| 7 | Xuất ONNX int8, tích hợp backend (`app/ner`), bật nút trên UI | Chạy CPU, không cần torch. |
| 8 | Quét cấu hình + phân tích ngoại tuyến (`analyze_probs.py`) | **XLM-R-base F1 0,609 ± 0,012** so với PhoBERT 0,539 (+0,074, CI95 [0,042; 0,106], thắng cả 5 lượt). XLM-R-large không hơn; gộp model / chỉnh ngưỡng không đáng. |
| 9 | **Triển khai prod** | Model XLM-R-base ONNX int8 (278 MB) đang chạy; 0,18–0,28 s cho đoạn ~130 ký tự; bản PhoBERT giữ ở `models/ner_vi.bak`. |
| 10 | Công cụ gợi ý nhãn (`prelabel_with_model.py`) | 3.706 thực thể gợi ý cho 114 cây chưa soát (`data/03_derived/prelabel_xlmr_v1/`). |
| 11 | Quy trình huấn luyện lại (`prepare_retrain.py`) | Gộp + làm sạch + bỏ trùng + chia kiểm chéo + đóng zip cho Colab, có manifest. |

## 3. Trạng thái hiện tại

- **Prod**: `giapha.kimtudien.com.vn` — nút "Model NER (thử nghiệm)" dùng XLM-R-base; chỉ trích **thực thể** (PER_NAME, LOC, DATE, GENERATION, ORDER), **chưa có quan hệ** cha/mẹ/vợ chồng. Dùng làm gợi ý, cần người soát lại.
- **PR**: #12–#17 đã merge. **#18** (prelabel ghi model_version) chờ merge — chỉ công cụ/tài liệu, không đổi production.
- **Điểm yếu lớn nhất**: PER_NAME F1 ≈ 0,40 ở mọi cấu hình. Địa danh 0,62, ngày tháng ~0,80, đời ~0,67, thứ bậc chưa đo được (chỉ 11 mẫu).
- **Hạn chế dữ liệu**: gold người soát mới 25 cây (692 thực thể); gold này tạo từ sửa nhãn Gemini nên có thể bị neo (F1 thật có thể thấp hơn chút).
- **Chưa làm**: SikuBERT/chữ Hán (chưa có gold chữ Hán), model quan hệ, kiểm thử quy mô lớn.

## 4. Kế hoạch tiếp theo

1. **Anh Lâm soát thêm nhãn** (việc quyết định nhất): import `data/03_derived/prelabel_xlmr_v1/tasks.json` vào Label Studio, soát theo `priority.csv` (cây 229, 1695, 1717, 243, 1636 trước); ưu tiên **PER_NAME** (model dễ bỏ sót/cắt tên), rồi LOC. Xuất cây đã soát bằng `export_ls_gold.py`.
2. **Huấn luyện lại** (em làm, hỏi trước vì tốn tiền Colab): `prepare_retrain.py` → notebook CV → bản cuối → xuất ONNX. Chỉ thay prod nếu F1 kiểm chéo gộp ≥ 0,609 và PER_NAME không tụt.
3. **Thay model trên prod** (cần anh cho phép): chép 4 tệp vào `models/ner_vi/` trên VPS (giữ bản cũ làm `.bak`), restart backend. Hoàn tác ~1 phút.
4. **Quan hệ (RE)**: sau khi NER ổn (ví dụ PER_NAME ≥ 0,6), huấn luyện phân loại quan hệ FATHER_OF/MOTHER_OF/SPOUSE; dựng cây từ thực thể + quan hệ.
5. **Chữ Hán (SikuBERT)**: gán nhãn thí điểm 10–20 trang trước (có thể tốn tiền nếu dùng LLM gợi ý), kiểm tra lỗi lệch offset UTF-16 (câu hỏi Q1 còn mở).
6. **Dọn kỹ thuật** (nhỏ): hai test giao diện chập chờn (`PageViewer.test.tsx`, `LlmImportPanel.test.tsx`) làm CI hay phải chạy lại; 3 lỗi `prefer-const` trong `theme/colorUtils.ts`; tên tham số `model_version="phobert"` của API nay thực chất chọn "model NER hiện hành" (cân nhắc đổi tên, giữ tương thích).

## 5. Quyết định còn chờ

- Soát bao nhiêu cây và bắt đầu từ lúc nào (quyết định tốc độ cải thiện PER_NAME).
- Có dùng LLM (RamCloud/Gemini, tốn tiền) để gợi ý nhãn cho chữ Hán không.
- D3–D7 trong `docs/schemas/NER_RE_LABEL_SCHEMA_AND_PIPELINE.md` cần thầy duyệt trước khi chốt nhãn.

## 6. Vị trí tệp quan trọng

| Thứ | Ở đâu |
|---|---|
| Mã huấn luyện, phân tích, chuẩn bị dữ liệu | `research/label_studio_pipeline/` (`train_ner.py`, `analyze_probs.py`, `prepare_retrain.py`, `export_*.py`, `prelabel_with_model.py`) |
| Notebook Colab | `research/notebooks/` |
| Backend suy luận | `nlp_family_extractor/app/ner/phobert_onnx.py`; endpoint trong `api.py` |
| Model XLM-R (ONNX) | `data/03_derived/models/xlmr_ner_v1/` (cục bộ, gitignore) và `models/ner_vi/` trên VPS |
| Kết quả kiểm chéo thô | `data/03_derived/sweep_v1/` |
| Drive Colab | `MyDrive/family_tree_ner/` |

## 7. Cách vận hành nhanh

- Kiểm tra prod: gửi `POST /api/genealogy/extract` với `{"text": "...", "language": "vietnamese", "model_version": "phobert"}`.
- Hoàn tác model: trên VPS đổi tên `models/ner_vi` → `ner_vi.xlmr`, `ner_vi.bak` → `ner_vi`, `docker restart family-tree-backend`.
- Chạy Colab qua Chrome: xem ghi chú trong bộ nhớ dự án (Drive hay lỗi mount → nhúng dữ liệu base64 vào notebook; luôn xoá runtime sau khi xong để khỏi tốn tiền).
