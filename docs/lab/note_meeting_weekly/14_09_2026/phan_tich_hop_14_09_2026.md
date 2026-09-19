# Phân tích ghi chú họp 14/9/2026

> Nguồn: [`14_09_2026.md`](./14_09_2026.md) — ghi chép thô, câu ngắn/rời rạc theo đúng phong cách note họp trực tiếp (so `31_08_2026.md`). File này tách riêng phần diễn giải + đối chiếu hiện trạng code + câu hỏi mở, không sửa lại ý gốc.
>
> Quy ước: **Nguyên văn** = chép đúng lời thầy · **Diễn giải** = suy luận của tôi (có thể sai, cần thầy xác nhận) · **Đối chiếu hiện trạng** = fact từ code/repo hiện có · **Câu hỏi** = cần thầy trả lời trước khi làm.

---

## 1. "Fake API, dùng UI tự gọi cho Gemini"

**Nguyên văn:** *fake api, dùng ui tự gọi cho gemini*

**Diễn giải:** Thay vì gọi Gemini qua API trả phí (đang bị giới hạn hạn mức/billing — xem sự cố hết credit tuần trước), dựng một lớp "giả API" bằng cách điều khiển giao diện web Gemini (AI Studio / Gemini app) tự động — có thể qua browser automation — để lấy kết quả dịch nghĩa mà không tốn quota API chính thức.

**Đối chiếu hiện trạng:** Hiện `L3 dịch nghĩa` đang gọi Gemini qua API key thật (`GOOGLE_API_KEY`, project "Egitech" link tới billing "Firebase Payment" đã sửa tuần trước). Chưa có code nào tự động hoá UI Gemini trong repo.

**Câu hỏi cần hỏi thầy:**
- "Fake API" nghĩa là dựng wrapper giả lập REST API nhưng backend thật sự là tự động hoá trình duyệt gọi Gemini UI (để né giới hạn/phí API), đúng không?
- Có rủi ro vi phạm điều khoản dịch vụ Google khi tự động hoá UI không — thầy có yêu cầu ràng buộc gì (chỉ dùng nội bộ, không production) không?

---

## 2. Sửa vote OCR — bắt buộc vote theo câu

**Nguyên văn:** *sửa vote, bắt buộc vote từ câu, nếu dùng câu để nói câu*

**Đối chiếu hiện trạng (fact, từ `hannom-bilingual-dataset/scripts/vote_ocr.py`):** Thuật toán vote hiện tại **đã** làm theo 2 bước: (1) khớp dòng-với-dòng bằng `best_match` (tìm dòng backbone khớp nhất ở engine khác), rồi (2) vote **ở mức ký tự** trong nội bộ dòng đã khớp, dùng `difflib.SequenceMatcher` (thuật toán Ratcliff/Obershelp) để lấy opcode `equal/replace/insert/delete`. Chỉ đoạn `equal` và `replace` **cùng độ dài** mới được vote ký tự; đoạn `replace` lệch độ dài, `insert`, `delete` bị bỏ qua vote, chỉ ghi vào `structural_diffs` (theo docstring: *"không thể ánh xạ theo vị trí ký tự một cách tin cậy"*).

**Diễn giải:** "Bắt buộc vote từ câu" có thể là: (a) khẳng định lại bước khớp-dòng-trước (đã có), yêu cầu làm chặt/đúng hơn; hoặc (b) yêu cầu đổi đơn vị vote từ ký tự sang **câu/dòng** làm đơn vị chính — tức nếu 2 dòng khác nhau đủ nhiều thì vote chọn nguyên cả dòng của 1 engine, không chẻ nhỏ ký tự. Cụm "nếu dùng câu để nói câu" đọc như một nguyên tắc nhất quán đơn vị: đã chọn đơn vị câu thì phải xử lý/so sánh nhất quán ở cấp câu, không trộn lẫn cấp ký tự giữa chừng.

**Câu hỏi cần hỏi thầy:**
- Vote nên ở cấp **câu/dòng** (chọn nguyên dòng của engine thắng) hay giữ vote **ký tự** như hiện tại nhưng sửa lại cách khớp dòng cho chặt hơn?
- Nếu là (a) — khớp dòng chặt hơn — thì mục 3 (Levenshtein) chính là câu trả lời kỹ thuật cho việc này.

---

## 3. Dùng Levenshtein (MED) để nối/căn hàng trước khi so sánh

**Nguyên văn:** *trước khi so sánh, dùng Levenshtein (MED) nối 2 thằng lại giống hàng, số lượng ký tự, thiếu insert, remove, replace*

**Đối chiếu hiện trạng (fact):** `vote_ocr.py` hiện dùng `difflib.SequenceMatcher`, **không phải** Levenshtein/Minimum Edit Distance thật. Hai thuật toán khác nhau: SequenceMatcher (Ratcliff/Obershelp) tìm khối khớp dài nhất theo kiểu heuristic, không tối ưu số phép sửa; Levenshtein/MED tính **số phép edit tối thiểu** (insert/remove/replace) để biến chuỗi A thành chuỗi B, và có thể dùng ma trận quy hoạch động để **căn hàng (alignment)** từng ký tự — kể cả khi 2 chuỗi lệch độ dài. Đây chính xác là chỗ thuật toán hiện tại đang **bỏ cuộc** (`structural_diffs`, không vote) khi gặp `insert`/`delete`/`replace` lệch độ dài.

**Diễn giải:** Thầy chỉ đúng chỗ hổng thật của code: thay `difflib.SequenceMatcher` bằng Levenshtein MED alignment (vd. thư viện `python-Levenshtein`, `rapidfuzz`, hoặc tự cài Needleman-Wunsch/Wagner-Fischer) để 2 chuỗi OCR được "nối lại giống hàng" (align) ký-tự-đối-ký-tự trước khi vote — kể cả những đoạn lệch độ dài hiện đang bị bỏ qua.

**Việc cần làm (khá rõ ràng, ít cần hỏi thêm):**
- Thay bước alignment trong `vote_ocr.py` bằng MED/Levenshtein alignment (giữ nguyên phần vote theo đa số phía sau).
- Mục tiêu: xoá/giảm `structural_diffs` (hiện đang né vote) bằng cách vote được cả đoạn insert/delete/replace lệch độ dài.

**Câu hỏi cần hỏi thầy:**
- Có yêu cầu dùng đúng thư viện/công cụ nào không, hay tự chọn miễn đúng thuật toán Levenshtein MED?

---

## 4. Dịch nghĩa dùng Gemini

**Nguyên văn:** *Dịch nghĩa dùng gemini*

**Đối chiếu hiện trạng:** Đúng như đang làm — L3 dịch nghĩa hiện dùng Gemini (`gemini-3.5-flash-lite` sau khi đổi model tuần trước). Đây là xác nhận lại hướng đã chọn, không phải thay đổi mới.

---

## 5. Tìm mô hình có sẵn cho gia phả Hán (Trung Quốc) — "đi săn" bằng Claude

**Nguyên văn:** *Tìm mô hình có sẵn của gia phả của Hán (Trung Quốc) — Cố gắng đi săn, dùng claude đi săn, rồi vào chạy thử*

**Diễn giải:** Tìm các mô hình/dataset/công cụ NLP đã có sẵn, huấn luyện trên dữ liệu gia phả chữ Hán của Trung Quốc (ví dụ mô hình NER/RE cho văn bản cổ Hán, dataset gia phả Trung Quốc công khai) — dùng Claude (qua Claude Code hoặc web) để tìm kiếm/khảo sát ("đi săn"), sau đó tải về chạy thử trên dữ liệu của mình để đánh giá có dùng lại/transfer được không.

**Việc cần làm:** Đây là task tìm kiếm — tôi (Claude) có thể trực tiếp tra cứu khi được yêu cầu (papers, HuggingFace, GitHub) cho mô hình/dataset gia phả Hán Trung Quốc. Sẽ làm khi có xác nhận phạm vi.

**Câu hỏi cần hỏi thầy:**
- Ưu tiên loại mô hình nào: OCR chữ Hán cổ, NER (trích xuất tên người/quan hệ), hay mô hình sinh cây gia phả từ text?
- Có nguồn/từ khoá cụ thể thầy đã biết (tên nhóm nghiên cứu, tên dataset) để tìm nhanh hơn không?

---

## 6. "Gia phả xoay quanh nó, và gần với mình để kế thừa nó, tự động hình [thành cây]"

**Nguyên văn:** *Gia phả xoay quanh nó, và gần với mình để kế thừa nó, tự động hình*

**Diễn giải (độ tin cậy thấp — câu gốc bị cắt/thiếu chữ):** Có thể ý là: chọn mô hình gia phả Hán (Trung Quốc, mục 5) làm tâm tham chiếu, ưu tiên nguồn dữ liệu/ngữ cảnh gần với gia phả Việt (cùng gốc Hán Nôm, cấu trúc tương tự) để **kế thừa** (transfer learning / dùng lại kiến trúc) từ mô hình đó, hướng tới tự động **hình thành cây** gia phả (dựng sơ đồ quan hệ tự động) từ text đã dịch.

**Câu hỏi cần hỏi thầy:** Câu này trong ghi chép bị thiếu chữ cuối ("tự động hình" — hình gì?) — nhờ thầy nói lại rõ ý đầy đủ, tôi ghi chưa đủ kịp trong lúc họp.

---

## 7. Ưu tiên tìm gia phả lâu năm — gốc sẽ có Hán Nôm

**Nguyên văn:** *tìm gia phả lâu năm, thì gốc sẽ có hán nôm*

**Diễn giải:** Khi tìm nguồn dữ liệu mới, ưu tiên gia phả có niên đại càng lâu/càng cổ, vì bản gốc của chúng nhiều khả năng được chép bằng Hán Nôm (khác với gia phả soạn gần đây thường chỉ có Quốc ngữ) — đúng hướng bổ sung Track 1/Track 2 (cần bản Hán), tránh lặp lại tình huống Track 3 (mất bản Hán, chỉ còn Quốc ngữ).

**Đối chiếu hiện trạng:** Khớp với quan sát đã ghi trong báo cáo tuần trước — 3 tài liệu Track 3 hiện tại đều không còn bản Hán. Đây là tiêu chí chọn nguồn rõ ràng, không cần hỏi lại.

---

## 8. Gia phả Nguyễn Phước — thầy có quen

**Nguyên văn:** *gia phả nguyễn phước (thầy có quen)*

**Diễn giải:** Thầy có mối quan hệ cá nhân/quen biết có thể giúp tiếp cận gia phả dòng họ Nguyễn Phước (họ của hoàng tộc nhà Nguyễn — dòng lớn, nhiều khả năng có bản Hán Nôm gốc lâu đời, khớp tiêu chí mục 7). Đây là một nguồn dữ liệu mới tiềm năng qua giới thiệu của thầy, chưa có trong 25 tài liệu đã catalogue.

**Câu hỏi cần hỏi thầy:** Thầy có thể giới thiệu/kết nối liên hệ này khi nào — có cần tôi chuẩn bị gì trước (thư ngỏ, mô tả dự án) không?

---

## 9. Hướng tới bài toán song song — dịch và song song

**Nguyên văn:** *Hướng tới bài toán song song, dịch và song song*

**Diễn giải (2 khả năng, chưa rõ khả năng nào đúng):**
- (a) "Song song" = **dữ liệu song ngữ** (bilingual parallel corpus Hán–Việt) — tức trọng tâm nghiên cứu nên xoay quanh việc dịch + xây kho ngữ liệu song song, đúng hướng `pairs[]`/Bertalign đang làm.
- (b) "Song song" = **xử lý song song** (parallelization) — liên quan đến việc tăng tốc pipeline OCR/dịch bằng chạy song song, chủ đề đã khảo sát ở phiên làm việc tuần trước ("parallelization speed test investigation").

**Câu hỏi cần hỏi thầy:** "Song song" ở đây là dữ liệu song ngữ hay xử lý đa luồng/song song? Hay cả hai — dịch song ngữ **và** làm cho pipeline chạy song song?

---

## Tổng hợp câu hỏi cần thầy trả lời

1. "Fake API" cho Gemini — có đúng là browser-automation thay UI cho API call để né quota/phí không? Có ràng buộc gì cần tuân thủ?
2. Vote OCR nên đổi đơn vị sang cấp câu/dòng, hay giữ cấp ký tự nhưng sửa cách căn hàng (câu trả lời kỹ thuật ở mục 3 có đủ không)?
3. Levenshtein MED — có yêu cầu thư viện/công cụ cụ thể không?
4. Ưu tiên loại mô hình gia phả Hán Trung Quốc nào (OCR / NER / dựng cây)? Có nguồn gợi ý sẵn không?
5. Câu "gia phả xoay quanh nó... tự động hình" — nhờ thầy nói lại đầy đủ, ghi chép bị thiếu.
6. Liên hệ gia phả Nguyễn Phước — khi nào có thể kết nối, cần chuẩn bị gì trước?
7. "Bài toán song song" — dữ liệu song ngữ, xử lý đa luồng, hay cả hai?

## Việc có thể làm ngay, không cần chờ thầy trả lời

- Mục 3 (Levenshtein/MED thay SequenceMatcher trong `vote_ocr.py`) — đủ rõ về mặt kỹ thuật, có thể triển khai song song với việc chờ thầy xác nhận mục 2.
- Mục 5 (tìm mô hình gia phả Hán Trung Quốc) — có thể bắt đầu khảo sát sơ bộ (papers/HuggingFace/GitHub) trong lúc chờ thầy gợi ý phạm vi ưu tiên.
- Mục 7 (ưu tiên nguồn gia phả lâu năm) — áp dụng ngay làm tiêu chí khi tìm thêm dữ liệu, không có gì mơ hồ.

---

## Cập nhật 15/9 — đã triển khai mục 2+3, phát sinh thêm 2 việc mới

**Mục 2+3 (vote câu bằng Levenshtein MED) — ĐÃ LÀM.** `vote_ocr.py` đổi hẳn
sang vote ở cấp CÂU/DÒNG (không còn ghép ký tự Frankenstein từ nhiều engine),
dùng `rapidfuzz.distance.Levenshtein` (MED thật) để gom các dòng "cùng câu"
thành cụm rồi chọn nguyên dòng của cụm thắng — xem chi tiết thuật toán +
verify offline trên dữ liệu thật (`runs/*.vote.json`, không tốn API) trong
docstring `hannom-bilingual-dataset/scripts/vote_ocr.py` và README repo đó.

**Việc mới 1 — "luôn chạy đủ lẻ tool để vote".** Tôi (Lâm) yêu cầu thêm:
`vote_page()` giờ luôn đảm bảo tổng số engine tham gia vote là số LẺ — nếu 1
engine lỗi/hết quota khiến số engine thành công bị chẵn, tự động loại bớt 1
(vẫn giữ text thô để tham khảo, chỉ không cho nó bỏ phiếu). Lý do: số phiếu
chẵn có rủi ro 2 cụm bằng nhau không cụm nào áp đảo, giống rủi ro "2 engine
hoà 1-1" ở quy mô lớn hơn — xem docstring `vote_ocr.py`.

**Việc mới 2 — thầy quan sát "Gemini đúng nhiều hơn".** Tôi báo lại quan sát
này của thầy. Nó **mâu thuẫn trực tiếp** với số liệu win-rate tôi tính trước
đó (Gemini chỉ thắng vote 4,7%/526 trang, thấp gần nhất trong 5 engine). Sau
khi điều tra kỹ:
- Phát hiện lỗ hổng phương pháp: win-rate cũ đo "khớp với đa số", không đo
  "đúng thật" — nếu 2 engine cùng mắc lỗi giống nhau, chúng vẫn thắng vote dù
  sai, còn Gemini đọc đúng hơn nhưng khác biệt vẫn bị tính thua.
- Phát hiện thêm: Gemini có trang tách dòng khác hẳn 4 engine kia (vd.
  `nom-208/076`: Gemini 17 dòng ngắn vs kim_hannom_lab 11 dòng dài hơn), khiến
  so khớp dòng cũ đánh giá sai.
- **Đã đổi thiết kế:** bỏ hẳn priority cố định (`kim_hannom_lab > paddle_v6 >
  deepseek > google_vision > gemini`) khi chọn backbone/engine bị loại, thay
  bằng xếp hạng ĐỘNG theo độ giống nhau thật giữa các engine mỗi trang
  (`rank_by_similarity()`, bag-of-lines Levenshtein — không phụ thuộc thứ tự
  dòng, tự sửa 1 lỗi tương tự phát hiện được ở paddle_v6 trong lúc kiểm
  chứng). Kết quả 529 trang thật: paddle_v6 giống đa số nhất ở 62% trang
  (không phải kim_hannom_lab như priority cũ luôn giả định); Gemini/Google
  Vision vẫn thấp nhất TRUNG BÌNH nhưng có trang cụ thể (vd. `nom-1255/001`)
  Gemini gần ngang paddle_v6 — tức quan sát của thầy và số liệu của tôi **không
  mâu thuẫn**, chỉ khác góc nhìn (trung bình toàn bộ vs trang cụ thể thầy xem).
  Bảng đầy đủ: README `hannom-bilingual-dataset`.

**Chưa giải quyết — mục 1 (Fake API) phát sinh rủi ro mới.** Tôi (Lâm) đã tự
thêm `hannom-bilingual-dataset/Fake_ChatGPT_API/` — dùng `undetected-
chromedriver` + các cấu hình "stealth" để tự động hoá đăng nhập/gõ prompt vào
giao diện web ChatGPT thay cho gọi API trả phí. Claude đã từ chối tích hợp
việc này vào pipeline vì đây là kỹ thuật né bot-detection thật sự, nhiều khả
năng vi phạm Điều khoản dịch vụ OpenAI — cần thầy xác nhận hướng xử lý (dùng
API trả phí hợp lệ thay thế, hay có phương án khác) trước khi làm tiếp mục 1.
