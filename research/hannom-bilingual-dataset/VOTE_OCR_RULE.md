# Vote OCR — Rule & Requirement (bản tích hợp, sẵn cho CI/CD)

> **Vai trò file:** gom lại thành **1 nguồn duy nhất** thuật toán vote đang nằm rải trong docstring `scripts/vote_ocr.py`, mục §"Vote OCR" của `CLAUDE.md`, và README — kèm requirement + đề xuất CI/CD. Không thay thế docstring gốc (vẫn là nơi có phân tích số liệu chi tiết nhất), file này là bản tóm tắt kỹ thuật để tích hợp/kiểm thử.
>
> **Ngày viết:** 2026-09-29 · **Đã kiểm tra lại (không chỉ đọc docstring):** đọc trực tiếp toàn bộ `scripts/vote_ocr.py` (541 dòng) — xem §5 "Phát hiện khi rà lại" cho 1 điểm docstring cũ chưa cập nhật.

---

## 1. Mục tiêu & phạm vi

Trộn (vote) kết quả OCR từ tối đa 5 engine (`kim_hannom_lab`, `paddle_v6`, `deepseek`, `google_vision`, `gemini`) cho 1 trang tài liệu Hán-Nôm, ra 1 `voted_text` đáng tin hơn bất kỳ engine đơn lẻ nào, **không tự đoán khi không có đa số thật**.

**Không thuộc phạm vi rule này:** gọi API OCR (adapter riêng, cần key), dịch nghĩa, OCR gốc — rule này chỉ xử lý N kết quả text **đã có sẵn**, thuần logic, không network.

---

## 2. Rule — thuật toán vote hiện tại

### 2.1. Đơn vị vote: CÂU/DÒNG, không phải ký tự

Dùng `rapidfuzz.distance.Levenshtein` (Minimum Edit Distance thật), **không** dùng `difflib.SequenceMatcher` — vì difflib bỏ qua mọi đoạn insert/delete/replace lệch độ dài (chỉ vote được phần cùng độ dài).

### 2.2. Chọn backbone — ĐỘNG theo độ giống nhau thật (`rank_by_similarity`)

Với mỗi engine có dữ liệu cho trang, tính độ giống trung bình (`_bag_of_lines_similarity`, bag-of-lines — không phụ thuộc thứ tự dòng) so với TẤT CẢ engine khác. Engine có độ giống trung bình **cao nhất** làm backbone (đọc "gần đa số" nhất). `DEFAULT_PRIORITY` chỉ còn dùng để (a) chọn engine nào được GỌI, (b) tie-break khi 2 engine có độ giống trung bình bằng hệt nhau (ví dụ đúng 2 engine: A~B luôn = B~A).

### 2.3. Giữ số phiếu LẺ ở cấp trang

Nếu số engine "khác backbone" (`other_names`) là số lẻ → tổng phiếu (backbone + others) sẽ chẵn → loại 1 engine (engine có độ giống trung bình **thấp nhất** trong `other_names`, theo `rank_by_similarity`, KHÔNG mất text — vẫn còn trong `engines{}`, chỉ không được bỏ phiếu) để tổng phiếu thành lẻ. Mục đích: giảm rủi ro 2 cụm ý kiến ngang phiếu không phân định được.

**Trường hợp biên đã biết (ghi rõ trong docstring gốc):** ở cấp TỪNG DÒNG, 1 engine có thể không có dòng khớp đủ ngưỡng (`SIM_NOTE_MIN=0.30`) cho vị trí đó → `n_total` của dòng đó vẫn có thể chẵn dù cấp trang đã ép lẻ. Đây là hạn chế đã được tác giả tự nhận, không phải lỗi ẩn.

### 2.4. Vote từng dòng (`vote_line`)

1. Với mỗi engine khác, `best_match()` tìm dòng khớp nhất trong toàn bộ dòng của nó so với dòng backbone (bằng Levenshtein similarity, không phải vị trí dòng tương ứng — chịu được lệch thứ tự nhẹ).
2. Gom {backbone + các dòng khớp nhất} thành cụm: 1 dòng vào cụm nếu giống dòng **đầu tiên** của cụm đó ≥ `SIM_MATCH=0.92`.
3. Cụm có nhiều engine hơn cụm chứa backbone → thắng, ghi đè (`line_majority_override`). Cụm ngang phiếu (kể cả 1-1) → **không ghi đè**, giữ backbone (`line_no_majority`/`line_confirmed_majority`). Chỉ 1 cụm duy nhất → `line_unanimous`.
4. Cụm thắng có >1 dòng khác nhau chút → chọn dòng "trung tâm" (medoid — tổng khoảng cách Levenshtein tới các dòng còn lại trong cụm nhỏ nhất).

### 2.5. Fallback vote theo vị trí ký tự (`vote_line_positional`)

Chỉ chạy khi `vote_line()` không rõ ràng (`line_no_majority` hoặc `line_confirmed_majority`). Căn từng engine khác vào đúng vị trí ký tự của backbone bằng `Levenshtein.editops()` (star alignment lấy backbone làm tâm), vote riêng từng vị trí/khe hở — **chỉ tự sửa khi ≥3 engine đồng thuận tại đúng 1 vị trí** (mặc định `min_majority=3`). Mục đích: ghép được chỗ đúng của nhiều engine khác nhau khi mỗi engine chỉ sai 1 chỗ khác nhau trong cùng 1 dòng (vote CÂU không làm được việc này).

### 2.6. Nguyên tắc an toàn xuyên suốt

- Không bao giờ ghi đè khi 2 cụm/2 giá trị ngang phiếu (1-1, 2-2...).
- Cấp câu: không có ngưỡng số tối thiểu cố định (chỉ cần "nhiều hơn cụm backbone"); cấp vị trí ký tự (fallback): bắt buộc ≥3.
- Mọi bất đồng không đủ đa số → ghi vào `uncertain_spans`/`uncertain_positions` cho người soát, **không đoán**.

---

## 3. Requirement (dependency)

**Third-party packages thực tế được import trong `scripts/*.py` + `scripts/ocr_adapters/*.py`** (rà bằng grep import trực tiếp trên toàn bộ code, không suy đoán từ README):

| Package | Dùng ở đâu | Ghi chú |
|---|---|---|
| `rapidfuzz` | `vote_ocr.py` (`rapidfuzz.distance.Levenshtein`) | **Bắt buộc** cho rule vote — lõi thuật toán §2 |
| `python-dotenv` | các adapter (`from dotenv import ...`), `dich_nghia.py`, `phien_am.py` | Đọc `.env` (API key OCR/dịch — không cần cho riêng logic vote offline) |
| `requests` | adapter gọi API OCR (paddle_v6, deepseek, google_vision, gemini, kim_hannom_lab) | Không cần nếu chỉ test/CI logic vote với input cố định (§4) |
| `jsonschema` | `scripts/add_new_source.py`, lệnh validate trong README/CLAUDE.md | Cho validate schema record, không phải vote |

**Chuẩn Python:** 3.10+ (dùng `from __future__ import annotations`, kiểu `dict[str, Any]`, `list[...]`).

**Chưa có `requirements.txt` ở root cho các script chính** (`scripts/*.py`) — chỉ có 3 file `requirements.txt` con trong `TOOL_Gemini_API/`, `TOOL_ChatGPT_API/`, `sentence-alignment-main/` (không liên quan trực tiếp `vote_ocr.py`). Đã tạo `requirements.txt` ở root kèm file này (xem §4).

---

## 4. CI/CD — đề xuất tích hợp

**Fact quan trọng cho CI:** `vote_line()`, `vote_line_positional()`, `rank_by_similarity()`, `best_match()`, `vote_from_results()` là **pure function** — nhận text/dict có sẵn, không gọi network/API, không đọc file ngoài (`vote_from_results` không đụng `load_catalog()`/adapter). → **Test được 100% offline, deterministic, an toàn chạy trong CI** không cần API key OCR. Chỉ `vote_page()` (gọi `ADAPTERS[name].load(...)`) và `main()` (đọc `books_catalog.json` từ `../family-tree`) mới cần môi trường thật/API — **không đưa 2 hàm này vào CI**.

### 4.1. Đề xuất cụ thể

1. **Thêm `requirements.txt`** ở root (đã tạo cùng lúc với file này) — CI cài `pip install -r requirements.txt` trước khi test.
2. **Viết test cố định** (`scripts/test_vote_ocr.py` hoặc `tests/test_vote_ocr.py`, chưa tồn tại — cần làm) với input giả lập nhiều engine (dict tên → text), assert:
   - 1-1 bất đồng không bao giờ override (`line_no_majority`).
   - ≥2 engine đồng ý khác backbone (backbone chỉ có 1) → override đúng (`line_majority_override`).
   - `rank_by_similarity` chọn đúng engine giống nhau nhất làm backbone trên input đã biết trước đáp án.
   - Số phiếu lẻ ở cấp trang được đảm bảo (`vote_from_results` với 2 hoặc 4 "other engines" giả).
3. **Thêm stage vào `Jenkinsfile` hiện có** (đang chỉ có `Checkout OK` → `Build Dashboard Image` → `Deploy`, không test gì) — chèn stage mới TRƯỚC `Build Dashboard Image`:
   ```groovy
   stage('Unit Test Vote Rule') {
       steps {
           sh 'pip install -r requirements.txt'
           sh 'python -m pytest scripts/test_vote_ocr.py -v'
       }
   }
   ```
4. **Không** đưa `main()`/`vote_page()` (cần `books_catalog.json` + API key) vào CI — CI chỉ test logic vote thuần, không test OCR thật.

### 4.2. Việc chưa làm (checklist)

- [ ] Viết `scripts/test_vote_ocr.py` với ≥5 test case theo §4.1 mục 2.
- [ ] Thêm stage `Unit Test Vote Rule` vào `Jenkinsfile` (mẫu ở §4.1 mục 3).
- [ ] Chạy thử CI 1 lần, xác nhận pass/fail thật (chưa làm ở phiên này).

---

## 5. Phát hiện khi rà lại rule (2026-09-29) — không chỉ đọc docstring, đã đối chiếu với code chạy thật

**Fact:** docstring đầu file, mục (4) và mục "Vì sao số tool tham gia vote phải luôn LẺ" (dòng ~17-22 và ~91-123 của `vote_ocr.py`), mô tả việc loại engine khi cần giữ lẻ là **"chọn theo `priority.index()`, tức engine đứng CUỐI trong `DEFAULT_PRIORITY`"** — đọc như thể thứ tự loại bỏ cố định theo danh sách ưu tiên tĩnh.

**Fact (đối chiếu trực tiếp code `vote_from_results()`, dòng 397-412):** thứ tự loại bỏ thực tế lấy từ `ranked, avg_sim = rank_by_similarity(results, priority)` rồi `other_names = ranked[1:]`, loại `other_names[-1]` — **`rank_by_similarity` sắp xếp theo độ giống nhau trung bình ĐO ĐƯỢC trên chính trang đó** (`priority` chỉ dùng để tie-break khi giống nhau bằng hệt). Đây đúng là thiết kế đã đổi ở phần "PHÂN TÍCH" của `rank_by_similarity()` (tự ghi rõ: "không xếp theo thứ tự ưu tiên, mà xếp theo độ giống nhau của các tools", XÁC NHẬN 2026-09-15).

**Kết luận (độ tin cậy cao — đọc trực tiếp 2 đoạn code, không suy đoán):** đoạn docstring mục (4) và mục "Vì sao... LẺ" ở đầu file **chưa được cập nhật** sau khi đổi sang `rank_by_similarity` — mô tả hành vi loại engine theo `DEFAULT_PRIORITY` tĩnh trong khi code thật dùng độ giống nhau động, `priority` chỉ là tie-break. Không ảnh hưởng kết quả vote (code chạy đúng theo `rank_by_similarity`), nhưng **có thể khiến người đọc docstring hiểu sai** engine nào bị loại khi có nhiều engine cùng chạy. Đề xuất: sửa 2 đoạn docstring đó để khớp hành vi thật (việc nhỏ, chưa làm trong phiên này — cần xác nhận trước khi sửa vì đây là file thuộc repo dữ liệu, không phải phạm vi "web" đang làm tuần này).

**Chưa kiểm chứng (do ngoài phạm vi phiên này):** giá trị ngưỡng `SIM_MATCH=0.92` và `SIM_NOTE_MIN=0.30` — hardcode, chưa thấy phân tích độ nhạy (sensitivity analysis) nào trong repo đo xem đổi ngưỡng có làm thay đổi đáng kể tỉ lệ override/uncertain không. Không phải lỗi, chỉ là giới hạn đánh giá hiện tại.

---

## 6. Ràng buộc — giữ nguyên nguyên tắc tách 2 repo (`CLAUDE.md` rule #6)

`CLAUDE.md` của repo này quy định: *"Không sửa/xoá gì trong `family-tree` từ repo này — 2 repo độc lập, chỉ đọc tham chiếu."* Vì vậy, **"tích hợp thành 1" trong file này = 1 FILE RULE DUY NHẤT** (đã làm ở §2), **không phải gộp 2 git repo**. Nếu sau này muốn pipeline chính (`nlp_family_extractor` trong `family-tree`) dùng lại đúng thuật toán vote này: copy có ghi rõ nguồn (`hannom-bilingual-dataset/scripts/vote_ocr.py`, commit hash cụ thể) vào `family-tree`, hoặc đóng gói thành 1 package Python riêng cả 2 repo cùng cài — **không** symlink hoặc import chéo trực tiếp giữa 2 repo (phá vỡ ranh giới rule #6).
