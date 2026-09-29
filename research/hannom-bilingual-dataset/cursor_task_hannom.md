# Nhiệm vụ: vote lại L1 OCR cho toàn bộ dataset bằng thuật toán mới (KHÔNG gọi API, miễn phí)

## Bối cảnh

Repo: `/Users/forestlam/Documents/projects/cao_hoc/source/hannom-bilingual-dataset`

Ngày 14–15/9 đã đổi thuật toán vote OCR trong `scripts/vote_ocr.py`: từ vote
**ký tự** (difflib.SequenceMatcher) sang vote **câu/dòng** bằng Levenshtein MED
thật (`rapidfuzz`), backbone/engine bị loại khi cần giữ số phiếu lẻ chọn theo
độ giống nhau thật giữa các engine (không còn priority cố định), cộng thêm
fallback vote theo vị trí ký tự khi vote câu không đủ đa số rõ ràng
(`vote_line_positional`). Đã áp dụng thử và xác nhận đúng trên `nom-1255`
(6/6 trang, commit `89c6efa`).

**Kiểm tra 21/9: 17 tài liệu còn lại (1.250/1.275 trang, ~98% dataset) vẫn
đang dùng kết quả vote CŨ** (`vote_method` kiểu `..._backbone_char_vote_N_other`,
không phải `..._backbone_line_vote_levenshtein_N_other`). Việc bạn cần làm: áp
dụng lại thuật toán mới cho 17 tài liệu này.

## QUAN TRỌNG NHẤT — đây là việc MIỄN PHÍ, không gọi API

Text thô của cả 5 engine (kim_hannom_lab, paddle_v6, deepseek, google_vision,
gemini) đã lưu sẵn trong từng trang (`l1_ocr.engines{}.<engine>.text`) từ lần
OCR trước. **Chỉ cần vote lại trên text đã có, không OCR lại.**

`scripts/run.py` đã có sẵn đúng flag cho việc này:

```bash
python3 scripts/run.py <doc_id> --all --from-record
```

**BẮT BUỘC phải có cả `--all` VÀ `--from-record` trên MỌI lệnh.**
- Thiếu `--from-record` → script rơi vào nhánh gọi API THẬT (deepseek/google_vision/
  gemini) cho từng trang — tốn tiền/quota thật, KHÔNG được chạy nhầm.
- Thiếu `--all` → chỉ vote lại 3 trang đầu, bỏ sót phần còn lại.

Không sửa `scripts/vote_ocr.py`, `scripts/run.py`, hay bất kỳ file trong
`scripts/ocr_adapters/` — các file này đã ổn định, chỉ dùng nguyên trạng.

## Chạy đầu tiên: `git pull`

```bash
cd /Users/forestlam/Documents/projects/cao_hoc/source/hannom-bilingual-dataset
git pull
```

## Chia 5 nhóm chạy song song (5 Cursor instance, mỗi instance 1 nhóm)

Chia theo tổng số trang cho cân, mỗi nhóm ~230–265 trang. **Chỉ làm đúng
danh sách của nhóm mình, không đụng tài liệu nhóm khác** (tránh commit đè
nhau — cả 5 nhóm sửa data/track1_hannom_only/ khác file nhau nên an toàn nếu
đúng danh sách).

| Nhóm | doc_id (theo thứ tự chạy) | Tổng trang |
|---|---|---|
| **A** | `pdf-1005-tran` (233), `nom-865` (21) | 254 |
| **B** | `pdf-1000-mai` (131), `nom-147` (58), `nom-563` (44), `nom-429` (9) | 242 |
| **C** | `pdf-1001-la` (118), `nom-833` (60), `nom-557` (55) | 233 |
| **D** | `nom-855` (100), `nom-208` (79), `nom-84` (47), `nom-1256` (30) | 256 |
| **E** | `pdf-phan-gia-cong-pha` (85), `nom-207` (85), `nom-1158` (55), `nom-854` (40) | 265 |

Với MỖI tài liệu trong nhóm, chạy đúng 1 lệnh:

```bash
python3 scripts/run.py <doc_id> --all --from-record
```

Lệnh này tự làm hết: vote lại từng trang từ cache → gộp vào
`data/track1_hannom_only/<doc_id>.json` → in `uncertain_rate` trung bình.
Không cần script phiên âm/dịch nghĩa — L2/L3 đã xong từ trước và **không bị
đụng tới** (script chỉ ghi đè `l1_ocr`, giữ nguyên `l2_phien_am`/`l3_dich_nghia`/
`pairs`).

## Lưu ý khi đọc kết quả — không phải lỗi

- Một số tài liệu (vd. `nom-429`) chỉ có 2/5 engine chạy được lúc OCR ban đầu.
  Theo luật giữ số phiếu lẻ, 2 engine sẽ tự rút xuống còn 1 (backbone một
  mình) — `uncertain_rate` ra 0% và `vote_method` có dạng
  `..._only_no_other_engine_excl_<engine>_for_odd`. Đây là hành vi ĐÚNG theo
  thiết kế, không phải bug.
- `uncertain_rate` sau khi vote lại **không so sánh trực tiếp được** với giá
  trị cũ (đổi mẫu số từ số ký tự sang số dòng) — đừng hoảng nếu số này nhảy
  vọt so với trước.

## Sau khi xong MỖI tài liệu — validate rồi mới sang tài liệu tiếp theo

Chú ý: `pdf-phan-gia-cong-pha` (nhóm E) nằm ở `data/track2_bilingual/`, KHÔNG
phải `track1_hannom_only/` — dùng glob thay vì gõ path cứng, như dưới đây:

```bash
python3 -c "
import json, jsonschema, glob
schema = json.load(open('schema/bilingual_record.schema.json', encoding='utf-8'))
v = jsonschema.Draft7Validator(schema)
path = glob.glob('data/*/<doc_id>.json')[0]
d = json.load(open(path, encoding='utf-8'))
errs = list(v.iter_errors(d))
print(path, '— schema errors:', len(errs))
for e in errs: print(list(e.path), e.message)
"
```

Phải ra `schema errors: 0` mới commit. Nếu có lỗi — DỪNG lại, không tự sửa
schema hay tự đoán, báo lại nguyên văn lỗi.

## Sau khi xong CẢ NHÓM (tất cả doc_id trong danh sách của mình)

```bash
# 1. Cập nhật dashboard
python3 scripts/build_dashboard.py

# 2. Pull trước khi push (4 nhóm khác cũng đang commit song song)
git pull

# 3. Nếu dashboard/index.html hoặc dashboard/status.json báo conflict khi pull:
#    không cần merge tay — chạy lại `python3 scripts/build_dashboard.py` rồi add lại,
#    vì 2 file này chỉ là dữ liệu SINH RA tự động.

# 4. Commit + push — liệt kê đủ doc_id đã làm trong 1 commit cho cả nhóm
# (dùng git add -u để bắt đúng mọi file JSON đã sửa, không cần gõ tay từng path/track)
git add -u data/track1_hannom_only/ data/track2_bilingual/ dashboard/index.html dashboard/status.json
git commit -m "Vote lại L1 theo thuật toán câu/Levenshtein cho <danh sách doc_id nhóm mình>

Co-Authored-By: Cursor <noreply@cursor.com>"
git push
```

## KHÔNG làm

- **Không** bỏ `--from-record` khỏi lệnh chạy — sẽ tốn tiền/quota thật.
- **Không** sửa `scripts/vote_ocr.py`, `scripts/run.py`, `scripts/ocr_adapters/*`.
- **Không** đụng tài liệu ngoài danh sách nhóm mình.
- **Không** tự phân loại/gán mã định danh (`quy_mo`, `hinh_thuc`, `ho`,
  `dia_danh`, `nien_dai`, `ma_dinh_danh`) — không liên quan việc này.
- **Không** đụng `l2_phien_am`/`l3_dich_nghia`/`pairs` — việc này chỉ vote lại L1.
- **Không** commit `.env` hay `secrets/`.

## Thứ tự đề xuất trong mỗi nhóm

Chạy đúng thứ tự đã liệt kê trong cột "doc_id" của bảng trên (tài liệu lớn
nhất trong nhóm chạy trước — nếu có lỗi/bất thường sẽ lộ ra sớm trên tài liệu
lớn, đỡ mất công phát hiện muộn ở cuối).
