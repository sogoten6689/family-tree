# Làm trọn từng cuốn gia phả (GP-18)

Script dựng bộ đầu ra cho từng cuốn: nhãn NER/RE theo trang, cây BalkanNode, bản có cấu trúc. Đầu ra nằm trong repo dữ liệu: `data/03_derived/nom_volume_trees/<volume_id>/`. Đầu vào: `data/00_raw/hannom/giapha_web_export_2026-10-19/<volume_id>/NNN.json`.

| File | Việc |
|---|---|
| `engine.py` | Bộ máy dùng chung: nhận danh sách thực thể theo thứ tự đọc (key, nhãn, chuỗi) và quan hệ (loại, key đầu, key cuối, độ tin cậy, căn cứ); dò offset tuần tự trong `hannom_text`, kiểm tra `text[start:end]`, ghi `pages/NNN.json` |
| `vol429_annotate.py` | Nhãn vol 429 (bản đầu, tự chứa bộ dò offset; kết quả đã commit) |
| `vol429_build_tree.py` | Dựng `tree.json` và `gia_pha_structured.json` cho vol 429 |
| `vol563_annotate.py` | Nhãn vol 563 (44 trang) qua `engine.run` |
| `vol563_build_tree.py` | Dựng `tree.json` (69 người) và `gia_pha_structured.json` cho vol 563 |
| `validate_tree.py` | Kiểm tra cây theo JSON Schema và hàm chuẩn hoá của backend |

Chạy lại vol 429 (từ gốc repo code):

```bash
python -X utf8 research/nom_volume_trees/vol429_annotate.py data/00_raw/hannom/giapha_web_export_2026-10-19/429 data/03_derived/nom_volume_trees/429
python -X utf8 research/nom_volume_trees/vol429_build_tree.py data/03_derived/nom_volume_trees/429
```

Quy ước nhãn: `docs/schemas/NER_RE_LABEL_SCHEMA_AND_PIPELINE.md` §3–§4 (tên gồm 公/氏, húy/tự/hiệu tách span, DATE không gồm 忌, không sửa OCR). Nguồn nhãn ghi `silver_claude` (chưa người duyệt). Không gọi dịch vụ trả tiền.
