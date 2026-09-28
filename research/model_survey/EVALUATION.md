# T3 — Đánh giá bằng chứng: CHAT_models (kraken OCR Hán cổ)

> Kết quả T2+T3 của [`../../docs/planning/chinese_genealogy_model_hunt_plan.md`](../../docs/planning/chinese_genealogy_model_hunt_plan.md).
> Log thật: [`trial/real_sample_ocr_log.txt`](./trial/real_sample_ocr_log.txt), [`trial/synthetic_sample_ocr_log.txt`](./trial/synthetic_sample_ocr_log.txt). Bản vá lỗi API kraken 7.x: [`trial/chat_models_demo_fixed.py`](./trial/chat_models_demo_fixed.py). Báo cáo đầy đủ: [`BAO_CAO_DANH_GIA_CHAT_MODELS.md`](./BAO_CAO_DANH_GIA_CHAT_MODELS.md).

## Bảng đánh giá (yêu cầu bắt buộc theo T3)

| Ứng viên | % tên đúng | % quan hệ đúng | License | Effort tích hợp | Giả thuyết được ủng hộ | Độ tin cậy |
|---|---|---|---|---|---|---|
| **CHAT_models** (kraken seg+rec, **với kraken<5**) | **Phần lớn đọc được** — output gồm nhiều đoạn văn/thơ cổ điển có nghĩa (nhan đề, tên tác giả có thật xác minh được), xen một số đoạn ngắn dạng số/ký hiệu lạ. Chưa đếm % dòng-đúng chính xác (cần đối chiếu ground-truth gốc của ảnh, chưa có) | 0% — không trích được quan hệ (đây là OCR, không phải NER; không có bước quan hệ) | **CC BY-NC 4.0** — cấm thương mại | **Trung bình** (kỹ thuật thấp nếu ghim `kraken<5`) | **H2 xác nhận** (version mismatch, không phải model kém) — xem "Tái lập độc lập 27/9" | **High** (quan sát trực tiếp, tái lập được, có mốc kiểm tra độc lập là tên tác giả/nhan đề thơ cổ có thật) |
| **CHAT_models (kraken 7.1.1, không ghim version)** | 0% — như T3 gốc | 0% | CC BY-NC 4.0 | Trung bình nhưng **cấu hình mặc định (`pip install kraken`) vẫn hỏng** nếu không tự ghim `<5` | H1 bị bác bỏ | High |
| guwen-ner / GuwenBERT | **[ĐÃ SỬA, xem "Thực nghiệm Colab mở rộng"]** Trên 1 câu tự soạn: 0/4 phồn thể, 3/4 giản thể. Nhưng trên **9 đoạn Sử Ký thật**: **95% phồn thể, 97.5% giản thể** — gần như không khác biệt | Không đo (không phải task RE) | Apache-2.0 (tốt) | Thấp-Trung bình — chạy tốt trên văn phong sử/truyện ký thật; rủi ro còn lại là từ vựng riêng của gia phả (`諱`...) chưa test đủ | Kết luận cũ "vô dụng trên phồn thể" bị **bác bỏ** khi test trên mẫu lớn hơn (n=1 → không đại diện). Vẫn cần test trên câu/đoạn gia phả THẬT (không tự soạn) trước khi kết luận chắc chắn | **High** cho kết quả trên Sử Ký (n=9, có nguồn xác minh); **Moderate** cho khả năng tổng quát sang đúng văn phong gia phả Hán-Nôm (chưa có dữ liệu thật) |
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

## Thực nghiệm Colab mở rộng — ĐẢO NGƯỢC 1 kết luận quan trọng

> Chạy trên Google Colab (GPU Tesla T4, không bị chặn egress). Log/JSON thật đọc trực tiếp (không phải tường thuật): [`colab/results/A_guwen_ner.json`](./colab/results/A_guwen_ner.json), [`colab/results/B_sikubert_fillmask.json`](./colab/results/B_sikubert_fillmask.json), [`colab/results/C_kraken_bench.json`](./colab/results/C_kraken_bench.json) + các file `.txt`/`.jsonl` kèm theo. Notebook nguồn: [`colab/hannom_model_experiments.ipynb`](./colab/hannom_model_experiments.ipynb).

### ⚠️ Sửa lại kết luận trước: "guwen-ner gần như vô dụng trên phồn thể" — SAI, dựa trên mẫu quá nhỏ (n=1 câu)

**[Fact]** Chạy `guwen-ner` trên **9 đoạn Sử Ký thật** (孔子世家, 項羽本紀, 高祖本紀, 老子韓非列傳, 留侯世家..., lấy từ Kanripo, pin commit `1c19dc6f`, có `assert` xác nhận đoạn trích khớp nguyên văn nguồn — không bịa dữ liệu), đo recall tên người (lenient) từng đoạn:

| | Phồn thể (trad) | Giản thể (simp) |
|---|---|---|
| Recall tên người (P1–P9, micro) | **95% (38/40)** | 97.5% (39/40) |
| Recall exact | 85% (34/40) | 95% (38/40) |
| Tỷ lệ ký tự → `[UNK]` | 16.6% (55/331) | 0% |

**Script tự tính "verdict" theo tiêu chí đặt trước** (support: trad≤10% & simp≥50%; reject: trad≥50%): kết quả trả về **"BÁC BỎ 'vô dụng trên phồn thể' (phồn ≥ 50%)"**.

**Đối chiếu với câu P0 (câu tự soạn 26–27/9, `始祖諱文成官至知府娶阮氏生子一人諱德重`):** tái lập đúng y hệt kết luận cũ — **0/3 trên phồn thể, 3/3 trên giản thể**. Tức kết luận "yếu trên phồn thể" tuần trước **không sai vì đo sai**, mà sai vì **khái quát hoá từ đúng 1 câu tự soạn** lên toàn bộ "văn bản phồn thể nói chung" — một sai lầm suy luận cổ điển (mẫu n=1, không đại diện).

**Suy luận mới (Moderate-High confidence):** vấn đề không phải "phồn thể" nói chung, mà nhiều khả năng là **từ vựng/quy ước riêng của thể loại gia phả** (ví dụ `諱` — chữ chuyên dùng trước tên huý tổ tiên trong gia phả, hiếm gặp trong văn phong sử ký/truyện ký mà guwen-ner được huấn luyện) khiến câu P0 rơi vào phân phối lạ, không phải vì bản thân bộ chữ phồn thể. **Cần bộ test bằng câu gia phả THẬT (không tự soạn) để kết luận chắc chắn** — đây là giới hạn còn lại, chưa giải quyết được.

**Falsification check đã tự chạy (đúng tinh thần T3):** nếu có ≥1 đoạn Sử Ký thật mà trad tệ hơn hẳn simp thì nghi ngờ "phồn thể nói chung yếu" được củng cố lại — thực tế: `sign_test` cho `wins=1, losses=1, ties=7` (hầu hết đoạn HOÀ, không nghiêng hẳn bên nào) → không có bằng chứng hệ thống rằng phồn thể kém hơn giản thể trên văn bản thật.

### Nhóm B — SikuBERT vs GuwenBERT (fill-mask, license đã xác nhận cả 2 Apache-2.0)

**[Fact]** Cả `SIKU-BERT/sikubert` và `ethanyt/guwenbert-base` đều **Apache-2.0** (tra trực tiếp qua HF API, không phải "chưa rõ" như candidates.md ghi trước đây).

**[Fact]** Độ chính xác dự đoán ký tự nền (không phải thực thể) khi che 1 ký tự, top-1, trên 9 đoạn Sử Ký:

| Model | Phồn thể | Giản thể | Chênh lệch (giản − phồn) | UNK trên phồn thể |
|---|---|---|---|---|
| **SikuBERT** | **45.0%** (77/171) | 34.5% (59/171) | **−10.5%** (tốt hơn trên phồn thể) | **0/171 — không UNK** |
| GuwenBERT-base | 45.6% (78/171) | 74.9% (128/171) | **+29.2%** (tệ hơn hẳn trên phồn thể) | 34/171 (~20%) |

**Kết luận (High confidence — kết quả sạch, đối lập rõ, khớp cả 3 nguồn độc lập: NER tuần này với P0, thí nghiệm labmate về guwen-punc, và fill-mask này):** SikuBERT xử lý phồn thể **tốt hơn hẳn** GuwenBERT về mặt tokenizer/OOV (0% vs 20% UNK) và không bị lệch hiệu năng theo phồn/giản thể như GuwenBERT. **Nên ưu tiên SikuBERT làm nền tảng fine-tune**, không phải GuwenBERT — khuyến nghị này giờ có 3 bằng chứng độc lập ủng hộ, không còn là suy luận đơn lẻ.

### Nhóm C — Benchmark GPU kraken<5 + CHAT_models

**[Fact]** `kraken==4.3.13` cài được trong venv Colab sau khi vá lỗi `setuptools<81` (xem commit `ff5908e`). CHAT_models HEAD khớp đúng `9b86ab6c...` (đúng bản đã dùng 27/9).

**[Fact]** Cùng ảnh `houcunxiansheng.png`, cùng máy: **segmentation CPU 601.1s vs GPU 15.9s → tăng tốc 37.8 lần**. Độ giống văn bản giữa 2 lần chạy CPU/GPU: 97.3% (gần như y hệt, GPU không làm giảm chất lượng).

**[Fact]** Đối chứng dương (3 chuỗi mốc từ log 27/9: `巫山高`, `謝眺`, `恭惟某官`) đều xuất hiện lại trong output GPU/CPU trên Colab → **tái lập thành công H2 lần thứ 2, trên máy/hạ tầng khác** (Mac local 27/9 → Colab GPU) — củng cố thêm độ tin cậy, không còn phụ thuộc 1 máy duy nhất.

**[Fact] Thử fine-tune tốc độ (`ketos segtrain`/`train`) — THẤT BẠI do lỗi cú pháp CLI, không phải lỗi hạ tầng:** cả 4 lần gọi đều báo `Error: Invalid value for '-q'/'--quit': 'fixed' is not one of 'early', 'dumb'.` — tham số `-q fixed` không hợp lệ với kraken 4.3.13 (đúng phải là `-q dumb` để chạy đúng N epoch không early-stop). Đây là lỗi trong script notebook (chưa tra cứu kỹ CLI `ketos --help` trước khi dùng), **chưa đo được tốc độ fine-tune/epoch** — vẫn là việc còn thiếu.

## Kết luận T3 (cập nhật sau tái lập 27/9 — thay thế kết luận "chưa đủ điều kiện T4" ở bản gốc)

- **H2 được xác nhận bằng thực nghiệm tái lập được LẦN 2** (Mac local 27/9 → Colab GPU): CHAT_models 0% chính xác ở T3 gốc là do version mismatch kraken (7.1.1 vs 2023), **không phải model kém**. Ghim `kraken<5` là điều kiện bắt buộc, không phải tuỳ chọn, nếu dùng CHAT_models. GPU tăng tốc segmentation **37.8 lần** so với CPU (601s → 15.9s/trang) — khả thi cho pipeline xử lý hàng loạt nếu có GPU.
- **Kết luận về guwen-ner đã bị đảo ngược một phần** (xem "Thực nghiệm Colab mở rộng"): KHÔNG còn đúng là "gần như vô dụng trên phồn thể" — trên 9 đoạn Sử Ký thật, recall tên người đạt 95% phồn thể / 97.5% giản thể, gần như ngang nhau. Kết luận cũ chỉ đúng cho đúng 1 câu tự soạn (n=1), không đại diện. **Vẫn còn thiếu:** test trên câu/đoạn gia phả Hán-Nôm THẬT (không phải Sử Ký hay câu tự soạn) để biết hiệu năng thật trên đúng thể loại.
- **SikuBERT được xác nhận là nền tảng tốt hơn GuwenBERT** để fine-tune tiếp — bằng chứng hội tụ từ 3 nguồn độc lập: (1) fill-mask Colab (SikuBERT 0% UNK trên phồn thể vs GuwenBERT ~20% UNK), (2) NER tuần này, (3) thí nghiệm guwen-punc của labmate (F1 0.195, kết luận overfitting).
- **Điều kiện T4 nay đã đạt:** cả CHAT_models (OCR, non-commercial) lẫn hướng NER (guwen-ner hoặc SikuBERT fine-tune) đều có bằng chứng thực nghiệm đủ mạnh để viết proposal T4 **cho mục đích nghiên cứu/luận văn phi thương mại** (license CC BY-NC của CHAT_models vẫn cấm thương mại — ràng buộc cứng, không đổi).
- **Việc còn thiếu, chưa đo được:** tốc độ fine-tune (`ketos train`/`segtrain`) — 4 lần thử đều lỗi cú pháp CLI (`-q fixed` không hợp lệ, phải là `-q dumb`), chưa phải lỗi hạ tầng, dễ sửa nhưng chưa làm.
- **Phát hiện quan trọng cho luận văn (không đổi):** không tồn tại mô hình/dataset mã nguồn mở nào giải quyết trực tiếp "gia phả Hán TQ → cây gia phả có cấu trúc" — khoảng trống này vẫn là **cơ hội đóng góp học thuật** tiềm năng. **Độ tin cậy: High.**
