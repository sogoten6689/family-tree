# Quy trình huấn luyện lại NER sau khi soát thêm nhãn

Áp dụng cho PhoBERT (tiếng Việt). Ngày viết: 11/10/2026. Nhật ký thí nghiệm: `NER_WORK_LOG.md`.

## 0. Việc của người soát (anh Lâm)
1. Import `data/03_derived/prelabel_phobert_v1/tasks.json` vào một project Label Studio mới (nhãn do model gợi ý, có điểm tin cậy). Soát theo thứ tự `priority.csv`.
2. Xuất các cây đã soát: `python -m label_studio_pipeline.export_ls_gold --output-dir <thư mục cây mới>` (cần `.env` Label Studio; chỉ lấy annotation do người sửa).
   Gợi ý ưu tiên soát: **PER_NAME** (model dễ bỏ sót) và **LOC** (nhãn Gemini nhiễu), rồi tới ORDER.

## 1. Chuẩn bị dữ liệu (một lệnh, chạy máy local, không tốn tiền)
```bash
cd research
python -m label_studio_pipeline.prepare_retrain \
  --human-dir ../data/02_gold/gold_labels/v1_human \
  --new-dir   <thư mục cây mới> \
  --output-dir ../data/03_derived/retrain_v2
```
Tạo `vi_cv5.zip`, `vi_final.zip`, `manifest.json` (số cây, cây trùng bị bỏ, băm dữ liệu, thống kê làm sạch), `clean_report.json`.
Kiểm tra `manifest.json`: `duplicates_dropped` và `cleaning_totals.flag_entity_contains_newline` (thực thể chứa xuống dòng cần người xem).

## 2. Huấn luyện trên Colab (TỐN TIỀN — hỏi anh Lâm trước)
Upload vào `MyDrive/family_tree_ner/`: `vi_cv5.zip`, `vi_final.zip`, `train_ner.py`, `export_onnx.py` và hai notebook `research/notebooks/train_ner_cv_colab.ipynb`, `train_ner_final_colab.ipynb`.
1. Chạy notebook **cv** → F1 gộp kiểm chéo (đây là con số báo cáo). 2. Chạy notebook **final** → trọng số + ONNX int8 + `onnx_report.json`.
Mỗi notebook có ô cuối `runtime.unassign()` để dừng tính tiền.

## 3. Quyết định có triển khai bản mới không
Chỉ thay model trên prod khi **F1 kiểm chéo gộp ≥ bản đang chạy (0,538)** và PER_NAME không tụt. Lưu ý: tập cây đã đổi (nhiều hơn 25) nên so sánh chỉ mang tính gần đúng; để so sánh sạch, đánh giá thêm trên 25 cây cũ.
Triển khai (cần anh Lâm cho phép, thao tác lên production): chép `model.int8.onnx`, `vocab.txt`, `bpe.codes`, `label_list.json`, `model_card.json` vào `models/ner_vi/` trên VPS (xem `NER_WORK_LOG.md`). Giữ bản cũ đổi tên `ner_vi.bak` để hoàn tác nhanh. Không cần build lại ảnh Docker (model được mount).

## 4. Ghi lại
Cập nhật `NER_WORK_LOG.md` (số cây, F1 gộp, F1 từng nhãn, quyết định) và lưu `manifest.json` cùng `model_card.json`.
