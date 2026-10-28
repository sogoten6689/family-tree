# Harness tích hợp (API qua HTTP thật)

Code: `nlp_family_extractor/tests/integration/` · chạy: `scripts/harness.sh`.

| Tầng | Lệnh | Cần | Phủ |
|------|------|-----|-----|
| Không DB | `scripts/harness.sh` | Python deps | khởi động uvicorn thật; `/health`, `/openapi.json`, `/docs`, CORS, từ chối ẩn danh, `/api/genealogy/extract` |
| Có MySQL | `scripts/harness.sh db` | Docker daemon | MySQL **tạm** (container `harness-mysql`, cổng 3319, không volume, không đụng `family-tree-mysql`); thêm: đăng nhập admin, CRUD cây/nút/liên kết, export, xoá |

Nhắm vào stack đã chạy: `HARNESS_API_URL=http://host:port scripts/harness.sh`.
Tầng không DB cũng nằm trong lệnh pytest của CI (~7 giây); test `requires_db` tự skip khi không có DB.

## Đã kiểm chứng (25/10/2026)
- Tầng không DB: 8 pass, 2 skip. Tầng `db`: 10 pass; container tạm được xoá sau khi chạy.
- Harness hộp đen theo nhân vật (repo riêng `family-tree-harness`) chạy trên cùng API: 42 test pass với MySQL.

## Phát hiện từ harness
- Không có MySQL, `GET /api/family-trees` từng trả **500** (do `get_db()` ném `RuntimeError`). Đã sửa 25/10/2026: `get_db()` ném `DatabaseUnavailable` (lớp con `RuntimeError`) và `api.py` trả 503. Test: `tests/test_database_unavailable.py`.

## Model NER chữ Hán (`NER_MODEL_DIR_HAN`)
`POST /api/genealogy/extract` với `language="hannom"` **hoặc** `model_version="sikubert"` chạy SikuBERT mức ký tự
(`app/ner/phobert_onnx.py`, `language="han"`). Chưa đặt biến / thiếu tệp → `success=false`, `error` nêu rõ biến/tệp thiếu (không giả lập).

1. Tải `MyDrive/family_tree_ner/sikubert_family_han_v1/` về máy (cần torch, transformers, onnx, onnxruntime).
2. Xuất ONNX (tạo cả `model.onnx` fp32 và `model.int8.onnx`):
   `python nlp_family_extractor/tools/export_ner_onnx.py --model-dir sikubert_family_han_v1 --output-dir han_onnx --sample-conll data/03_derived/han_ner_v1/han_final/test.conll`
   — xem `onnx_report.json`: `label_agreement_with_torch.int8` gần 1 và `tokenizer_json_mismatch.count` = 0.
3. `export NER_MODEL_DIR_HAN=/đường/dẫn/han_onnx NER_ONNX_FILE_HAN=model.onnx` (cần tệp ONNX đã chọn, `tokenizer.json`, `label_list.json`; `model_card.json` nếu có).
   **Dùng fp32** (anh Lâm chọn 28/10/2026): `quantize_dynamic` int8 làm `sikubert-family` v1 mất ~23% thực thể (F1 0,769 so với torch
   trên 100 câu `han_final`), fp32 khớp torch 690/690. Bỏ `NER_ONNX_FILE_HAN` thì loader đọc `model.int8.onnx` (mặc định, như `vi`);
   `model_info.model_name` ghi `ONNX fp32`/`ONNX int8` theo tệp đang chạy. Chi tiết: family-tree-harness `research/FINDINGS.md` §17.

Chia câu khớp lúc huấn luyện: mỗi ký tự không phải khoảng trắng là một token, hết câu sau `。`, tối đa 128 ký tự; offset theo code point.
`model_info.note` ghi rõ model học trên **nhãn máy Gemini, chưa người soát** (F1 0,715 là so với nhãn máy, 15 trang test).
Khi đã cấu hình biến này, các test "hannom phải thất bại trung thực" (`tests/integration/test_smoke_no_db.py`, harness hộp đen M6) sẽ không còn đúng.
