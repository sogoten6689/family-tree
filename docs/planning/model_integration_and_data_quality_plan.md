# Kế hoạch: model thật + làm sạch dữ liệu + tích hợp hệ thống

Trạng thái: **bản nháp chờ anh Lâm duyệt** (10/10/2026). Không dùng bộ trích xuất regex; hướng chính là model huấn luyện thật.
Schema nhãn: `docs/schemas/NER_RE_LABEL_SCHEMA_AND_PIPELINE.md` (5 thực thể, 3 quan hệ).

## 1. Hiện trạng (đã đo, không phải ước đoán)

| Mục | Kết quả | Mức tin cậy |
|---|---|---|
| Model đã huấn luyện trong repo | **Chưa có** (không có trọng số, không có code nạp PhoBERT/SikuBERT) | cao |
| Endpoint `/api/genealogy/extract` trên prod | Luôn lỗi (gọi hàm không tồn tại) và từng ghi nhãn "PhoBERT/SikuBERT fine-tuned" sai sự thật. Đã vá trong nhánh này: nói thẳng "chưa huấn luyện" | cao |
| Gold do người soát | 25 cây, ~68k ký tự, 692 thực thể (PER_NAME 192, LOC 283, DATE 150, GENERATION 56, ORDER 11) | cao |
| Nhãn máy (Gemini) so với người | strict F1 **0.34**, lenient 0.45; LOC strict F1 **0.10** (fp 285) | vừa (người soát sửa từ nhãn Gemini nên có thể bị neo) |
| Regex (chỉ để đối chiếu) | tên người F1 0.25, quan hệ F1 0 | vừa (8 cây) |
| OCR Hán | 2.094 trang, tỉ lệ chữ Hán 0.98; sách hỗn hợp thấp hơn (0.80–0.93) | vừa; chỉ số `uncertain_rate` chưa kiểm định nghĩa |

**Kết luận:** nút thắt là **số lượng và chất lượng gold**, chưa phải kiến trúc model. 25 cây quá ít để tin bất kỳ số F1 nào từ model fine-tune.

## 2. Làm sạch dữ liệu (đã có công cụ)

`research/label_studio_pipeline/clean_gold.py` — không phá huỷ, ghi ra thư mục mới, có báo cáo `clean_report.json`, 9 test.

| Bước | Việc | Ghi chú |
|---|---|---|
| C1 | Bỏ zero-width/điều khiển, CRLF→LF, NBSP→dấu cách, NFC | offset dời theo từng đoạn, không đoán lại |
| C2 | Cắt khoảng trắng/dấu câu ở mép thực thể | |
| C3 | Bỏ thực thể chồng/trùng, dời lại chỉ số quan hệ | |
| C4 | Kiểm tra `text[start:end]==entity.text`, chỉ số quan hệ | lỗi cứng, thoát mã 1 |
| Cờ | Thực thể chứa xuống dòng; tài liệu trùng; đoạn dùng chung | chỉ báo, **không tự sửa** |

Chạy thử trên 139 tài liệu `gold_labels`: 4.954 → 4.953 thực thể (35 bị cắt mép, 1 bỏ), 895 quan hệ giữ nguyên, 28 thực thể có xuống dòng, 1 cặp trùng văn bản (1852 ≡ 1772), 0 lỗi kiểm tra cuối.

Còn thiếu (làm tiếp): (a) cổng chất lượng OCR cho Hán (loại trang rỗng/placeholder, tách đoạn Hán–Việt trong sách hỗn hợp); (b) chia train/dev/test theo **dòng họ/sách**, không theo trang, để không rò rỉ; (c) manifest có phiên bản (băm nội dung + phiên bản làm sạch) để tái lập.

## 3. Model

| Ngôn ngữ | Ứng viên chính | Lý do | Lưu ý |
|---|---|---|---|
| Hán | **SikuBERT** (Apache-2.0), mức ký tự | 0 UNK trên chữ phồn thể; GuwenBERT ~20% UNK | Mô hình có sẵn `guwen-ner` không nhận ra câu gia phả (0/3) → phải fine-tune |
| Việt | **PhoBERT-base** (MIT) | chuẩn cho NER tiếng Việt | **Tránh PhoBERT-base-v2: AGPL-3.0**. Cần tách từ trước (RDRSegmenter) |
| Dự phòng | XLM-RoBERTa-base (MIT) | một model cho cả hai | nặng hơn (279M) |
| Gán nhãn trước | LLM (RamCloud/Gemini) hoặc `NlpHUST/ner-vietnamese-electra-base` | chỉ để rút ngắn thời gian soát, **không phải gold** | giấy phép electra chưa rõ; LLM tốn tiền, phải hỏi |

Quan hệ (FATHER_OF/MOTHER_OF/SPOUSE) làm ở **giai đoạn 2**, sau khi NER đạt ngưỡng; dùng phân loại cặp thực thể trên cùng encoder.

Quy trình đánh giá: dev/test cố định theo dòng họ; báo F1 strict + lenient từng nhãn; so với đường cơ sở "nhãn máy chưa soát" (0.34). Với < 100 cây, báo khoảng tin cậy bằng bootstrap, không báo một con số trơn.

## 4. Tích hợp vào hệ thống

1. **Huấn luyện** ngoài prod (Colab/RunPod GPU — tốn tiền, hỏi trước mỗi lần); xuất trọng số + `model_card.json` (dữ liệu, phiên bản làm sạch, chỉ số, giấy phép).
2. **Kho model:** MinIO `models/<ngôn ngữ>/<phiên bản>/` + bảng DB `model_versions` (trạng thái: candidate / active / retired). Chỉ model có chỉ số trên test mới được `active`.
3. **Suy luận trên VPS (16 vCPU, không GPU):** xuất ONNX, chạy bằng ONNX Runtime trên CPU, tải theo ngôn ngữ khi khởi động. Độ trễ cho văn bản ~2.400 ký tự **chưa đo** → đo trước khi cam kết. Image backend hiện không có torch (~210 MB), nên ONNX Runtime giữ image nhỏ.
4. **Endpoint:** giữ `POST /api/genealogy/extract`; `model_version` chọn từ bảng `model_versions`; `model_info` trả đúng tên/phiên bản/chỉ số của model thật. Chưa có model active thì trả lỗi rõ ràng như hiện nay (không giả lập).
5. **Giao diện:** nút model chỉ bật khi có model active; hiển thị độ tin cậy từng thực thể; sửa tay → lưu vào hàng chờ gold (vòng phản hồi).
6. **Vòng lặp người–máy:** model gợi ý → người soát → gold mới → huấn luyện lại. Đây là cách tăng gold nhanh nhất.

## 5. Mốc thực hiện

| Mốc | Việc | Tốn tiền? |
|---|---|---|
| M0 | Làm sạch + báo cáo chất lượng + manifest (đã xong phần lõi) | không |
| M1 | Gán nhãn thêm: mục tiêu ≥ 100 cây Việt đã soát; thí điểm Hán 10–20 trang | LLM gán trước: **có** |
| M2 | Fine-tune PhoBERT-base (NER Việt), đánh giá trên test theo dòng họ | GPU: **có** |
| M3 | Đo độ trễ ONNX/CPU trên VPS; nối vào endpoint + kho model | không |
| M4 | Fine-tune SikuBERT (NER Hán) khi đủ gold Hán | GPU: **có** |
| M5 | Quan hệ (RE) giai đoạn 2 | GPU: **có** |

## 6. Rủi ro

- Gold quá ít → F1 dao động mạnh; mitigation: bootstrap, tăng gold bằng vòng người–máy.
- Offset Label Studio với chữ Hán (UTF-16 hay code point) **chưa kiểm** (Q1) — kiểm trước khi gán nhãn Hán.
- LOC nhiễu nặng ở nhãn máy → không dùng silver để huấn luyện LOC.
- Giấy phép: tránh PhoBERT-v2 (AGPL); CHAT_models OCR là CC BY-NC (chỉ nghiên cứu).
- D3–D7 trong tài liệu schema cần thầy duyệt trước khi chốt nhãn.

## 7. Cần anh Lâm quyết định

1. Duyệt hướng: PhoBERT-base (Việt) trước, SikuBERT (Hán) sau?
2. Cho phép thí điểm gán nhãn trước bằng LLM (RamCloud) cho bao nhiêu cây? (tốn tiền)
3. Chọn nơi huấn luyện: Colab hay RunPod?
