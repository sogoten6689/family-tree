# Hán Nôm Bilingual Dataset — "done data"

> **Cập nhật 2026-09-29:** mã nguồn (folder này) đã gộp vào `family-tree`
> (`family-tree/research/hannom-bilingual-dataset/`) — theo yêu cầu "tích hợp
> thành 1 repo duy nhất". Repo Git riêng `hannom-bilingual-dataset` **vẫn tồn
> tại** nhưng từ giờ chỉ còn giữ `data/` và `runs/` (nặng, cố ý không đưa vào
> family-tree). Chạy script ở đây vẫn đọc/ghi đúng chỗ cũ nhờ `DATA_REPO_ROOT`
> trong `scripts/_repo_paths.py` (mặc định: thư mục sibling `../hannom-
> bilingual-dataset` cạnh `family-tree`, override bằng biến môi trường
> `HANNOM_DATA_ROOT` nếu bạn clone repo dữ liệu ở chỗ khác).

Trước đây là repo Git độc lập chứa dữ liệu gia phả Hán Nôm **đã xử lý xong**, mỗi tài liệu là
1 file JSON có cấu trúc, phân loại và gắn tên rõ ràng. Tách bạch khỏi repo làm việc
[`family-tree`](../family-tree) (nơi giữ ảnh gốc, PDF, kịch bản OCR, phân tích tay) —
repo này **không copy ảnh/PDF gốc**, mỗi record chỉ tham chiếu đường dẫn tương đối
trong `family-tree` (trường `nguon.duong_dan_goc`), tránh 2 nguồn sự thật.

## 3 nơi cần nhớ — không hơn

| # | Thư mục | Là gì | Có commit không |
|---|---|---|---|
| 1 | `family-tree/data/00_raw/hannom_inbox/<doc_id>/` | Ảnh gốc — nơi **BỎ ẢNH VÀO** khi có tài liệu mới | Có (bên repo family-tree) |
| 2 | `runs/<doc_id>/` | Kết quả OCR+vote **thô** từng trang (`*.vote.json`) — cache tạm | **Không** (gitignore, xoá/chạy lại thoải mái) |
| 3 | `data/track1\|2\|3_*/​<doc_id>.json` | **Kết quả CUỐI** — record đã gộp, đây mới là "sản phẩm" của repo | Có |

Và chỉ 2 lệnh cần nhớ:

```bash
python3 scripts/add_new_source.py --doc-id <id> --title-vn "..."   # 1 lần — đăng ký tài liệu mới
python3 scripts/run.py <id>                                        # chạy lại bao nhiêu lần cũng được
```

## Rule 1 (mục tiêu của repo)

> Có Hán–Việt song ngữ, đã phân loại gắn tên, JSON có cấu trúc cho dữ liệu song ngữ.

Không phải tài liệu nào cũng thoả được ngay — xem 3 track bên dưới.

## 3 track dữ liệu nguồn

| Track | Ý nghĩa | Số file | Thư mục |
|---|---|---|---|
| **1** ⭐ | Toàn Hán Nôm, **chưa có** dịch nghĩa thật — cần chạy OCR-vote → phiên âm → dịch nghĩa | 17 | `data/track1_hannom_only/` |
| **2** ⭐ | **Đã có sẵn** cả Hán và Việt (song ngữ) — chỉ cần chuẩn hoá/ghép cặp vào đúng schema | 3 | `data/track2_bilingual/` |
| **3** | Văn bản gia phả **tiếng Việt thuần** — bản Hán đã mất hoặc chưa từng có | 4 | `data/track3_viet_only/` |

⭐ = **ưu tiên chính của repo** (Track 1 & 2 — đây mới là dữ liệu song ngữ thật sự phục vụ Rule 1).
Track 3 **ưu tiên thấp hơn hẳn** — dễ tìm, không cần OCR, chỉ giữ lại để dùng làm
tài liệu tham khảo câu văn/văn phong (vai trò gần giống corpus VGP Quốc ngữ hiện
đại bên `family-tree`), không phải mục tiêu chính cần đầu tư công sức xử lý.

`manifest/classification.json` là nguồn sự thật cho việc phân track (sinh bởi
`scripts/build_manifest.py` từ `family-tree/data/00_raw/hannom/books_catalog.json`,
kèm 4 tài liệu bị loại khỏi phạm vi vì không phải bản thân 1 bộ phả — xem trường
`loai_khoi_pham_vi` trong manifest).

Corpus Quốc ngữ hiện đại (VGP, 2.152 cây từ vietnamgiapha.com) **không** đưa vào
repo này — giữ vai trò tham khảo văn phong riêng ở `family-tree`.

Track 3 có `co_ban_han: false` — **không** được coi là song ngữ dù có text Việt.

## `doc_id` vs `ma_dinh_danh` — 2 mã khác nhau, đừng nhầm

- **`doc_id`** = key kỹ thuật nội bộ (`nom-84`, `gpc-dang-1928`, `le-01`...) —
  ổn định, có **TRƯỚC KHI** đọc/phân loại tài liệu, dùng làm tên file/tra cứu
  trong toàn bộ script. Sinh bằng `scripts/suggest_doc_id.py`.
- **`ma_dinh_danh`** = mã định danh khoa học (F-code) đã chốt với thầy 06–07/09
  (nguồn: `family-tree/docs/lab/note_meeting_weekly/31_08_2026/huong_dan_gia_pha_han_nom.md`
  + `31_08_2026.md`) — chỉ tính được **SAU KHI** đã xác nhận đủ 5 thành phần
  qua đọc trực tiếp: `quy_mo`, `hinh_thuc`, `ho`, `dia_danh`, `nien_dai` (năm
  soạn **bản gốc**, không phải năm ấn bản/dịch lại), cộng thêm 1 số ID tăng
  dần theo thứ tự nhập catalogue. `null` cho tới khi đủ điều kiện — **không suy
  đoán ID hay địa danh khi chưa chắc**.

Cấu trúc: `F-{chữ A-V ứng Quy_Mô×Hình_Thức}-{Mã Họ 2 chữ}-{Địa Danh cấp thấp
nhất, không dấu không cách}-{ID 3 chữ số}-{Năm soạn gốc}`. Ví dụ đã chốt:
`F-B-PN-GiaThien-001-1930` (Phan gia công phả). Bảng tra cứu đầy đủ (20 chữ
A-V, 12 mã Họ) nằm trong `scripts/ma_dinh_danh_tables.py`, dùng qua
`build_ma_dinh_danh(quy_mo, hinh_thuc, ho, dia_danh_ngan, id_seq, nam_goc)`.

**Hiện trạng 2026-09-09**: 3/28 tài liệu đã có `ma_dinh_danh` (3 record Track 2
đủ thông tin). ID=001 (`pdf-phan-gia-cong-pha`) đã chốt trực tiếp với thầy;
ID=002/003 (`gpc-dang-1928`, `docx-nguyen-van`) là **suy luận** của AI (xếp
theo năm soạn gốc sớm→muộn) — ghi rõ trong `ghi_chu` từng record, cần thầy xác
nhận lại thứ tự thật khi có dịp. 25 tài liệu còn lại chưa đủ điều kiện tính mã
(thiếu 1+ trong 5 thành phần) — xem cột `ma_dinh_danh: null`.

## Schema

`schema/bilingual_record.schema.json` (JSON Schema draft-07). Khung 4 lớp
L0 (ảnh gốc) → L1 (OCR Hán, có `engines{}` cho tối đa 5 tool) → L2 (phiên âm
Hán-Việt) → L3 (dịch nghĩa Quốc ngữ hiện đại) kế thừa từ
`family-tree/docs/planning/labeling_and_hannom_ocr_plan.md` §3.1, cộng thêm mảng
`pairs` ghép câu Hán↔Việt tường minh cho mục tiêu song ngữ.

Validate:

```bash
pip install jsonschema
python3 -c "
import json, jsonschema, glob
schema = json.load(open('schema/bilingual_record.schema.json', encoding='utf-8'))
v = jsonschema.Draft7Validator(schema)
for f in glob.glob('data/*/*.json'):
    d = json.load(open(f, encoding='utf-8'))
    for e in v.iter_errors(d):
        print(f, list(e.path), e.message)
"
```

## Phân tích: vì sao OCR cần vote + mixing

**Cập nhật 2026-09-14 — đổi đơn vị vote từ KÝ TỰ sang CÂU/DÒNG, dùng Levenshtein
MED thật** (`pip install rapidfuzz`), theo yêu cầu họp 14/09 ("bắt buộc vote từ
câu"; xem [`note_meeting_weekly/14_09_2026/`](../family-tree/docs/lab/note_meeting_weekly/14_09_2026/)).
Lý do đổi: vote ký tự bản cũ (dưới đây) dùng `difflib.SequenceMatcher`
(Ratcliff/Obershelp) — **không phải** Levenshtein/Minimum-Edit-Distance thật —
nên mọi đoạn `insert`/`delete`/`replace` LỆCH ĐỘ DÀI đều bị bỏ qua, không vote
được, chỉ ghi vào `structural_diffs` để đọc tay. Bản mới dùng
`rapidfuzz.distance.Levenshtein` để gom các dòng OCR "cùng 1 câu" (dù lệch độ
dài) thành cụm rồi vote nguyên dòng thắng cuộc — xoá hẳn giới hạn đó. Đã kiểm
chứng offline (không gọi API mới, dùng lại cache thật `runs/nom-208/076.vote.json`,
5/5 engine): thuật toán mới cho `line_majority_override` đúng như kỳ vọng khi
≥2 engine đồng ý khác backbone, `line_no_majority` khi không bên nào áp đảo.
**Lưu ý:** `uncertain_rate` đổi mẫu số (số dòng, không phải số ký tự) — không
so trực tiếp giá trị cũ/mới cùng 1 trang. Chi tiết thuật toán đầy đủ: docstring
đầu `scripts/vote_ocr.py`.

**Cập nhật 2026-09-15 — luôn đảm bảo số tool tham gia vote là số LẺ.** 5 tool
vẫn luôn được gọi hết cho mỗi trang; nếu 1 tool lỗi/hết quota khiến số tool
THÀNH CÔNG bị chẵn (vd. 4/5), `vote_page()` tự loại 1 engine khỏi vòng vote
(giữ nguyên text thô trong `engines{}`, chỉ không cho nó bỏ phiếu) — số phiếu
chẵn có rủi ro 2 cụm bằng nhau không cụm nào áp đảo, giống hệt rủi ro "2 engine
hoà 1-1" ở quy mô lớn hơn. **Đánh đổi cần biết:** trang chỉ có đúng 2 engine sẽ
không còn thấy bất đồng 1-1 trong `uncertain_spans` nữa (engine thứ 2 bị loại
trước khi so dòng) — muốn soát tay vẫn đọc được đầy đủ trong `engines{}`.

**Cập nhật 2026-09-15 (tiếp) — chọn backbone/engine bị loại theo ĐỘ GIỐNG NHAU
thật giữa các tool, không theo priority cố định nữa.** Trước đó ưu tiên cố
định `kim_hannom_lab > paddle_v6 > deepseek > google_vision > gemini` luôn
chọn kim_hannom_lab làm backbone và luôn loại gemini đầu tiên khi cần giữ số
lẻ — không phản ánh đúng thực tế mỗi trang. Đổi sang `rank_by_similarity()`:
tính độ giống trung bình (bag-of-lines, không phụ thuộc thứ tự dòng — xem lý
do trong docstring hàm, phát hiện thật paddle_v6 có trang đọc đúng thứ tự cột
NGƯỢC hẳn engine khác dù nội dung gần giống) giữa mỗi engine với TỪNG engine
khác có dữ liệu cùng trang; engine giống đa số nhất làm backbone, engine lạc
nhóm nhất bị loại đầu tiên khi cần giữ lẻ. Kết quả thật trên 529 trang cache:

| Engine | Số lần làm backbone | Số lần bị loại (giữ lẻ) | Độ giống TB với engine khác |
|---|---|---|---|
| paddle_v6 | **328** | 14 | **0,605** |
| deepseek | 88 | 25 | 0,535 |
| kim_hannom_lab | 54 | 33 | 0,584 |
| gemini | 51 | **137** | 0,451 |
| google_vision | 8 | 5 | 0,468 |

paddle_v6 hoá ra giống đa số nhất trên phần lớn trang (62%) — điều bản priority
cũ không bao giờ cho thấy vì kim_hannom_lab luôn được ưu ái làm backbone bất kể
dữ liệu thật. Gemini/Google Vision vẫn có độ giống trung bình thấp nhất trên
diện rộng — nhưng vì xếp hạng giờ tính LẠI cho TỪNG trang, trang nào Gemini
thật sự đọc gần đúng đa số (vd. `nom-1255/001`: Gemini 0,853, gần ngang
paddle_v6 0,907) thì Gemini vẫn được tin — đúng ý quan sát "Gemini đúng nhiều
hơn" của thầy có thể đúng ở NHỮNG TRANG CỤ THỂ dù không đúng trên trung bình
toàn bộ 529 trang. Chi tiết thuật toán: `rank_by_similarity()` trong
`scripts/vote_ocr.py`.

**Cập nhật 2026-09-17 — fallback vote THEO TỪNG VỊ TRÍ khi cả câu không đủ đa
số.** Vote CÂU (2026-09-14) chọn NGUYÊN 1 dòng thắng cuộc, nên nếu mỗi engine
chỉ sai ở 1 CHỖ KHÁC NHAU trong cùng 1 câu (vd. engine A thiếu 1 chữ giữa câu,
engine B thừa 1 chữ ở chỗ khác), không dòng nào đủ giống dòng nào để thắng —
có khi còn ngược lại: 2 engine tình cờ CÙNG SAI giống nhau (cùng thiếu 1 chữ)
lại bị tính là "đa số" (`line_confirmed_majority`), trong khi 3 engine khác
đọc ĐÚNG đúng chữ đó (mỗi engine chỉ sai 1 chỗ khác) lại không được tính vì
nhìn CẢ DÒNG thì không giống nhau. `vote_line_positional()` sửa việc này:
căn từng engine khác vào đúng vị trí ký tự của backbone bằng
`Levenshtein.editops()` thật (xử lý được cả chèn/xoá, không bỏ qua như
difflib ở bản vote ký tự cũ bên dưới), rồi vote riêng từng vị trí/khe hở theo
ĐÚNG luật gốc trong `CLAUDE.md` của repo — chỉ tự sửa khi ≥3/5 engine đồng
thuận tại đúng 1 vị trí. Chỉ chạy cho dòng mà vote CÂU chưa rõ ràng
(`line_no_majority`/`line_confirmed_majority`); dòng đã `line_unanimous`/
`line_majority_override` giữ nguyên, không chạy lại.

Kiểm chứng offline (không gọi API mới, dùng cache thật `runs/nom-208/*.vote.json`,
20 trang đầu, 5/5 engine): 348 dòng rơi vào diện fallback, trong đó fallback tự
sửa được 43 vị trí/khe hở có ≥3 engine đồng thuận mà vote CÂU bỏ lỡ. Ví dụ thật
(trang 1, dòng 1): backbone đọc `鋭`, 3/4 engine khác đọc `銳` (dị thể phồn thể
đúng) → tự sửa thành `銳`; trang 1 dòng 10: `為`→`爲` (3/4 đồng thuận); trang 3
dòng 4: `楊`→`揚` (3/5 đồng thuận). Các chỗ chỉ có <3 engine đồng ý (vd. lỗi lẻ
của riêng 1 engine) vẫn giữ nguyên và được ghi rõ vào `uncertain_positions` bên
trong `uncertain_spans` của dòng đó — không bị tự sửa nhầm theo thiểu số. Chi
tiết thuật toán và lý do đổi từ vote-cả-cụm-chèn sang vote-từng-ký-tự-trong-cụm:
docstring hàm `vote_line_positional()` trong `scripts/vote_ocr.py`.

### Lịch sử — bản vote ký tự (đến 2026-09-13, giữ lại để tham khảo)

**Cập nhật 2026-09-09 — test thật với ĐỦ 5 engine** trên `gpc-dang-1928`
(4 trang, lệnh dùng: `python3 scripts/vote_ocr.py --book gpc-dang-1928 --pages 0,1,2,6`):

| Trang | Số ký tự | uncertain_rate (2 engine, bản cũ) | uncertain_rate (5 engine) | Số ký tự **tự sửa** (đa số thật ≥3 engine) |
|---|---|---|---|---|
| 0 | 3 | 0% | 0% | 0 |
| 1 | 89 | 10,1% | **22,5%** | 9 |
| 2 | 17 | 0% | 5,9% | 1 |
| 6 | 101 | 16,8% | **35,6%** | 12 |
| **Tổng** | **210** | — | **27,1%** | **22** |

Hai quan sát quan trọng, tránh hiểu lầm:

1. **uncertain_rate TĂNG khi thêm engine — đây là điều đúng, không phải lỗi.**
   Thêm engine không tạo ra bất đồng mới, nó chỉ **phát hiện** bất đồng vốn đã ở
   đó mà 2 engine cũ tình cờ trùng nhau. Càng nhiều nguồn độc lập, càng ít chỗ
   "trùng ngẫu nhiên" che giấu lỗi thật.
2. **22/57 vị trí bất đồng (39%) giờ tự sửa được bằng đa số thật** (≥2 trong 4
   engine khác đồng ý với nhau, khác backbone) — điều **không thể xảy ra** khi
   chỉ có 2 engine (tối đa hoà 1-1, `vote_ocr.py` không bao giờ tự đoán). Ví dụ
   trang 2: `顔` (backbone kim_hannom_lab) bị 3 phiếu (`顏`×2 + `颜`×1) áp đảo →
   tự sửa thành `顏` — đúng thể chữ phồn thể chuẩn.

Ví dụ bất đồng còn kinh điển từ bản 2-engine cũ vẫn giữ nguyên: trang 1 dòng
cuối, lab đọc `欤` (trợ từ nghi vấn, khớp đúng ngữ pháp câu "khởi bất vĩ dư!"
trong bản dịch đã có), paddle đọc `欣` (vui mừng — sai nghĩa dù mặt chữ gần
giống). Nếu chỉ tin 1 engine làm "khung" và ghi chú riêng ra file khác (cách
làm cũ của `mix_hannom.py`), lỗi loại này lọt thẳng vào input cho bước phiên
âm/dịch nghĩa mà không ai để ý.

`vote_ocr.py` sửa việc này bằng vote ký tự thật (xem docstring đầu file để
biết chi tiết thuật toán): mỗi vị trí ký tự được "bỏ phiếu" giữa các engine;
**chỉ tự động sửa khi có đa số thật sự (≥3 engine đồng thuận)**; mọi bất đồng
— dù đã tự sửa hay chưa — được liệt kê tường minh vào `uncertain_spans` (kèm
toạ độ dòng/vị trí + toàn bộ phiếu bầu) ngay trong chính record, không phải
file ghi chú rời có thể bị bỏ qua. Kết quả 4 trang này đã được gộp thật vào
`data/track2_bilingual/gpc-dang-1928.json` qua `build_record.py`.

## 5 tool OCR-vote (Track 1)

Đúng 5 tool đã chốt: **Paddle v6, Kim Hán Nôm Lab, DeepSeek, Google Vision, Gemini**.
(XÁC NHẬN 2026-09-08: "CLC" nhắc trong họp trước và "Kim Hán Nôm Lab" là **1 dịch vụ
duy nhất**, không phải 2 engine khác nhau — đã gộp lại, không có adapter `clc.py`
riêng.) Nguyên tắc: 1 engine ưu tiên làm khung đọc cột (mặc định `kim_hannom_lab`),
các engine khác chỉ **đối chiếu** (similarity ratio) — không tự trộn chữ, kế thừa
triết lý từ `family-tree/nlp_family_extractor/tools/mix_hannom.py`.

**Trạng thái key hiện tại (2026-09-09):**

| Engine | Sẵn sàng? |
|---|---|
| `paddle_v6` | ✅ chạy được (đọc kết quả PaddleOCR đã có trong family-tree) |
| `kim_hannom_lab` (= CLC) | ✅ chạy được (đọc kết quả Kim Hán Nôm Lab đã có trong family-tree) |
| `gemini` (vai trò OCR) | ✅ XÁC NHẬN 2026-09-09 — chạy được với GOOGLE_API_KEY sẵn có, nhưng tốn quota/request thật mỗi trang (không đọc cache như 2 engine trên) |
| `deepseek` | ✅ XÁC NHẬN 2026-09-09 — chạy được thật (6 dòng đọc đúng, trang 1 `gpc-dang-1928`, kể cả đọc đúng "元龜") sau khi user tự top-up $2 (Claude không được phép giao dịch tài chính thay). |
| `google_vision` | ✅ XÁC NHẬN 2026-09-09 — chạy được thật (7 dòng đọc đúng, trang 1 `gpc-dang-1928`). Billing account "Firebase Payment" chỉ cần reopen (không cần thẻ mới) nên thực hiện được trong phiên này. |

**Cả 5/5 adapter đã chạy thật, không còn stub** — `paddle_v6`, `kim_hannom_lab`,
`gemini`, `google_vision`, `deepseek`. Test 3 engine trở lên trên cùng 1 trang
(`gpc-dang-1928` trang 1) cho kết quả gần như trùng khớp — sẵn sàng để
`vote_ocr.py` bắt đầu vote đa số thật (≥3 engine) thay vì chỉ flag
`uncertain_spans` như trước.

Chạy tool nào đang có key trước, không chờ đủ 5 — `vote_ocr.py` tự bỏ qua engine
trả `None`.

### Thiết lập `.env` (mang key sang máy khác)

`deepseek.py` và `google_vision.py` đọc key từ file `.env` ở gốc repo này
(KHÔNG commit — đã có trong `.gitignore`). Để chuyển sang máy khác:

1. Copy 2 file sau sang máy mới, giữ đúng vị trí:
   - `.env` (chứa `DEEPSEEK_API_KEY` + đường dẫn `GOOGLE_APPLICATION_CREDENTIALS`)
   - `secrets/google_vision_sa.json` (service account key JSON của Cloud Vision)
2. Nếu không copy được `.env` (vd. máy mới, key đã đổi), dùng `.env.example`
   làm mẫu: `cp .env.example .env` rồi điền lại `DEEPSEEK_API_KEY` (lấy tại
   https://platform.deepseek.com/api_keys) và đường dẫn tới file key Vision.
3. `gemini.py` KHÔNG đọc từ `.env` của repo này — nó đọc `GOOGLE_API_KEY` từ
   `family-tree/nlp_family_extractor/.env` (dùng chung với vai trò dịch nghĩa
   L3 bên family-tree), xem `_ensure_client()` trong `scripts/ocr_adapters/gemini.py`.
4. Không sửa cấu trúc 2 biến trong `.env.example` khi thêm engine mới — chỉ
   thêm dòng mới, tránh phá format đang dùng trong `_ensure_key()`/`_ensure_client()`
   của các adapter.

## Chạy pipeline cho 1 tài liệu đã đăng ký (đã có trong `data/track*/`)

```bash
python3 scripts/run.py <doc_id>              # 3 trang đầu (mặc định, an toàn quota)
python3 scripts/run.py <doc_id> --pages 0,6  # đúng các trang này
python3 scripts/run.py <doc_id> --all        # TOÀN BỘ trang — tốn quota thật, cân nhắc
```

1 lệnh làm hết: vote OCR từng trang → lưu thô vào `runs/<doc_id>/` → gộp vào
`data/track*/<doc_id>.json` → in `uncertain_rate` trung bình + đường dẫn kết
quả cuối. Muốn xem chi tiết thuật toán/flag riêng từng bước, `vote_ocr.py` và
`build_record.py` (mà `run.py` gọi bên trong) vẫn dùng được độc lập — xem
docstring 2 file đó.

L2 (phiên âm) + L3 (dịch nghĩa) chưa tự động — dùng lại tool bên family-tree
(`dich_hannom_catalog.py`, `dich_qwen.py`) rồi điền tay vào `page["l2_phien_am"]`/
`page["l3_dich_nghia"]` trong file JSON kết quả cuối (backlog: nối tự động).

## Thêm tài liệu MỚI vào repo — 3 bước

Dành cho ảnh/scan **chưa từng có** trong family-tree (trường hợp phổ biến nhất
khi anh tìm thêm dữ liệu bỏ vào). Không cần tự sửa tay `books_catalog.json`.

**Bước 0 — chưa biết đặt `doc_id` gì? Để script gợi ý, đảm bảo không trùng:**

```bash
python3 scripts/suggest_doc_id.py --ho "Nguyễn"    # -> nguyen-01 (hoặc -02... nếu đã có)
python3 scripts/suggest_doc_id.py                  # chưa rõ họ -> moi-01
```

Chỉ đọc `books_catalog.json` để kiểm tra trùng, không ghi/đăng ký gì cả — script
in luôn 2 lệnh tiếp theo (mkdir + add_new_source.py) để copy chạy ngay.

**Bước 1 — bỏ ảnh vào đúng thư mục**, đặt tên theo số thứ tự trang bắt đầu từ 0:

```text
family-tree/data/00_raw/hannom_inbox/<doc_id>/0.jpg
family-tree/data/00_raw/hannom_inbox/<doc_id>/1.jpg
...
```

(chấp nhận `.jpg`/`.jpeg`/`.png`; `<doc_id>` chỉ chữ thường/số/gạch ngang, vd. `nom-2000`)

**Bước 2 — chạy đúng 1 lệnh:**

```bash
python3 scripts/add_new_source.py --doc-id <doc_id> \
  --title-vn "Tên gọi tiếng Việt" [--title-han "漢字"] [--ho "Họ"]
```

Lệnh này tự động: thêm entry vào `books_catalog.json` (chỉ append, không sửa
entry khác) → chạy lại `build_manifest.py` → tạo record Track 1 draft (mọi
trường phân loại để `null` + ghi_chu "Chưa phân loại", không bịa) → validate
schema. Xong sẽ in sẵn lệnh bước tiếp theo để xem OCR ngay (chính là lệnh ở
mục "Chạy pipeline" phía trên):

```bash
python3 scripts/run.py <doc_id>
```

**Đã test thật 2026-09-09** (2 lần, mỗi lần 1 ảnh demo, dọn dẹp sau khi test —
không để lại trong repo): `add_new_source.py` + `run.py` chạy sạch từ đầu đến
cuối, nhận diện đúng **3/5 engine** (`deepseek`, `google_vision`, `gemini` — 3 engine gọi API sống
trên ảnh bất kỳ). **Lưu ý quan trọng**: `paddle_v6` và `kim_hannom_lab` KHÔNG
chạy được cho ảnh hoàn toàn mới — 2 adapter này chỉ đọc file kết quả đã có sẵn
từ pipeline cũ trong family-tree (`nlp_family_extractor/tools/ocr_paddleocr.py`,
`ocr_lab_hannom_catalog.py`), chưa tự gọi OCR trên ảnh mới. Muốn đủ 5/5 engine
cho tài liệu mới, cần tự chạy 2 tool đó bên `family-tree` trước (xem thư mục
`nlp_family_extractor/tools/`), hoặc chấp nhận 3/5 engine (vẫn đủ để vote —
xem quy tắc ≥3 engine ở mục Phân tích phía trên).

Nếu tài liệu là PDF/Word hoặc đã có sẵn bản dịch (Track 2/3), quy trình này
chưa hỗ trợ tự động — viết tay record theo mẫu trong `data/track2_bilingual/`
hoặc `data/track3_viet_only/`, rồi validate bằng lệnh ở mục Schema phía trên.

## Backlog

- Chạy OCR-vote thật cho 17 tài liệu Track 1 — cần key DeepSeek/CLC/Google Vision.
- Bước L2/L3 hàng loạt cho Track 1 sau khi có L1.
- Đẩy repo lên GitHub (remote) — chưa làm, quyết định riêng khi cần.
- 3 tài liệu Track 1 còn nghi vấn cần đọc thêm để xác nhận: `nom-557` (bia đá,
  không thuộc 4 hình thức Bộ/Đồ/Ký/Điệp — cần hỏi thầy xếp vào đâu), `nom-833`
  (địa danh Mộ Trạch thường gắn họ Vũ, chưa rõ vì sao đây là họ Lê), `nom-429`
  (page_count=0 trong nguồn crawl, cần kiểm tra lại file gốc).
