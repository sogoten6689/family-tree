# Báo cáo: Khảo sát và thử nghiệm các mô hình có sẵn cho gia phả Trung Quốc (家谱/族谱)

**Ngày thực hiện:** 25/09/2026
**Bối cảnh:** Theo yêu cầu của giảng viên hướng dẫn tại buổi họp 14/9/2026 ("Tìm các mô hình đã có cho gia phả Trung Quốc — cố dùng Claude để lùng, tải về và thử chạy"), báo cáo này ghi lại quá trình tìm kiếm, lựa chọn và **chạy thử thực tế** một mô hình mã nguồn mở liên quan đến xử lý văn bản Hán cổ / gia phả Trung Quốc, nhằm đánh giá khả năng tích hợp vào pipeline của dự án family-tree.

**Nguyên tắc trình bày:** Các mục đánh dấu **[Quan sát/Fact]** là kết quả quan sát trực tiếp (lệnh đã chạy, log thực tế). Các mục đánh dấu **[Suy luận/Inference]** là đánh giá/diễn giải chủ quan dựa trên bằng chứng đó.

**Tóm tắt nhanh (executive summary):** Không tìm thấy mô hình mã nguồn mở nào giải quyết trực tiếp bài toán "gia phả Trung Quốc → cây gia phả có cấu trúc". Ứng viên NER cổ văn phù hợp nhất về lý thuyết (guwen-ner/GuwenBERT, Apache-2.0) và toolkit Jiayan (MIT) **không thể chạy thử được** trong sandbox này vì HuggingFace Hub và Google Drive đều bị chặn bởi chính sách egress của tổ chức. Ứng viên duy nhất thực sự **clone-và-chạy-được** là **CHAT_models** (OCR cho Hán văn cổ dạng dọc, license CC BY-NC 4.0) — repo này cài đặt sạch nhưng README có bug (path mismatch) và code demo bị lỗi do kraken (dependency) đã thay đổi API kể từ khi repo viết năm 2023; sau khi tự vá lỗi, chạy được nhưng rất chậm trên CPU (459.5 giây/trang chỉ riêng bước segmentation) và cho kết quả nhận dạng **không đọc được thành văn bản có nghĩa** (chuỗi ký tự rỗng hoặc lặp vô nghĩa) cả trên ảnh scan thật của repo lẫn trên câu Hán cổ tự tạo — nhiều khả năng do kraken engine hiện tại (7.1.1) không tương thích tối ưu với định dạng mlmodel cũ (2023), chưa kiểm chứng được với phiên bản kraken cùng thời. Khuyến nghị: dùng làm baseline/tài liệu tham khảo cho nghiên cứu, không dùng thẳng cho sản xuất; xem Mục 5 để biết chi tiết và mức độ tin cậy từng khuyến nghị.

---

## 0. Ràng buộc môi trường quan trọng (Fact — ảnh hưởng quyết định đến toàn bộ báo cáo)

**[Quan sát/Fact]** Môi trường sandbox chạy phiên làm việc này có một egress proxy chặn theo chính sách tổ chức (organization policy, trả về `403 connect_rejected`, không phải lỗi mạng tạm thời) đối với các host sau, đã kiểm chứng trực tiếp bằng `curl`:

| Host | Kết quả |
|---|---|
| `huggingface.co` | 403 CONNECT tunnel failed (org policy) |
| `cdn-lfs.huggingface.co` | 403 CONNECT tunnel failed (org policy) |
| `hf-mirror.com` | 403 CONNECT tunnel failed (org policy) |
| `modelscope.cn` / `www.modelscope.cn` | 403 CONNECT tunnel failed (org policy) |
| `drive.google.com` | 403 CONNECT tunnel failed (org policy) |
| `zenodo.org` | 403 CONNECT tunnel failed (org policy) |
| `github.com`, `raw.githubusercontent.com`, `objects.githubusercontent.com` | Reachable (git clone hoạt động bình thường) |
| `pypi.org`, `files.pythonhosted.org` | Reachable (HTTP 200, nằm trong danh sách no-proxy) |
| `*.github.io` (GitHub Pages, ví dụ demo online của guwen-models) | 403 CONNECT tunnel failed (org policy) — không xem được demo online |

**Ý nghĩa:** Bất kỳ mô hình nào chỉ phân phối trọng số qua HuggingFace Hub, ModelScope, Google Drive hoặc Zenodo **không thể tải về được trong môi trường này**, bất kể chất lượng hay license của mô hình đó. Điều này loại trực tiếp các ứng viên mạnh nhất về mặt lý thuyết cho bài toán NER cổ văn (GuwenBERT/guwen-ner, SikuBERT — đều host trên HuggingFace) và Jiayan (host trên Google Drive/Baidu NetDisk) khỏi khả năng **chạy thử thực tế** trong phiên này, dù mã nguồn của chúng có sẵn công khai trên GitHub.

Đây là lý do quyết định tại sao ứng viên được chọn để chạy thử ở Mục 2 là một repo host trọng số **trực tiếp trong git repository trên GitHub** (không qua HF/Zenodo).

---

## 1. Danh sách repo/model đã khảo sát

Tìm kiếm bằng các từ khóa: "家谱 NER 知识图谱", "GuwenBERT genealogy", "OCR vertical classical Chinese old book scans", "族谱数字化 知识图谱", "classical-chinese GitHub topics". Không tìm thấy mô hình nào được huấn luyện/tinh chỉnh **chuyên biệt cho văn bản 家谱/族谱** với code chạy được công khai (hạng mục "trực tiếp phân tích 家谱/族谱 thành cây gia phả" — mục tiêu tìm kiếm ưu tiên nhất — **không có ứng viên trực tiếp**, chỉ có công cụ tổng quát về Hán cổ hoặc quan hệ nhân vật hiện đại có thể dùng làm nền tảng). Đây là một quan sát quan trọng, không phải giả định: hạng mục cụ thể nhất mà giảng viên yêu cầu ("mô hình cho gia phả Trung Quốc") dường như chưa tồn tại dưới dạng mô hình/dataset mã nguồn mở sẵn có; các ứng viên tìm được đều là công cụ NLP/OCR Hán cổ tổng quát cần được áp dụng/tinh chỉnh thêm.

### 1.1 OCR cho chữ Hán cổ/dọc (scan sách cổ)

| Tên | Link | Ghi chú | License |
|---|---|---|---|
| **CHAT_models** (đã chọn chạy thử) | https://github.com/colibrisson/CHAT_models | Mô hình kraken (segmentation + recognition) huấn luyện trên 1.7 triệu dòng văn bản Hán cổ in/viết tay, thế kỷ 10–20, dự án Numerica Sinologica (Pháp), có liên kết tài trợ tới "Vietnamica project ERC 833933" | CC BY-NC 4.0 |
| CnOCR | https://github.com/breezedeus/cnocr | OCR tiếng Trung tổng quát, hỗ trợ văn bản dọc, không chuyên biệt Hán cổ | Xem repo (MIT lõi, một số model phái sinh có điều kiện) |
| chinese-pdf-ocr-toolkit | https://github.com/MH-API/chinese-pdf-ocr-toolkit | Pipeline OCR sách scan tiếng Trung, dùng VLM (cần API key ngoài, không phải mô hình cục bộ) + tesseract offline | Chưa kiểm tra kỹ (không chạy thử) |
| sanskrit-ocr (tham khảo phương pháp) | https://github.com/ihdia/sanskrit-ocr | Không phải tiếng Trung, chỉ tham khảo kiến trúc | — |

### 1.2 NER cổ văn (Classical Chinese) — tên người, chức quan, quan hệ thân tộc

| Tên | Link | Ghi chú | License | Khả năng chạy trong môi trường này |
|---|---|---|---|---|
| **guwen-ner** (dựa trên GuwenBERT) | https://huggingface.co/ethanyt/guwen-ner (index tại https://github.com/Ethan-yt/guwen-models) | NER cổ văn, có ví dụ suy luận qua `transformers` + tùy chọn giải mã CRF (`crf_example.ipynb`) | Apache-2.0 | **[Fact] Không tải được** — host trên HuggingFace Hub, bị chặn (Mục 0) |
| GuwenBERT (base/large) | https://github.com/Ethan-yt/guwenbert | Pretrained LM nền tảng cho các model guwen-* | Apache-2.0 | Không tải được (HF Hub) |
| SikuBERT/SikuRoBERTa | https://huggingface.co/SIKU-BERT/sikubert | Pretrained trên Tứ khố toàn thư | Chưa rõ | Không tải được (HF Hub) |
| Jiayan (甲言) | https://github.com/jiaeyan/Jiayan | Toolkit phân đoạn từ/POS/ngắt câu/thêm dấu câu cho cổ văn, cài qua `pip install jiayan` | MIT | **[Fact] Không tải được** — trọng số host trên Google Drive/Baidu NetDisk, bị chặn (Mục 0) |
| UD-Kanbun | https://github.com/KoichiYasuoka/UD-Kanbun | Phân đoạn từ, POS, phân tích cú pháp cho Kanbun (Hán văn cổ kiểu Nhật) | Chưa kiểm tra | Chưa thử |

### 1.3 Trích xuất quan hệ / knowledge graph nhân vật (person relation extraction)

| Tên | Link | Ghi chú | License |
|---|---|---|---|
| PersonRelationKnowledgeGraph | https://github.com/liuhuanyong/PersonRelationKnowledgeGraph | Xây KG quan hệ nhân vật **tiếng Trung hiện đại** (không phải cổ văn/gia phả), có từ điển tên người + loại quan hệ có sẵn trong repo, phụ thuộc Scrapy để crawl dữ liệu huấn luyện | Không ghi rõ license trong repo (rủi ro) |
| PersonGraphDataSet | https://github.com/liuhuanyong/PersonGraphDataSet | Dataset ~10 vạn cặp quan hệ nhân vật tiếng Trung hiện đại, không phải model | Không ghi rõ |
| DeepKE (zjunlp) | https://github.com/zjunlp/DeepKE | Toolkit NER/RE tổng quát, có cnSchema off-the-shelf, nhưng README khuyến nghị tải pretrained model từ HuggingFace trước khi dùng — cùng vướng chặn HF | MIT (nhưng phụ thuộc HF) |

### 1.4 Công cụ quản lý cây gia phả (không phải NLP, chỉ để tham khảo cấu trúc dữ liệu)

- https://github.com/snssv/jiapu — hệ thống quản lý gia phả trực tuyến, có mô hình dữ liệu cha/con + vợ/chồng + con nuôi, hữu ích tham khảo schema nhưng không phải NLP/OCR.
- https://github.com/KirigiriSuzumiya/family-tree — hệ thống nhận diện khuôn mặt + gia phả, không liên quan trực tiếp đến xử lý văn bản.

**Shortlist 2–3 ứng viên khả thi nhất (có thể clone/chạy được, không chỉ là paper):**
1. **guwen-ner / GuwenBERT** (Ethan-yt) — phù hợp nhất về mặt học thuật cho NER cổ văn (tên người, có khả năng bao gồm chức quan) nhưng **không chạy được trong môi trường hiện tại** do chặn HuggingFace.
2. **Jiayan** — toolkit MIT đầy đủ (phân đoạn từ, POS, ngắt câu cổ văn) nhưng **không chạy được** do trọng số host trên Google Drive (bị chặn).
3. **CHAT_models** (Numerica Sinologica / Colin Brisson et al.) — **duy nhất trong 3 ứng viên có trọng số nằm ngay trong git repo trên GitHub**, do đó là ứng viên duy nhất thực sự chạy thử được trong sandbox này. Được chọn cho Mục 2.

---

## 2. Repo đã chọn chạy thử + lý do

**Repo:** https://github.com/colibrisson/CHAT_models ("Chinese Historical documents Automatic Transcription")

**Lý do chọn (dựa trên bằng chứng, không phải chỉ vì nó dễ nhất):**
- **[Fact]** Đây là ứng viên OCR duy nhất trong danh sách khảo sát mà file trọng số mô hình (`chat_seg.mlmodel` 5.0MB, `chat_rec.mlmodel` 42.5MB) nằm trực tiếp trong git repository (không qua Git-LFS pointer, không qua HuggingFace/Zenodo) — xác nhận bằng `git clone` thành công và `ls -la` cho thấy kích thước file thực (không phải text pointer vài trăm byte).
- **[Fact]** Repo có sẵn dữ liệu mẫu thực (2 ảnh scan trang gia phả/sách cổ Hán văn: `houcunxiansheng.png`, `yutaixinyong.png`) và script demo (`demo/chat_models_demo.py`), tức đáp ứng đúng yêu cầu "chạy trên sample data của chính repo".
- **[Suy luận/Inference]** Về mặt chủ đề, đây là loại tài liệu gần nhất với gia phả Hán-Nôm mà nhóm tìm được: văn bản Hán cổ dạng dọc, in mộc bản/viết tay, thế kỷ 10–20 — cùng thời kỳ và cùng phong cách trình bày (cột dọc, mật độ chữ cao) với gia phả chữ Hán/Hán-Nôm Việt Nam, dù bản thân nó không phải OCR gia phả (譜) chuyên biệt.
- Điểm đáng chú ý: phần "Acknowledgement" của README ghi nhận tài trợ từ **"Vietnamica project (ERC 833933)"** — một dự án nghiên cứu văn bản Việt Nam — cho thấy nhóm tác giả có quan tâm tới ngữ liệu Việt Nam, dù CHAT_models tự thân được huấn luyện trên ngữ liệu Trung Quốc.

### Quá trình cài đặt

**[Fact]** Cài đặt trong venv Python 3.11 sạch:
```
python3 -m venv venv && source venv/bin/activate
pip install kraken
```
Kết quả: **cài đặt thành công, không lỗi**, kéo theo ~90 gói phụ thuộc (torch 2.14.0 CPU+CUDA wheels, torchvision, pytorch-lightning, scikit-image, coremltools, v.v.). Không cần GPU để cài; không có bước biên dịch native nào thất bại. Tổng thời gian cài đặt vài phút (giới hạn bởi băng thông tải gói, tất cả từ PyPI — không bị chặn).

**[Fact]** Phát hiện một lỗi nhỏ trong repo: script `demo/chat_models_demo.py` đọc ảnh từ thư mục `<cwd>/test/*.png`, nhưng 2 ảnh mẫu đi kèm nằm ở `demo/*.png`. Chạy đúng như hướng dẫn trong README (`python demo/chat_models_demo.py` từ thư mục gốc repo) **không báo lỗi nhưng cũng không tạo ra output nào** — vòng lặp `test_dir.glob("*.png")` rỗng nên chương trình chỉ in `"Done!"` mà không xử lý ảnh nào. Đây là một mismatch đường dẫn trong chính repo gốc (chưa được sửa upstream tại thời điểm khảo sát), không phải lỗi do môi trường của chúng tôi. Để chạy thử thực sự, chúng tôi tạo thư mục `test/` và copy 2 ảnh mẫu vào đó (`cp demo/*.png test/`) — đây là chỉnh sửa tối thiểu, chỉ trong scratchpad, không đụng tới mã nguồn gốc.

- **[Fact — lần chạy thứ 1, chỉ sửa đường dẫn ảnh, giữ nguyên logic gốc của repo]** Sau khi sửa đường dẫn, script chạy khoảng 7-8 phút trên CPU (segmentation trên ảnh full-page ~1000x1400px), sau đó **crash** với lỗi:
  ```
  TypeError: 'Segmentation' object is not subscriptable
  ```
  tại dòng `for line in baseline_seg["lines"]:` trong hàm `check_line_direction()` của chính `demo/chat_models_demo.py`.

  **Phân tích nguyên nhân gốc (root cause):** `pip install kraken` (không ghim version) cài **kraken 7.1.1** (bản mới nhất tại 25/09/2026). Trong các phiên bản kraken hiện tại, `kraken.blla.segment()` trả về object `kraken.containers.Segmentation` (dataclass, truy cập bằng `.lines`, mỗi dòng là `BaselineLine` truy cập bằng `.baseline`), thay vì dict như API cũ (`["lines"]`, `["baseline"]`) mà script demo của repo (viết năm 2023) giả định. Đây là **lỗi tương thích do dependency không ghim phiên bản (unpinned/deprecated API)**, không phải lỗi của mô hình `.mlmodel` hay do thiếu GPU. Repo không có `requirements.txt` hay ghim `kraken==<version cũ>`, nên bất kỳ ai làm theo đúng README hôm nay đều gặp lỗi này.

- **[Fact — lần chạy thứ 2, đã tự vá lỗi tương thích]** Chúng tôi viết bản `demo/chat_models_demo_fixed.py` (chỉ trong scratchpad, không sửa file gốc trong git repo đã clone) thay `baseline_seg["lines"]`/`line["baseline"]` bằng `baseline_seg.lines`/`line.baseline` theo API mới của kraken 7.1.1. Kết quả chạy thực tế: xem Mục 3 ngay bên dưới.

---

## 3. Kết quả chạy thử thực tế (Fact)

### 3.1 Chạy trên dữ liệu mẫu có sẵn của repo (ảnh scan Hán văn cổ thật)

**[Fact]** Sau khi vá lỗi API (Mục 2), chạy `python demo/chat_models_demo_fixed.py` trên 2 ảnh mẫu gốc của repo (`houcunxiansheng.png` 1011×1433px, `yutaixinyong.png` 892×1456px — cả hai là scan trang sách/tài liệu Hán văn cổ dạng cột dọc).

- **[Fact] Thời gian đo được chính xác:** segmentation của `houcunxiansheng.png` (1011×1433px) hoàn tất sau **459.5 giây (7 phút 40 giây)**, tìm được **12 dòng/cột văn bản**. Đây là số đo trực tiếp từ code tự thêm `time.time()`, không phải ước lượng. Đây là **fact quan trọng cho đánh giá effort vận hành**: mô hình này không phù hợp để chạy real-time trên CPU cho một pipeline xử lý nhiều trang gia phả (một cuốn gia phả vài chục-vài trăm trang sẽ mất nhiều giờ chỉ riêng bước segmentation nếu chạy tuần tự trên CPU); cần GPU hoặc chấp nhận độ trễ, hoặc batch hoá khi tích hợp.

- **[Fact] Kết quả nhận dạng (recognition) trên 4/12 dòng đầu tiên** (dừng thực nghiệm ở dòng thứ 4 để tiết kiệm thời gian sau khi đã có đủ bằng chứng rõ ràng — xem giải thích bên dưới; log đầy đủ lưu tại `CHAT_models/real_sample_ocr_log.txt` trong scratchpad):

  ```
  line 01: (rỗng)
  line 02: 八
  line 03: 八一一一一一
  line 04: 八八川川八川人○川八川八人川人○川八八川
  ```

  Cảnh báo runtime đi kèm: `UserWarning: Using legacy polygon extractor, as the model was not trained with the new method. Please retrain your model to get speed improvement.`

  **Phân tích (Root cause — 2 giả thuyết cạnh tranh, chưa phân định dứt khoát):**
  - **H1 (Suy luận, Moderate confidence):** Bản thân dữ liệu/mô hình `chat_rec.mlmodel` có chất lượng nhận dạng kém hơn công bố (>99% accuracy trong README) khi chạy qua pipeline kraken hiện tại.
  - **H2 (Suy luận, Moderate-High confidence — có bằng chứng gián tiếp ủng hộ mạnh hơn H1):** Model được lưu ở định dạng cũ, buộc kraken 7.1.1 phải dùng "legacy polygon extractor" (theo đúng cảnh báo runtime) — một code path cũ/kém tối ưu hơn dùng khi model "không được huấn luyện với phương pháp mới". Kết hợp với việc chúng tôi phải tự vá lỗi API ở Mục 2 (bằng chứng rằng model+script này được viết cho một phiên bản kraken cũ hơn nhiều so với 7.1.1 hiện tại), giả thuyết hợp lý hơn là: **có version mismatch giữa mlmodel (2023) và kraken engine (2026) làm suy giảm chất lượng trích xuất polygon dòng chữ**, dẫn đến các vùng ảnh đưa vào recognizer bị lệch/biến dạng, sinh ra output lặp ký tự đặc trưng của lỗi CTC decode trên input nhiễu (八, 一, 川 lặp lại) — không nhất thiết phản ánh đúng chất lượng gốc của mô hình khi chạy với phiên bản kraken cùng thời (bản 2023).
  - **Test phân định 2 giả thuyết (đề xuất, chưa thực hiện do giới hạn thời gian phiên này):** cài `kraken` phiên bản cũ hơn (khoảng cuối 2023, cùng thời điểm publish model, ví dụ kraken 4.x/5.x) trong một venv riêng và chạy lại đúng ảnh này; nếu output trở nên hợp lý (đọc được thành câu có nghĩa) → H2 đúng (vấn đề là version mismatch, có thể khắc phục bằng ghim version); nếu vẫn ra ký tự lặp vô nghĩa → H1 đúng (vấn đề nằm ở bản thân model/pipeline).
  - **[Fact, không suy luận]** Dù nguyên nhân là gì, kết luận thực dụng cho báo cáo này không đổi: **với cấu hình cài đặt "ngay lập tức, theo đúng hướng dẫn hiện tại" (pip install kraken mới nhất), người dùng sẽ nhận được output không dùng được**, và đây chính xác là kịch bản mà bất kỳ ai làm theo README hôm nay sẽ gặp phải.
  - Quan sát bổ sung: mẫu lặp ký tự trên dòng thật (八, 一, 川) và trên câu tổng hợp ở Mục 3.2 (八, 十, 一) có phần trùng lặp (đều thiên về 八/一) — gợi ý (Suy luận, Low-Moderate confidence) đây có thể là các ký tự có xác suất tiên nghiệm cao trong tập huấn luyện mà mô hình "rơi về" khi không chắc chắn (một dạng mode collapse của decoder), củng cố thêm cho H2.

### 3.2 Chạy trên mẫu câu gia phả tự tạo (Hán cổ, theo đúng yêu cầu đề bài)

Theo yêu cầu của đề bài ("tạo một mẫu Hán tự ngắn nêu tên người, tên cha, và một chức quan"), chúng tôi tạo câu mẫu:

> **始祖諱文成官至知府娶阮氏生子一人諱德重**
> (Nghĩa: "Thủy tổ, tên húy Văn Thành, làm quan đến chức Tri phủ [知府], lấy vợ họ Nguyễn [阮氏], sinh một con trai, tên húy Đức Trọng" — có đủ: tên người, chức quan, quan hệ cha-con, giống cấu trúc câu gia phả thật.)

**[Fact — hạn chế thực nghiệm cần nêu rõ]** Vì môi trường sandbox không có font khắc mộc bản/viết tay cổ, câu trên được render bằng font **WenQuanYi Zen Hei** (font sans-serif hiện đại) thành ảnh PNG dạng cột dọc đơn, kích thước 148×1182px (tỉ lệ khung ~1:8, khác xa tỉ lệ ~9:16 mà `chat_seg.mlmodel` được huấn luyện/khuyến nghị). Đây **không phải một bài test công bằng** về năng lực lõi của mô hình (khác cả về phong cách nét chữ lẫn bố cục trang so với dữ liệu huấn luyện là bản in/viết tay 10th-20th century), mà là một **stress test nhanh** để xem hành vi khi input lệch xa phân phối huấn luyện — vốn cũng là tình huống thực tế có thể gặp khi áp dụng cho ảnh scan gia phả Việt Nam có phong cách khác với ngữ liệu Trung Quốc gốc.

**[Fact] Kết quả quan sát được:**
```
segmentation done in 81.1s, 6 lines
line 0: (rỗng)
line 1: (rỗng)
line 2: 八
line 3: (rỗng)
line 4: 人十一一一
line 5: (rỗng)
recognition done in 1.2s
```
- Segmentation (được huấn luyện để tách các dòng/cột trong bố cục trang sách nhiều cột) đã **chia sai** một cột văn bản duy nhất thành 6 "dòng" giả — dấu hiệu rõ ràng của domain mismatch về bố cục ảnh (ảnh của chúng tôi không có cấu trúc trang multi-column mà mô hình mong đợi).
- Recognition trả về: phần lớn dòng rỗng, và 2 dòng có ký tự nhưng là **ký tự sai hoàn toàn** so với câu gốc (mô hình "ảo giác" ra "八" (tám) và "人十一一一" (người-mười-một-một-một) — không khớp với bất kỳ ký tự nào trong câu mẫu 始祖諱文成官至知府娶阮氏生子一人諱德重).
- **Kết luận (High confidence, vì là quan sát trực tiếp):** trên input dạng font hiện đại/tỉ lệ khung lệch chuẩn, mô hình **không nhận dạng đúng bất kỳ ký tự nào** trong câu mẫu gia phả tự tạo. Đây là bằng chứng thực nghiệm cho thấy: (a) mô hình rất nhạy với phong cách phông chữ/bố cục đầu vào (kỳ vọng hợp lý cho một OCR engine dựa trên CNN+seq2seq huấn luyện trên phân phối hẹp), và (b) **không thể dùng "as-is" cho ảnh không phải bản in/viết tay cổ chính thống** — cố gắng áp dụng ngay cho ảnh gia phả Hán-Nôm Việt Nam (có phong cách khắc/viết khác, cỡ trang khác, và có xen chữ Nôm) nhiều khả năng sẽ gặp vấn đề tương tự trước khi fine-tune.
- **Suy luận/Inference (Moderate confidence):** kết quả này KHÔNG chứng minh mô hình vô dụng trên scan gia phả thật — chỉ chứng minh nó nhạy với domain gap. Cần thử nghiệm với ảnh scan gia phả Hán-Nôm thật (không phải font render tổng hợp) để đánh giá chính xác hơn; đó là bước tiếp theo hợp lý nếu quyết định theo hướng này.



---

## 4. Đánh giá khả năng tích hợp vào pipeline family-tree

### 4.1 License — **cảnh báo quan trọng**

**[Fact]** File `LICENCE` trong repo `CHAT_models` xác nhận: **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**.

**[Suy luận/Inference]** Đây là license **KHÔNG phù hợp** để tích hợp trực tiếp vào một sản phẩm/pipeline có khả năng dùng cho mục đích thương mại (kể cả một phần), vì CC BY-NC cấm sử dụng thương mại. Đối với một đồ án/luận văn nghiên cứu (non-commercial), việc dùng để **thử nghiệm, đánh giá, viết báo cáo khoa học** là hợp lệ (Attribution vẫn phải ghi công tác giả). Nhưng nếu `family-tree` sau này được thương mại hóa, đóng gói bán, hoặc tích hợp vào dịch vụ có thu phí, thì **không được dùng thẳng mô hình `chat_rec.mlmodel`/`chat_seg.mlmodel`** — cần: (a) xin phép tác giả, (b) tìm mô hình license MIT/Apache/BSD thay thế, hoặc (c) tự huấn luyện lại trên dữ liệu riêng.

So sánh nhanh license các ứng viên khác đã khảo sát:
- guwen-ner / GuwenBERT: **Apache-2.0** (tốt, không hạn chế thương mại) — nhưng không tải được (Mục 0).
- Jiayan: **MIT** (tốt) — nhưng không tải được (Mục 0).
- PersonRelationKnowledgeGraph: **không ghi rõ license** → rủi ro pháp lý, mặc định phải coi là "All rights reserved" nếu không có file LICENSE.

### 4.2 Tương thích định dạng input/output với pipeline hiện tại

**[Fact]** Đã đọc (chỉ đọc, không sửa) mã nguồn trong `/home/user/family-tree/nlp_family_extractor/` để kiểm chứng thay vì đoán: pipeline hiện tại **đã có sẵn** một bước OCR dùng **PaddleOCR (PP-OCRv6)** chạy cục bộ, xem `nlp_family_extractor/tools/ocr_paddleocr.py`, và một engine OCR Hán-Nôm khác gọi là "lab engine" (có vẻ là API bên ngoài, `tools/ocr_hannom_catalog.py`, `tools/draw_hannom_bbox.py`). Script `ocr_paddleocr.py` ghi kết quả ra các file `*-ocr-raw.json` và `*-boundingbox.json` mỗi trang, cho phép so sánh A/B giữa các engine OCR khác nhau. Điều này cho thấy nhóm dự án **đã chủ động thiết kế pipeline để cắm thêm một OCR engine mới và so sánh A/B** — kraken/CHAT_models có thể cắm vào theo đúng mô hình này (một script `ocr_kraken_chat.py` mới sinh ra `*-ocr-raw.json` cùng schema) mà không cần thay đổi kiến trúc.
- **Input:** CHAT_models nhận ảnh nhị phân (binarized đen/trắng) tỉ lệ khung ~9:16, đúng kiểu ảnh scan trang sách/gia phả đơn cột dạng dọc — cùng loại input (`.jpg/.png` trang scan) mà `ocr_paddleocr.py` đang dùng (`IMAGE_SUFFIXES` gồm jpg/png/tif/bmp/webp). **Tương thích tốt** về hình thức đầu vào.
- **Output:** kraken trả text thuần theo từng dòng (`record.prediction`) kèm tọa độ baseline — cần một adapter nhỏ để chuyển sang schema `*-ocr-raw.json` mà pipeline hiện dùng, và ghép các dòng theo đúng thứ tự đọc phải-sang-trái của cột dọc Hán văn (thứ tự dòng — `line_orders` — kraken có hỗ trợ nhưng bản mlmodel/README của CHAT_models chưa cung cấp reading-order model, xem "Reading order model" ghi "sẽ phát hành sau" trong README gốc — **[Fact]** tính năng này **chưa có** ở phiên bản đã tải). Effort tích hợp: **thấp-trung bình**.

### 4.3 Nhu cầu fine-tuning trên dữ liệu Hán-Nôm Việt Nam

**[Suy luận/Inference — chưa kiểm chứng bằng thực nghiệm định lượng, chỉ dựa trên domain gap đã biết]**
- Chữ Hán-Nôm Việt Nam dùng bảng chữ Hán phồn thể/hài thanh tương tự Hán văn cổ Trung Quốc nhưng có thêm **chữ Nôm** (chữ tự tạo, không có trong bộ mã Hán chuẩn, không nằm trong tập 16.000+ ký tự mà `chat_rec.mlmodel` được huấn luyện). Do đó:
  - Với các đoạn văn bản gia phả Việt Nam **thuần chữ Hán** (không có chữ Nôm), mô hình CHAT có khả năng nhận dạng được ở mức độ nhất định (chưa kiểm chứng bằng số liệu — xem Mục 3 để biết chất lượng OCR quan sát được trên văn bản Hán cổ Trung Quốc gốc).
  - Với các đoạn có **chữ Nôm xen kẽ** (rất phổ biến trong gia phả Việt Nam), mô hình gần như chắc chắn sẽ nhận dạng sai hoặc bỏ sót các ký tự chữ Nôm đó, vì chúng không nằm trong bộ ký tự mà mô hình được huấn luyện.
  - Phông chữ khắc mộc bản Việt Nam (thường ở các dòng họ vùng Bắc Bộ/Trung Bộ) có thể khác biệt về nét/phong cách so với ngữ liệu huấn luyện Trung Quốc (10th-20th century Chinese prints/manuscripts), gây thêm domain gap.
  - **Kết luận:** gần như chắc chắn cần fine-tuning thêm trên dữ liệu Hán-Nôm Việt Nam thật để dùng sản xuất; nhưng có thể dùng ngay ở dạng "as-is" như một **baseline/pretrained checkpoint để fine-tune tiếp**, nhanh hơn nhiều so với huấn luyện from-scratch — kraken hỗ trợ sẵn lệnh `ketos train -i chat_rec.mlmodel <data mới>` để fine-tune tiếp.

### 4.4 Effort tích hợp tổng thể: **Trung bình (Medium)**

| Hạng mục | Effort | Ghi chú |
|---|---|---|
| Cài đặt kraken vào pipeline `nlp_family_extractor/` (FastAPI) | Thấp | `pip install kraken`, không cần GPU |
| Vá lỗi tương thích API kraken/script (đã làm ở Mục 3) | Thấp | Đã có sẵn bản vá |
| Viết adapter input/output nối với bước Gemini hiện tại | Thấp-Trung bình | Cần thống nhất định dạng |
| Xử lý license CC BY-NC nếu sản phẩm hướng thương mại | Trung bình-Cao (rủi ro pháp lý, không phải effort kỹ thuật) | Cần quyết định của nhóm/giảng viên |
| Fine-tune trên dữ liệu Hán-Nôm thật (nếu cần độ chính xác cao) | Cao | Cần bộ dữ liệu ảnh + ground-truth transcription Hán-Nôm được gán nhãn, dùng `ketos train` của kraken |

---

## 5. Khuyến nghị

### 5.1 Tóm tắt bằng chứng làm nền cho khuyến nghị

| Bằng chứng | Loại | Kết luận rút ra |
|---|---|---|
| Cài đặt kraken qua pip thành công, không lỗi | Fact | Kỹ thuật cài đặt không phải rào cản |
| Chạy đúng README gốc → im lặng, không lỗi, không output (bug đường dẫn `test/` vs `demo/`) | Fact | Cần đọc kỹ code, không thể "chạy suông" theo README |
| Chạy đúng logic gốc (chỉ sửa đường dẫn) → crash `TypeError` do kraken 7.1.1 đổi API so với lúc repo viết (2023) | Fact | Repo có nợ kỹ thuật (thiếu ghim version); vẫn sửa được trong vài dòng code |
| Sau khi vá lỗi, chạy được, nhưng ~7-10 phút/trang trên CPU cho bước segmentation | Fact | Chi phí vận hành cao nếu không có GPU; ảnh hưởng tới khả năng dùng trong pipeline xử lý hàng loạt trang gia phả |
| Trên ảnh scan Hán văn cổ THẬT của chính repo (`houcunxiansheng.png`): 4/12 dòng đầu quan sát được đều là output rỗng hoặc lặp ký tự vô nghĩa (八, 一, 川...), không phải văn bản có nghĩa | Fact | Ngay cả trên đúng loại dữ liệu mà model được quảng cáo đạt >99% accuracy, cấu hình cài đặt mặc định hiện tại (kraken mới nhất) cho kết quả không dùng được — nhiều khả năng do version mismatch (xem H1/H2 ở Mục 3.1), nhưng dù nguyên nhân gì thì "chạy ngay theo README" không cho ra kết quả tốt |
| Trên câu Hán cổ tự tạo (font hiện đại, tỉ lệ khung khác chuẩn): tương tự — output rỗng/lặp ký tự vô nghĩa (八, 十, 一...) | Fact | Củng cố thêm: vấn đề nhất quán trên cả 2 loại input, không phải ngẫu nhiên |
| License CC BY-NC 4.0 | Fact | Cấm dùng thương mại; ổn cho mục đích nghiên cứu/luận văn |
| HuggingFace/ModelScope/Google Drive/Zenodo đều bị chặn trong sandbox | Fact | Loại các ứng viên NER cổ văn (GuwenBERT/guwen-ner, Jiayan) khỏi khả năng thử nghiệm ngay bây giờ — không phải vì chúng kém hơn, mà vì hạ tầng phân phối |
| Gia phả Việt Nam có xen chữ Nôm, không nằm trong bộ ký tự huấn luyện của CHAT_models | Suy luận | Cần fine-tune để dùng thật sự cho Hán-Nôm |

### 5.2 Khuyến nghị cụ thể

1. **Không dùng ngay CHAT_models cho sản xuất (production)** ở trạng thái hiện tại (cấu hình mặc định, kraken mới nhất). Lý do: (a) license CC BY-NC cấm thương mại, (b) output nhận dạng quan sát được trên cả ảnh scan thật của repo lẫn câu tự tạo đều không đọc được thành văn bản có nghĩa (Mục 3), (c) tốc độ CPU quá chậm cho xử lý hàng loạt (459.5s/trang chỉ riêng segmentation).
   **Mức độ tin cậy: High** (dựa trực tiếp trên license text, log chạy thực tế, và benchmark thời gian đã đo — không phải suy đoán).

2. **Bước tiếp theo bắt buộc TRƯỚC KHI quyết định dùng hay bỏ CHAT_models:** cài `kraken` phiên bản cũ hơn (cùng thời điểm publish model, ~cuối 2023) và chạy lại đúng 2 ảnh mẫu — đây là thực nghiệm rẻ (vài giờ công) và **phân định dứt khoát H1 vs H2** ở Mục 3.1. Nếu output trở nên đọc được (H2 đúng — vấn đề chỉ là version mismatch), CHAT_models trở thành **baseline/tài liệu tham khảo kỹ thuật có giá trị thật** cho nghiên cứu: so sánh A/B với PaddleOCR hiện có, và dùng `chat_rec.mlmodel` làm điểm khởi đầu để `ketos train` fine-tune tiếp trên dữ liệu Hán-Nôm (transfer learning, rẻ hơn train from-scratch). Nếu vẫn ra ký tự vô nghĩa (H1 đúng), nên loại CHAT_models khỏi shortlist và ưu tiên tài nguyên cho hướng NER (mục 3 dưới đây) hoặc tìm mlmodel/OCR khác.
   **Mức độ tin cậy: Moderate** — kraken hỗ trợ `ketos train` fine-tune từ checkpoint có sẵn (đã xác nhận qua `ketos --help`, là fact), nhưng giá trị thực tế của CHAT_models phụ thuộc vào kết quả thực nghiệm H1/H2 chưa thực hiện.

3. **Ưu tiên theo dõi/thử lại guwen-ner (GuwenBERT) và Jiayan khi hạ tầng cho phép** (ví dụ chạy trên máy có thể truy cập HuggingFace/Google Drive, hoặc dùng một mirror công ty được duyệt): về mặt lý thuyết, đây là các ứng viên **phù hợp hơn CHAT_models cho bài toán NER** (tên người, chức quan, quan hệ) mà đề bài thực sự cần ở downstream (trích xuất cấu trúc gia phả), trong khi CHAT_models chỉ giải quyết được bước OCR (đầu vào chuỗi ký tự thô), không phải NER/RE.
   **Mức độ tin cậy: Moderate** — dựa trên đọc tài liệu (Apache-2.0/MIT license tốt, kiến trúc phù hợp) nhưng **chưa chạy thử được** nên chưa có bằng chứng thực nghiệm trực tiếp — đây là giới hạn quan trọng cần nêu rõ với giảng viên.

4. **Không tìm thấy mô hình/dataset nào giải quyết trực tiếp** bài toán "gia phả Trung Quốc → cây quan hệ có cấu trúc" mà đề bài mô tả. Khuyến nghị báo cáo lại với giảng viên: khoảng trống này có thể là **cơ hội đóng góp học thuật** của luận văn (xây bộ NER/RE chuyên biệt cho gia phả Hán-Nôm), thay vì một thất bại tìm kiếm.
   **Mức độ tin cậy: High** (dựa trên tìm kiếm có hệ thống qua nhiều từ khóa tiếng Trung và tiếng Anh, không tìm thấy repo/dataset nào khớp trực tiếp).



---

## Phụ lục: Ghi chú tái lập (Reproducibility)

- Môi trường: sandbox Linux (kernel 6.18.44-fc-v37), Python 3.11.15, không có GPU khả dụng qua CLI kiểm tra (`torch.set_num_threads(1)` do chính script gốc chỉ định, chưa kiểm tra CUDA riêng vì mô hình đủ nhỏ để chạy CPU).
- Đường dẫn làm việc: `/tmp/claude-0/-home-user-family-tree/3842576e-30ae-58f6-89fa-3083c949683a/scratchpad/repo-hunt/`
  - `guwen-models/` — clone của https://github.com/Ethan-yt/guwen-models (chỉ để đọc README/license, không chạy được do Mục 0)
  - `CHAT_models/` — clone của https://github.com/colibrisson/CHAT_models (đã chạy thử)
    - `CHAT_models/demo/chat_models_demo_fixed.py` — bản đã vá lỗi tương thích API kraken 7.x (Mục 2), viết thêm bởi nhóm khảo sát, không phải file gốc của repo
    - `CHAT_models/test/synthetic_genealogy_sample.png` — ảnh câu Hán cổ tự tạo dùng ở Mục 3.2
    - `CHAT_models/real_sample_ocr_log.txt` — log đầy đủ của lần chạy trên ảnh mẫu thật (Mục 3.1)
    - `CHAT_models/synthetic_sample_ocr_log.txt` — log đầy đủ của lần chạy trên câu tự tạo (Mục 3.2)
  - `venv/` — virtualenv Python có cài `kraken==7.1.1`
- Lệnh tái lập:
  ```bash
  git clone https://github.com/colibrisson/CHAT_models.git
  cd CHAT_models
  python3 -m venv venv && source venv/bin/activate
  pip install kraken   # cài kraken 7.1.1 tại thời điểm khảo sát (25/09/2026)
  mkdir -p test && cp demo/*.png test/
  python demo/chat_models_demo_fixed.py   # bản đã vá lỗi API kraken 7.x, xem Mục 3
  ```
  Để phân định H1/H2 (Mục 3.1), bước tiếp theo đề xuất: `pip install "kraken<5"` (hoặc phiên bản kraken phát hành gần thời điểm CHAT_models công bố, cuối 2023) trong venv riêng rồi chạy lại đúng script gốc (không cần bản vá, vì API cũ tương thích với dict-style access).
- Không có file nào trong `/home/user/family-tree` bị chỉnh sửa. Không có lệnh `git` nào được chạy trong repo `family-tree`. Toàn bộ clone/cài đặt/chạy thử nằm trong thư mục scratchpad nêu trên.
