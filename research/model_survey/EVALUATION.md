# T3 — Đánh giá bằng chứng: CHAT_models (kraken OCR Hán cổ)

> Kết quả T2+T3 của [`../../docs/planning/chinese_genealogy_model_hunt_plan.md`](../../docs/planning/chinese_genealogy_model_hunt_plan.md).
> Log thật: [`trial/real_sample_ocr_log.txt`](./trial/real_sample_ocr_log.txt), [`trial/synthetic_sample_ocr_log.txt`](./trial/synthetic_sample_ocr_log.txt). Bản vá lỗi API kraken 7.x: [`trial/chat_models_demo_fixed.py`](./trial/chat_models_demo_fixed.py). Báo cáo đầy đủ: [`BAO_CAO_DANH_GIA_CHAT_MODELS.md`](./BAO_CAO_DANH_GIA_CHAT_MODELS.md).

## Bảng đánh giá (yêu cầu bắt buộc theo T3)

| Ứng viên | % tên đúng | % quan hệ đúng | License | Effort tích hợp | Giả thuyết được ủng hộ | Độ tin cậy |
|---|---|---|---|---|---|---|
| **CHAT_models** (kraken seg+rec) | **0%** — 0/12 dòng của ảnh scan Hán cổ thật khớp văn bản có nghĩa; 0/9 ký tự của câu gia phả tự tạo (始祖諱文成官至知府娶阮氏生子一人諱德重) được nhận đúng | 0% — không trích được quan hệ (đây là OCR, không phải NER; không có bước quan hệ) | **CC BY-NC 4.0** — cấm thương mại | **Trung bình** (kỹ thuật thấp — pip install sạch, đã có bản vá; nhưng license + chất lượng output là rào cản chính) | Nghiêng về **H1/H2 chưa phân định được** (xem "Điều kiện chưa đủ" bên dưới) — **không ủng hộ** kết luận "khả thi dùng ngay" | **High** cho "không dùng được ngay hôm nay"; **Moderate** cho "có thể khả thi làm baseline sau khi phân định version mismatch" |
| guwen-ner / GuwenBERT | Không đo được — không chạy được (HF Hub bị chặn egress) | Không đo được | Apache-2.0 (tốt) | Không đánh giá được (chưa chạy) | Không kiểm chứng được trong phiên này | — (thiếu bằng chứng thực nghiệm, chỉ có đánh giá lý thuyết dựa trên license/kiến trúc) |
| Jiayan | Không đo được — không chạy được (Google Drive/Baidu bị chặn) | Không đo được | MIT (tốt) | Không đánh giá được (chưa chạy) | Không kiểm chứng được trong phiên này | — |

## Fact vs Inference (đối chiếu trực tiếp với yêu cầu T3)

**[Fact]** Cài đặt `pip install kraken` thành công, không lỗi native, không cần GPU.

**[Fact]** Chạy đúng theo README gốc của repo → im lặng, không lỗi, **không có output** (bug đường dẫn: script tìm ảnh ở `test/`, mẫu nằm ở `demo/`).

**[Fact]** Sau khi sửa đường dẫn, chạy logic gốc → crash `TypeError: 'Segmentation' object is not subscriptable`. Nguyên nhân xác định: `pip install kraken` kéo bản mới nhất (7.1.1), API trả về dataclass thay vì dict như lúc script được viết (2023). Đây là lỗi tương thích phiên bản dependency, **không phải lỗi mô hình**.

**[Fact]** Sau khi vá lỗi (giữ nguyên logic, chỉ đổi cú pháp truy cập), chạy được:
- Ảnh scan Hán cổ thật (`houcunxiansheng.png`, 1011×1433px): segmentation 459.5 giây/trang (CPU), tìm được 12 dòng. Nhận dạng 4 dòng đầu: `""`, `八`, `八一一一一一`, `八八川川八川人○川八川八人川人○川八八川` — không phải văn bản có nghĩa.
- Câu gia phả tự tạo (Hán cổ, render bằng font hiện đại — **giới hạn thực nghiệm cần nêu rõ**: không phải bản in/viết tay cổ, tỉ lệ khung 1:8 khác xa 9:16 lúc huấn luyện): segmentation chia sai 1 cột thành 6 "dòng" giả; nhận dạng ra ký tự sai hoàn toàn so với câu gốc.

**[Suy luận — 2 giả thuyết cạnh tranh, CHƯA phân định]**
- H1: bản thân model `chat_rec.mlmodel` chất lượng kém hơn công bố khi chạy qua kraken hiện tại.
- H2 (có bằng chứng gián tiếp mạnh hơn): cảnh báo runtime `"Using legacy polygon extractor, as the model was not trained with the new method"` cho thấy version mismatch giữa mlmodel (2023) và kraken engine (7.1.1, 2026) làm suy giảm chất lượng trích polygon dòng → recognizer nhận input bị lệch/biến dạng.
- **Test phân định (chưa thực hiện, đề xuất cho Cursor hoặc phiên sau):** cài `kraken<5` (phiên bản cùng thời điểm publish model, ~cuối 2023) trong venv riêng, chạy lại đúng ảnh thật. Output đọc được → H2 đúng (sửa bằng ghim version). Vẫn ra ký tự vô nghĩa → H1 đúng (loại bỏ CHAT_models khỏi shortlist).

## Falsification check (điều gì sẽ đảo ngược kết luận này)

Nếu chạy lại với `kraken<5` cho ra văn bản đọc được có nghĩa trên ảnh scan thật (`houcunxiansheng.png`) → đảo ngược kết luận "không khả thi", CHAT_models trở thành baseline fine-tune hợp lệ (kraken hỗ trợ sẵn `ketos train -i chat_rec.mlmodel <data mới>`).

## Kết luận T3

- **Không đạt điều kiện để tiến hành T4 ("effort Thấp/Trung bình VÀ có bằng chứng ủng hộ H1/H2")** ở dạng dứt khoát: effort kỹ thuật ở mức Trung bình nhưng (a) output hiện tại không dùng được (0% chính xác trên cả 2 test), (b) license CC BY-NC chặn thương mại, (c) nguyên nhân gốc (H1 vs H2) chưa phân định.
- **Khuyến nghị:** chạy thử nghiệm phân định H1/H2 (`kraken<5`) trước khi quyết định viết proposal T4. Đây là việc rẻ (ước lượng vài giờ), rủi ro thấp, và là bước tiếp theo hợp lý duy nhất được ủng hộ bởi bằng chứng hiện có.
- **Phát hiện quan trọng cho luận văn (không phải thất bại tìm kiếm):** không tồn tại mô hình/dataset mã nguồn mở nào giải quyết trực tiếp "gia phả Hán TQ → cây gia phả có cấu trúc" — khoảng trống này là **cơ hội đóng góp học thuật** tiềm năng (xây NER/RE chuyên biệt cho gia phả Hán-Nôm), nên báo lại với giảng viên như vậy thay vì như một tìm kiếm thất bại. **Độ tin cậy: High** — dựa trên tìm kiếm có hệ thống qua nhiều từ khoá Hán/Anh, không tìm thấy repo/dataset khớp trực tiếp.
- guwen-ner (Apache-2.0) và Jiayan (MIT) vẫn là ứng viên NER **lý thuyết** phù hợp hơn CHAT_models cho đúng bài toán downstream (trích tên/quan hệ, không chỉ OCR), nhưng chưa có bằng chứng thực nghiệm vì hạ tầng sandbox chặn HuggingFace/Google Drive — cần thử lại ở môi trường có thể truy cập các host này.
