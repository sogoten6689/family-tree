# Paddle xếp sai thứ tự cột & phân tích vote OCR

> Ngày: 03/10/2026 · Trạng thái: **đã sửa code + kiểm thử A/B/C/D, CHƯA áp vào dữ liệu thật**.
> **Chặn ghi dữ liệu:** giai đoạn D tìm ra lỗi vote dòng ngắn (§4, mục 2b ở §5).
> Không gọi API trả phí, không ghi vào `data/` hay production.

## 1. Tóm tắt 1 phút

```
Ảnh gia phả → 5 engine OCR → VOTE → chữ Hán → phiên âm → dịch nghĩa → web
                  ↑
         Paddle xếp sai thứ tự cột (ĐÃ SỬA trong code, CHƯA áp vào dữ liệu)
```

1. **Phần vote trên web** nằm ở: Gia phả → Chi tiết → tab **Trang** → kéo xuống khung
   "Xem chi tiết các bước xử lý" → bấm **2. Vote (hợp nhất)**.
2. **"80% dòng chưa chắc chắn" phóng đại vấn đề**: tính theo dòng, lệch 1 chữ là cả dòng
   bị tính. Tính theo CHỮ chỉ khoảng **18%**.
3. **Chưa biết engine nào ĐÚNG** — không có bộ trang chép chuẩn (gold). Mọi số hiện có
   chỉ đo các engine giống nhau tới đâu.
4. **Lỗi thật đã tìm ra:** PaddleOCR xếp dòng theo mép trên khung (kiểu chữ ngang), làm
   xáo trộn cột chữ Hán dọc (đúng là phải → trái). **628 trang** có `voted_text` sai thứ
   tự cột vì lấy Paddle làm engine nền. Nội dung chữ không sai, chỉ sai thứ tự.
5. Đã sửa code + kiểm thử kỹ trên **bản sao** dữ liệu. Chưa áp vào dữ liệu thật.

## 2. Số liệu chính (fact — đo trực tiếp)

Dữ liệu: 1.259 trang có kết quả nhiều engine (local = production).

| Đo | Kết quả |
|---|---|
| uncertain_rate trung vị: theo dòng / theo chữ | 0,80 / **0,18** |
| Dòng chưa chắc chắn có engine chỉ lệch ≤1 chữ | 44% |
| Dòng lệch do engine đọc khác chữ thật (dòng ≥4 chữ) | ~90% — giả thuyết "do chia dòng" **bị bác bỏ** |
| Dòng chưa chắc chắn ngắn < 4 chữ | 38% |
| Độ đồng thuận (tập chữ chung) cao nhất | Paddle ~ Kim Hán Nôm 0,75 · Paddle ~ DeepSeek 0,71 |
| Thấp nhất | Gemini ~ Google Vision 0,51 |

Paddle — thứ tự cột (Kendall τ so với Kim Hán Nôm / DeepSeek):

| | Paddle gốc | Chỉ sắp theo x | **Thuật toán mới** |
|---|---|---|---|
| 927 trang văn bản (τ trung vị / TB) | −0,51 / −0,44 | +1,00 / 0,90 | **+1,00 / 0,92** |
| 46 trang phả đồ (世系圖) | +0,33 | +0,41 | **+0,88** |
| Bộ thấp nhất | — | — | `pdf-1000-mai` 0,956 |

Bằng chứng gốc: ảnh `nom-1255` tr.1 — cột phải nhất là `皇朝維新五年歲次辛亥六月初六日`;
Kim, DeepSeek, Google Vision, Gemini đều đọc nó đầu tiên, Paddle đọc thứ 5 (toạ độ khung
trong `001-paddleocr.json` xếp theo y).

## 3. Đã làm (code, chưa commit)

Thư mục `research/hannom-bilingual-dataset/scripts/`:

| File | Vai trò |
|---|---|
| `ocr_adapters/paddle_v6.py` | Đọc `{stem}-paddleocr.json`, sắp **cột phải → trái, trong cột trên → dưới**; chú thích chữ nhỏ 2 hàng đọc phải → trái; không có JSON thì đọc `.txt` như cũ |
| `test_paddle_column_order.py` | 16 test (A1–A7), có test toạ độ thật `nom-1255`, `nom-1158` |
| `revote_paddle_order.py` | Vote lại OFFLINE từ text engine đã lưu (không gọi API). Mặc định chỉ đo; `--write` chỉ sửa 6 trường vote L1, giữ định dạng file |
| `check_revote_invariants.py` | Chạy `--write` 2 lần trên **bản sao** dữ liệu, kiểm tra bất biến |
| `eval_paddle_order.py` | Đo Kendall τ thứ tự dòng |
| `analyze_vote_alignment.py` | Phân tích độ đồng thuận / chia dòng / theo chữ |
| `render_paddle_order.py` | Vẽ khung + số thứ tự mới lên ảnh để soát bằng mắt (giai đoạn D) |

**Không** dùng `run.py`/`vote_page`: adapter DeepSeek, Gemini, Google Vision **gọi API thật** (tốn tiền).

## 4. Kết quả kiểm thử

- **A — unit test:** 16/16 đạt. Kiểm tra đột biến (tắt phần sửa A1) → 2 test trượt
  đúng như mong đợi. Tìm ra và sửa 2 lỗi: chú thích chữ nhỏ bị đọc trái trước phải;
  kết quả phụ thuộc thứ tự đầu vào khi khung trùng toạ độ.
- **B — bất biến (bản sao dữ liệu):** tất cả ĐẠT.
  - Paddle giữ đúng tập dòng 1.059/1.059; engine khác không đổi; engine nền không đổi.
  - 1.043 trang đổi L1: **1.025 chỉ đổi thứ tự**, 18 đổi nội dung 1–2 dòng (xem §6).
  - Ghi lần 2 không đổi gì; ngoài 6 trường vote không trường nào đổi (phiên âm, dịch,
    pairs giữ nguyên); record không đổi giữ nguyên từng byte; schema không thêm lỗi.
- **C — τ:** đạt tiêu chí (trung vị ≥ 0,9; không bộ nào < 0,7).

Lưu ý: τ đo **khớp với engine khác**, không phải **đúng** — trang có chú thích nhỏ thì
chính Kim cũng chỉ sắp theo x. Cần giai đoạn D (đối chiếu ảnh).

### Giai đoạn D — đối chiếu ảnh (03/10/2026, Claude xem, CHƯA có thầy/Lâm duyệt)

Công cụ: `scripts/render_paddle_order.py` vẽ khung Paddle + số thứ tự mới lên ảnh (ảnh ra
ngoài repo). Trong lúc làm đã sửa 2 lỗi của chính công cụ vẽ (gắn số theo chữ → 2 khung
trùng chữ bị nhầm số; nhãn đè nhau) — thêm `column_order_indices` + 1 test (17/17 đạt).

| Nhóm | Số trang | Kết quả |
|---|---|---|
| Ngẫu nhiên 2 trang/bộ | 30 | **Văn bản liền mạch: 23/24 đúng**, 1 lỗi nhỏ (`nom-563` tr.42: chú thích đọc trước cột chính vì chỉ chồng ~10px theo x); 1 trang chú thích quá dày chưa xác minh (`nom-854` tr.38). 5 trang bố cục không tuyến tính (bảng, lưới, cây) — xem dưới |
| Chú thích chữ nhỏ 2 hàng | 8 | Đúng (phải → trái, chú thích sau cột chính). Xác nhận bằng chữ `nom-1158` tr.24: `…時中 [耳上社 耳陀村] 阮維曉 [安朗縣 安朗社] 等中進士…` |
| τ thấp nhất | 10 | **10/10 là phả đồ cây / sơ đồ rời** — không có trang văn bản nào sai |
| Phả đồ có 世系圖 | 4 | Cùng dạng cây |
| Đổi nội dung | 18 | **Mới TỆ HƠN cũ ở ~11/18** (xem dưới) |

**Hạn chế đã biết — bố cục không tuyến tính** (`pdf-1000-mai`, `pdf-1005-tran`, `nom-208`,
`nom-557`): phả đồ cây (tổ → con → cháu) bị đọc theo cột dọc xuyên qua nhiều đời (vd
`pdf-1000-mai` tr.102: tổ `春義公` đọc thứ 14); bảng lưới bị đọc theo cột thay vì theo hàng
(`pdf-1000-mai` tr.57); Paddle còn gộp tên nhiều nhánh vào 1 khung ngang và nhận con dấu đỏ
thư viện thành khung chữ rác. Với các trang này KHÔNG có thứ tự tuyến tính đúng — cần quy
ước (thầy) hoặc tách cấu trúc cây; vote không bị ảnh hưởng vì vote ghép dòng không theo thứ tự.

**CHẶN `--write` — vote dòng ngắn ghép nhầm tên người khác.** Ở 18 trang đổi nội dung, đối
chiếu ảnh: hầu hết cả 2 tên đều CÓ trên trang (`有忠`/`有德`, `君璽`/`玉璽`, `士鶴`/`士德`,
`士應`/`士道`, `邕公`/`真公`, `仲載`/`仲篆`) — dòng tên 2–4 chữ bị ghép với tên NGƯỜI KHÁC
cùng trang; đổi thứ tự Paddle chỉ đổi "ai bị nhầm". Tệ nhất: `nom-207` tr.8 — 7 tên khác nhau
(`能智`, `能孝`, `能肇`, `能童`, `能淨`, `能澤`, `能學`) thành 7 lần `能體`.

| Đánh giá (theo ảnh) | Trang |
|---|---|
| Mới tốt hơn | `pdf-1000-mai` 090 (`煲肉氏` → `娶周氏`) |
| Tương đương / chữ dị thể | `nom-1255` 002, 004, 005 (賜/𧶽, 礼/禮, 茲/兹 — vốn không tái lập được), `nom-207` 012, `pdf-1005-tran` 135 |
| Mới tệ hơn | `nom-1158` 055, `nom-207` 008, 010, `nom-208` 010, `nom-557` 001, `pdf-1000-mai` 076, 084, 085, `pdf-1005-tran` 151, 162, 165, 224 |

Lỗi này CÓ SẴN trong vote cũ (bản cũ cũng nhầm, chỉ khác nạn nhân) nên sửa thứ tự Paddle
không gây ra nó — nhưng `--write` hiện tại sẽ làm 18 trang này tệ hơn.

## 5. Việc tiếp theo — cần quyết định

| # | Việc | Ai | Tốn tiền | Cấp |
|---|---|---|---|---|
| 1 | **Dọn repo dữ liệu** `../hannom-bilingual-dataset`: đang có file sửa dở/không theo dõi (không phải của Claude: `pdf-phan-gia-cong-pha.json`, schema, README, `hxh-*`, `nguyen-khoa-*`, `nlv-1042`, `nom-308`…) — commit hoặc stash trước | Lâm | Không | — |
| 2 | ~~Giai đoạn D~~ — Claude đã xem 70 trang (§4). Còn: thầy/Lâm duyệt 5–10 trang (chú thích nhỏ, phả đồ) + chốt quy ước thứ tự cho phả đồ cây/bảng | Lâm/thầy | Không | — |
| 2b | **Sửa vote dòng ngắn** trước khi ghi. Phương án (chọn 1): (a) phá hoà theo VỊ TRÍ dòng gần nhất — giờ Paddle đúng thứ tự nên vị trí có nghĩa; (b) không cho ghi đè dòng < 3–4 chữ, chỉ đánh dấu chưa chắc chắn; (c) `--write` chỉ đổi thứ tự, giữ nội dung cũ ở trang đổi nội dung. Đo lại 18 trang | Claude | Không | L2 (sửa `vote_ocr.py` = đổi thuật toán, cần duyệt thiết kế) |
| 3 | Ghi vào dữ liệu: `python3 scripts/revote_paddle_order.py --write`, rồi import lên web — **chỉ sau 2b** | Claude | Không | L2 → L5 (production) |
| 4 | ~158 trang phiên âm có thể lộn thứ tự (ước lượng, tin cậy vừa) — kiểm tra 20 trang rồi chọn: sắp lại (miễn phí) hay làm lại (Kim/Gemini) | Claude | Có thể | L2 / R3 |
| 5 | Bộ ~30 trang chép chuẩn → đo CER từng engine → quyết định bỏ engine tốn tiền | Lâm/thầy chép, Claude đo | Không | L2 |

Thứ tự khuyên: **1 → 2 → 3**, rồi 4, 5.

Quay lại làm tiếp, gõ: *"tiếp tục việc Paddle: dọn repo dữ liệu xong rồi, làm giai đoạn D, L2"*.

## 6. Vấn đề phụ đã biết (chưa sửa)

- **Dòng ngắn khớp hoà:** `best_match` chọn dòng ĐỨNG TRƯỚC khi nhiều dòng giống ngang
  nhau → đổi thứ tự Paddle làm đổi kết quả vote ở 15 trang (dòng tên 2–4 chữ), có chỗ tốt
  hơn (`煲肉氏` → `娶周氏`), có chỗ kém (`能智`, `能孝` → `能體`, `能體`). Cần sửa riêng.
- 3 trang `nom-1255` (002, 004, 005) không tái lập được vote cũ (khác chữ dị thể 禮/礼,
  兹/茲) — có từ trước, chưa rõ nguyên nhân.
- **Schema lệch:** 1.282 lỗi có sẵn, tất cả là `align_method: "llm_draft"` không có trong
  enum của schema bên family-tree (bản schema trong repo dữ liệu đang sửa dở).
- Card "Chi phí Gemini" trên web không đếm lần gọi qua khe engine văn bản.
- Tab "OCR / phiên âm" trên trang chi tiết còn ghi "sẽ bổ sung" — thực tế đã có ở tab Trang.

## 7. Môi trường

Các script cần `rapidfuzz` + `jsonschema`: dùng `python3` (pyenv 3.10). `nlp_family_extractor/.venv`
thiếu `jsonschema`. Chạy từ `research/hannom-bilingual-dataset/`.

## 8. Thử vote mới theo TỪNG CHỮ trên `nom-147` (phương án A, 03/10/2026)

Quy ước (Lâm chốt): **≥3/4 engine đồng ý → tự sửa; 2/4 → chỉ đề xuất; hoà → giữ nền, cần soát.**
Thêm/bớt chữ luôn chỉ đề xuất (lựa chọn thận trọng của Claude: engine đọc lệch thứ tự 1 đoạn
trông như "thiếu chữ"). Code thử nghiệm, KHÔNG ghi vào record:
`scripts/vote_char_majority.py` (+ 8 test), `scripts/compare_char_vote.py`.

Cách làm: mỗi engine → chuỗi chữ Hán CẢ TRANG theo thứ tự đọc (Paddle đã sắp theo cột), căn
từng engine vào nền theo chữ, cả 4 engine bỏ phiếu (không loại engine nào). Không ghép dòng →
hết lỗi tên ngắn ghép nhầm người khác.

| Đo (58 trang, 13.842 chữ) | Kết quả |
|---|---|
| 4/4 đồng ý | 4.890 (35%) |
| Nền giữ, ≥3/4 | 5.263 (38%) |
| Nền giữ, chỉ 2 phiếu | 2.003 (14,5%) |
| Hoà | 1.119 (8,1%) |
| **Đề xuất (2/4)** | 479 (3,5%) |
| **Tự sửa (≥3/4)** | **88** (0,6%) |
| Chữ cần soát (< 3/4 đồng ý) | 26% — vote cũ hiện "89%" theo dòng |

Đối chiếu ảnh (Claude xem, chưa có người duyệt):
- **Tự sửa: 20/20 mẫu ngẫu nhiên đúng với ảnh** (vd `王`→`三`, `于`→`子` 老子, `位`→`伍` 伍拾柒歲,
  `米`→`朱`, `祀`→`犯` 侵犯; 2 ca dị thể `來`→`来`, `為`→`爲` khớp nét chữ trên ảnh).
- **Đề xuất 2/4: 6/10 đúng, 1/10 nền đúng (`青編`), 3/10 không phân định** → giữ 2/4 ở mức đề xuất là đúng.

Còn chưa làm: chuẩn hoá chữ dị thể trước khi đếm phiếu; đưa vào `vote_ocr.py`/record; giao
diện theo từng chữ (mô phỏng đã duyệt hướng); đo trên bộ chép chuẩn (chưa có).

## 9. Vote theo từng chữ trên CẢ 19 bộ nhiều engine (03/10/2026)

`compare_char_vote.py` cho từng bộ (offline, không ghi record). 273.971 chữ: **tự sửa 1.204**,
đề xuất 26.499, 4/4 (hoặc mọi engine) đồng ý 108.800 (40%). Cần soát toàn bộ: 39% — bị kéo
lên bởi 4 bộ (xem dưới); các bộ chữ rõ, đủ 4–5 engine: 9–26%.

| Nhóm | Bộ | Kết quả |
|---|---|---|
| 4–5 engine, chữ rõ | `nom-1158`, `nom-1255`, `nom-147`, `nom-207`, `nom-208`, `nom-563`, `nom-833`, `nom-865`, `nom-854`, `nom-1256` | tự sửa 12–323/bộ, cần soát 9–37% |
| 3 engine | `pdf-1001-la`, `pdf-1005-tran`, `pdf-phan-gia-cong-pha`, `hxh-129` | **0 tự sửa** (đa số tối đa 2/3 < 3) — chỉ đề xuất |
| 2 engine | `nom-429`, `nom-855` | không vote được |
| Bất thường | `pdf-phan-gia-cong-pha` 15.558 đề xuất (49%): 3 engine đọc rất khác nhau (giống nhau 40–60%) — OCR khó, không phải lỗi thuật toán. `nom-557` cần soát 69%: DeepSeek trả 1.524 chữ nội dung KHÁC hẳn (trùng 3–5%) ở tr.15 — đọc nhầm/bịa; Paddle–Kim cùng chữ nhưng lệch thứ tự → căn chữ hỏng |

Đối chiếu ảnh 30 mẫu tự sửa ở các bộ khác (Claude xem): **25 đúng, 2 chữ dị thể (塲/場, 內/内),
3 không phân định, 0 sai rõ**. Nhóm 5 engine (sửa ở 3/5): 11 đúng, 2 dị thể, 2 không phân định;
nhóm 4 engine: 14 đúng, 1 không phân định. Cộng `nom-147`: **45/50 đúng, 0 sai rõ**.

Cần quyết định / làm thêm:
1. Ngưỡng tự sửa hiện là **≥3 phiếu tuyệt đối** → với 5 engine là 3/5 (60%). Giữ, hay đổi thành ≥75%?
2. Bộ 3 engine không bao giờ tự sửa — chấp nhận (chỉ đề xuất) hay cho 2/3 tự sửa?
3. Lọc engine "lạc đề" mỗi trang (trùng < ~20% chữ với mọi engine khác → không cho bỏ phiếu).
4. Đánh dấu trang "không căn được" (nhiều chữ chung nhưng lệch thứ tự) thay vì sinh đề xuất giả.
5. Bảng quy đổi chữ dị thể trước khi đếm phiếu (thầy duyệt).

## 10. Sàng engine trước khi vote (mục 3–4 của §9, 03/10/2026)

Lâm chốt: giữ ngưỡng **≥3 phiếu** (5 engine: 3/5 tự sửa); bộ 3 engine **chỉ đề xuất**.
Thêm vào `vote_char_majority.py` (13 test), ngưỡng chọn theo phân bố đo trên 19 bộ:
- **Lạc đề**: < 30% chữ của engine có ở engine khác, dài > 2× trung vị engine khác, ≥ 20 chữ →
  không bỏ phiếu, và bị loại TRƯỚC khi chọn nền. Bắt được 35 trang, chủ yếu DeepSeek đọc lặp
  (`nom-557` tr.49: 52.232 chữ; tr.54: 26.108; `pdf-phan-gia-cong-pha` tr.78: 14.862).
- **Lệch thứ tự** so với nền: tập chữ ≥ 30% nhưng giống theo thứ tự thấp hơn ≥ 0,3 → không bỏ phiếu.
- Còn < 2 engine bỏ phiếu → trang `unaligned`, cần soát toàn trang.

Kết quả 19 bộ: tự sửa 1.204 → 1.169; **đề xuất 26.499 → 10.977**; cần soát 39% → 33%.

**Đính chính §9:** `pdf-phan-gia-cong-pha` có 15.558 đề xuất KHÔNG phải chủ yếu do "3 engine
đọc khác nhau" — 14.529 (93%) đến từ 1 trang (tr.78) nơi bản DeepSeek đọc lặp được chọn làm
NỀN. Sau sàng: 957 đề xuất, cần soát 80% → 32%.

**Lỗi trong dữ liệu hiện có (vote cũ):** `pdf-phan-gia-cong-pha` tr.78 — `voted_text` = 14.862
chữ rác của DeepSeek (vote cũ chọn nó làm nền). Bộ này đã import lên web (scan #20) — chưa
kiểm tra trực tiếp trên production. 34 trang khác có engine lạc đề được bỏ phiếu (không làm nền).

Đối chiếu 8 ca "lệch thứ tự": 6 đúng (vd Google Vision đọc trang trái trước, `nom-147` tr.15/40);
2 loại quá tay (`nom-208` tr.59: Kim, Gemini khớp đầu trang, chỉ lệch đoạn sau) → mất phiếu tốt,
không sửa sai. Cải tiến sau: căn theo từng đoạn thay vì cả trang.
