# Paddle xếp sai thứ tự cột & phân tích vote OCR

> Ngày: 03/10/2026 · Trạng thái: **đã sửa code + kiểm thử A/B/C, CHƯA áp vào dữ liệu thật**, chưa commit.
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

## 5. Việc tiếp theo — cần quyết định

| # | Việc | Ai | Tốn tiền | Cấp |
|---|---|---|---|---|
| 1 | **Dọn repo dữ liệu** `../hannom-bilingual-dataset`: đang có file sửa dở/không theo dõi (không phải của Claude: `pdf-phan-gia-cong-pha.json`, schema, README, `hxh-*`, `nguyen-khoa-*`, `nlv-1042`, `nom-308`…) — commit hoặc stash trước | Lâm | Không | — |
| 2 | **Giai đoạn D** — xem bằng mắt ~30 trang (2 trang/bộ) + 18 trang đổi nội dung + 10 trang τ thấp; thầy/Lâm duyệt 5–10 trang có chú thích nhỏ, phả đồ | Claude + Lâm/thầy | Không | L2 |
| 3 | Ghi vào dữ liệu: `python3 scripts/revote_paddle_order.py --write`, rồi import lên web | Claude | Không | L2 → L5 (production) |
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
