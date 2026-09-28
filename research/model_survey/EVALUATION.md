# T3 — Đánh giá bằng chứng: CHAT_models (kraken OCR Hán cổ)

> Kết quả T2+T3 của [`../../docs/planning/chinese_genealogy_model_hunt_plan.md`](../../docs/planning/chinese_genealogy_model_hunt_plan.md).
> Log thật: [`trial/real_sample_ocr_log.txt`](./trial/real_sample_ocr_log.txt), [`trial/synthetic_sample_ocr_log.txt`](./trial/synthetic_sample_ocr_log.txt). Bản vá lỗi API kraken 7.x: [`trial/chat_models_demo_fixed.py`](./trial/chat_models_demo_fixed.py). Báo cáo đầy đủ: [`BAO_CAO_DANH_GIA_CHAT_MODELS.md`](./BAO_CAO_DANH_GIA_CHAT_MODELS.md).

## Bảng đánh giá (yêu cầu bắt buộc theo T3)

| Ứng viên | % tên đúng | % quan hệ đúng | License | Effort tích hợp | Giả thuyết được ủng hộ | Độ tin cậy |
|---|---|---|---|---|---|---|
| **CHAT_models** (kraken seg+rec, **với kraken<5**) | **Phần lớn đọc được** — output gồm nhiều đoạn văn/thơ cổ điển có nghĩa (nhan đề, tên tác giả có thật xác minh được), xen một số đoạn ngắn dạng số/ký hiệu lạ. Chưa đếm % dòng-đúng chính xác (cần đối chiếu ground-truth gốc của ảnh, chưa có) | 0% — không trích được quan hệ (đây là OCR, không phải NER; không có bước quan hệ) | **CC BY-NC 4.0** — cấm thương mại | **Trung bình** (kỹ thuật thấp nếu ghim `kraken<5`) | **H2 xác nhận** (version mismatch, không phải model kém) — xem "Tái lập độc lập 27/9" | **High** (quan sát trực tiếp, tái lập được, có mốc kiểm tra độc lập là tên tác giả/nhan đề thơ cổ có thật) |
| **CHAT_models (kraken 7.1.1, không ghim version)** | 0% — như T3 gốc | 0% | CC BY-NC 4.0 | Trung bình nhưng **cấu hình mặc định (`pip install kraken`) vẫn hỏng** nếu không tự ghim `<5` | H1 bị bác bỏ | High |
| guwen-ner / GuwenBERT | **Phồn thể: 0/4** (rỗng); **Giản thể: 3/4** (`文成`, `阮氏`, `德重`; bỏ sót `知府`) | Không đo (không phải task RE) | Apache-2.0 (tốt) | Trung bình — kỹ thuật dễ nhưng cần bước tiền xử lý giản thể hoá (rủi ro với chữ Nôm) | Chạy được, nhưng **nhạy cảm nghiêm trọng với phồn/giản thể** — gia phả Hán-Nôm thật dùng phồn thể → hiệu năng gần 0% nếu không tiền xử lý | **High** cho việc đo được (log trực tiếp); **Moderate** cho việc suy rộng ra dữ liệu Hán-Nôm thật (chưa test trên ảnh/text gia phả thật) |
| Jiayan | Không phải NER — nhưng phân đoạn từ đúng ranh giới `知府`, `阮氏` ở cả phồn/giản thể | Không đo (task khác: tokenize/POS) | MIT (tốt) | Thấp — chạy trực tiếp, không nhạy phồn/giản thể trong test này | Hữu ích như bước tiền xử lý (word segmentation) trước khi đưa vào NER khác, hơn là NER độc lập | **Moderate** — chỉ 1 câu test, cần thêm mẫu để khái quát hoá |

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

## Tái lập độc lập 27/9 (kraken<5, guwen-ner, Jiayan)

> Log thật đã đọc trực tiếp (không dựa vào tường thuật): [`trial/legacy_kraken_test_rerun_log.txt`](./trial/legacy_kraken_test_rerun_log.txt), [`trial/guwen_ner_rerun_log.txt`](./trial/guwen_ner_rerun_log.txt), [`trial/jiayan_rerun_log.txt`](./trial/jiayan_rerun_log.txt). Chạy trên máy khác (ngoài sandbox Claude Code cloud dùng ở T2/T3 gốc — log ghi `cwd: /Users/forestlam/...`), nên không bị chặn egress tới HuggingFace như ghi nhận ở mục 0 của báo cáo T1.

**Lưu ý về phạm vi xác minh:** người dùng báo có một lần chạy nội bộ ngày 26/9 (Cursor, chưa commit) cho ra cùng kết quả; tôi **không có** log 26/9 đó để đối chiếu trực tiếp, nên không xác nhận "khớp 26/9". Những gì dưới đây là kết luận rút ra **chỉ từ 3 file log ngày 27/9** mà tôi tự đọc.

### Nhánh A — Phân định H1 vs H2 (CHAT_models)

**[Fact]** `python demo/chat_models_demo.py` (script GỐC, không dùng bản vá `chat_models_demo_fixed.py`) + `kraken==4.3.13` (thay vì 7.1.1). Chạy 2026-09-27T11:27:55Z → 12:49:13Z (**81 phút 18 giây**), `exit: 0`.

**[Fact]** Output lần này là các đoạn văn/thơ cổ điển **đọc được, có nghĩa**, ví dụ nhan đề nhạc phủ cổ có thật `巫山高` (dòng 14) và bài `贈王主簿二首` ký tên tác giả `謝眺` (Tạ Diểu, thi nhân Nam triều Tề có thật — dòng 18–19) — đối lập hoàn toàn với log kraken 7.1.1 (25/9, dùng bản vá) vốn chỉ ra `八`, `一`, `川` lặp vô nghĩa trên cùng loại ảnh. Cần nêu trung thực: log cũng có vài đoạn ngắn dạng số/ký hiệu lạ xen kẽ (`人`, `上○`, `二二`, `○一八一一○`) — không phải 100% hoàn hảo tuyệt đối, nhưng phần lớn nội dung là văn bản Hán cổ có nghĩa thật.

**Kết luận:** đây là bằng chứng trực tiếp, có thể tái lập, ủng hộ **H2** (nguyên nhân 0% ở T3 gốc là version mismatch giữa `chat_rec.mlmodel` (2023) và kraken engine mới (7.1.1), không phải bản thân model kém) — **bác bỏ H1**. **Độ tin cậy: High** (quan sát trực tiếp, có `diff`-able evidence là nhan đề/tác giả thơ cổ có thật, không phải chuỗi ngẫu nhiên).

**Cập nhật khuyến nghị T3 gốc:** CHAT_models **có thể dùng làm baseline OCR** nếu ghim `kraken<5` — không phải "loại bỏ" như suy đoán trước đây. License CC BY-NC 4.0 (cấm thương mại) vẫn nguyên — không đổi.

### Nhánh B — guwen-ner và Jiayan (lần đầu chạy thử được trong repo này — trước đó bị chặn hoàn toàn ở T1/T2)

**[Fact] guwen-ner** trên câu mẫu `始祖諱文成官至知府娶阮氏生子一人諱德重`:
- Bản **phồn thể** (nguyên gốc, đúng dạng chữ Hán-Nôm thật sẽ gặp): `[]` — **0 thực thể nhận được**.
- Bản **giản thể** (chuyển đổi nhân tạo, KHÔNG phải dạng chữ gia phả Hán-Nôm thật): 3 thực thể — `文成` (score 0.967), `阮氏` (0.817), `德重` (0.948), nhãn chung `NOUN_OTHER` (không phải nhãn "person"/"official title" riêng biệt). Bỏ sót `知府` (chức quan).

**[Suy luận, High confidence vì đối lập rõ giữa 2 dòng log liền kề, cùng câu, chỉ khác phồn/giản thể]** guwen-ner rất nhạy với biến thể phồn thể/giản thể — model được huấn luyện chủ yếu trên dữ liệu giản thể hiện đại hoá, nên **gần như vô dụng (0%) trên đúng dạng chữ phồn thể** mà gia phả Hán-Nôm Việt Nam sẽ dùng, trừ khi tiền xử lý chuyển giản thể trước (bản thân bước chuyển đổi này có rủi ro sai nghĩa với chữ Nôm không có trong bảng ánh xạ giản/phồn chuẩn).

**[Fact] Jiayan** trên cùng câu (cả 2 bản phồn/giản thể): phân đoạn từ đúng ranh giới cho các cụm quan trọng — `知府` (chức quan) và `阮氏` (tên có họ) đều được tách thành 1 token riêng đúng nghĩa ở cả 2 bản; gắn nhãn POS hợp lý (`nh` cho `阮氏` — có vẻ là nhãn "human name"). Không nhạy cảm phồn/giản thể như guwen-ner trong test này.

## Kết luận T3 (cập nhật sau tái lập 27/9 — thay thế kết luận "chưa đủ điều kiện T4" ở bản gốc)

- **H2 được xác nhận bằng thực nghiệm tái lập được** (không còn là suy luận): CHAT_models 0% chính xác ở T3 gốc là do version mismatch kraken (7.1.1 vs 2023), **không phải model kém**. Ghim `kraken<5` là điều kiện bắt buộc, không phải tuỳ chọn, nếu dùng CHAT_models.
- **Điều kiện T4 nay đã đạt một phần:** CHAT_models có bằng chứng thực nghiệm ủng hộ H2 với effort Trung bình (ghim version + fine-tune) — đủ điều kiện viết proposal T4 **cho mục đích nghiên cứu/luận văn phi thương mại** (license CC BY-NC vẫn cấm thương mại — đây là ràng buộc cứng, không đổi dù kỹ thuật đã khả thi hơn).
- guwen-ner (Apache-2.0) và Jiayan (MIT) giờ có bằng chứng thực nghiệm thật (không còn "chưa kiểm chứng được"): guwen-ner chạy được nhưng gần như vô dụng trên phồn thể (dạng chữ Hán-Nôm thật sẽ gặp) nếu không tiền xử lý; Jiayan hữu ích như bước tách từ tiền xử lý.
- **T4 (đề xuất nâng cấp) — chưa viết trong phiên này.** Cursor có đề cập đã soạn 1 bản nhưng chưa được push/commit vào repo này (không có file nào trong `docs/planning/` khớp tên `hannom_ner_model_upgrade_proposal.md` tại thời điểm 2026-09-28) — không thể xác minh hay dùng lại nội dung đó. Nếu cần, viết T4 mới dựa trên bảng bằng chứng đã cập nhật ở trên, ưu tiên kiến trúc: Jiayan (tách từ) → guwen-ner (NER, cần tiền xử lý phồn→giản có kiểm soát) hoặc CHAT_models (`kraken<5`, ghim version) làm baseline OCR fine-tune.
- **Phát hiện quan trọng cho luận văn (không đổi):** không tồn tại mô hình/dataset mã nguồn mở nào giải quyết trực tiếp "gia phả Hán TQ → cây gia phả có cấu trúc" — khoảng trống này vẫn là **cơ hội đóng góp học thuật** tiềm năng. **Độ tin cậy: High.**
