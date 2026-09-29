# Kế hoạch hoàn thiện Track 1 (17 tài liệu Hán Nôm thô)

Cập nhật: 2026-09-12. Claude Code đã **dừng tự chạy tiếp** theo yêu cầu —
file này ghi lại chính xác trạng thái và bước tiếp theo để tiếp tục sau
(bằng Cursor, phiên Claude khác, hoặc tự tay).

## Mục tiêu

Mỗi tài liệu Track 1 cần đủ 4 lớp: **L1 (OCR 5-engine + vote) → L2 (phiên
âm) → L3 (dịch nghĩa + tự tạo pairs) → phân loại/mã định danh** (bước cuối
làm thủ công, không tự động hoá được).

## Trạng thái thật hiện tại (chạy `python3 scripts/status.py --track 1`)

| doc_id | Trang thật | L1 (vote 5-engine) | L2 (phiên âm) | L3 (dịch nghĩa) | Ghi chú |
|---|---|---|---|---|---|
| `nom-1255` | 6 | ✅ | ✅ | ✅ | **Xong hoàn toàn**, có `ma_dinh_danh` |
| `nom-1158` | 55 | ✅ | ✅ | ✅ | Xong OCR/dịch, **chưa phân loại** |
| `nom-865` | 21 | ✅ | ✅ | ✅ | Xong OCR/dịch, **chưa phân loại** |
| `nom-1256` | 30 | ✅ | ✅ | ✅ | Xong OCR/dịch, **chưa phân loại** |
| `nom-854` | 40 | ✅ | ✅ | ✅ | Xong OCR/dịch, **chưa phân loại** |
| `nom-563` | 44 | ✅ | ✅ | ⏳ đang chạy | Gần xong (dịch nghĩa) |
| `nom-84` | 47 | ❌ chỉ 2/5 engine cũ | ❌ | ❌ | **Chưa bắt đầu lại** |
| `nom-557` | 55 | ❌ chỉ 2/5 engine cũ | ❌ | ❌ | **Chưa bắt đầu lại** |
| `nom-147` | 58 | ❌ chỉ 2/5 engine cũ | ❌ | ❌ | **Chưa bắt đầu lại** |
| `nom-833` | 60 | ❌ chỉ 2/5 engine cũ | ❌ | ❌ | **Chưa bắt đầu lại** |
| `nom-208` | 79 | ❌ chỉ 2/5 engine cũ | ❌ | ❌ | **Chưa bắt đầu lại** |
| `nom-207` | 85 | ❌ chỉ 2/5 engine cũ | ❌ | ❌ | **Chưa bắt đầu lại** |
| `pdf-1000-mai` | ~131 (chưa xác nhận chính xác) | ❌ mới 3 trang mẫu | ❌ | ❌ | Cần đếm lại số trang thật trước |
| `pdf-1001-la` | chưa rõ | ❌ mới 3 trang mẫu | ❌ | ❌ | Cần đếm lại số trang thật trước |
| `pdf-1005-tran` | chưa rõ | ❌ mới 3 trang mẫu | ❌ | ❌ | Cần đếm lại số trang thật trước |
| `nom-429` | 9 | ✅ (chỉ deepseek+google_vision, tạm bỏ Gemini) | ✅ | ✅ | **Xong hoàn toàn**, có `ma_dinh_danh` (F-B-NG-ThuyUng-005-1912, ID suy luận) |
| `nom-855` | 100 | ✅ (chỉ deepseek+google_vision, tạm bỏ Gemini) | ✅ | ✅ | **Xong hoàn toàn**, có `ma_dinh_danh` (F-A-NG-TrungTu-006-1843, ID suy luận) |

**2026-09-13**: `nom-429`/`nom-855` được tải lại ảnh gốc (commit `cdd4186`) và
đã chạy L1+L2 (chỉ 2/5 engine — thiếu Gemini/Paddle/CLC lúc đó — nên
`uncertain_rate` có thể cao hơn các tài liệu dùng đủ 5 engine, cân nhắc chạy
lại vote với đủ engine trước khi tin tưởng hoàn toàn). Không còn nằm trong
diện loại bỏ vĩnh viễn. `nom-429` đã chạy xong L3 luôn (đổi API key sang
project Egitech/billing Firebase Payment vì key cũ HCMUS Learn hết credit;
model `gemini-3.5-flash-lite` — `gemini-2.5-flash-lite` bị 404 trên project
mới).

**Tổng còn phải xử lý thật sự**: 6 tài liệu nomfoundation (nom-84, nom-557,
nom-147, nom-833, nom-208, nom-207) = 384 trang, cộng 3 tài liệu pdf-* chưa
rõ tổng số trang (ước tính +300-400 trang nếu làm đủ). `nom-429`+`nom-855`
đã xong hoàn toàn L1+L2+L3.

## Quy trình 3 bước (đã ổn định, dùng lại nguyên văn)

```bash
cd /Users/forestlam/Documents/projects/cao_hoc/source/hannom-bilingual-dataset

# 0. Lấy danh sách trang thật của 1 tài liệu
python3 -c "
import json
d = json.load(open('data/track1_hannom_only/<doc_id>.json', encoding='utf-8'))
print(','.join(sorted(p['page_id'] for p in d['pages'])))
"

# 1. Vote OCR 5-engine (timeout 90s/lệnh, không còn treo vô hạn)
python3 scripts/run.py <doc_id> --pages <page_list>

# 2. Phiên âm (API lab, miễn phí)
python3 scripts/phien_am.py <doc_id> --pages <page_list>

# 3. Dịch nghĩa (Gemini, tự tạo pairs theo dòng)
python3 scripts/dich_nghia.py <doc_id> --pages <page_list>
```

Bước 2 và 3 ghi file **ngay sau mỗi trang** — an toàn nếu giữa chừng lỗi.
Sau mỗi bước, kiểm tra trang thiếu và chạy lại riêng (Gemini thỉnh thoảng
trả sai định dạng JSON, ~1-5% số trang, chạy lại là qua):

```bash
python3 -c "
import json
d = json.load(open('data/track1_hannom_only/<doc_id>.json', encoding='utf-8'))
print('thieu L2:', [p['page_id'] for p in d['pages'] if not p.get('l2_phien_am')])
print('thieu L3:', [p['page_id'] for p in d['pages'] if not p.get('l3_dich_nghia')])
"
```

Sau khi xong 1 tài liệu (đủ L1+L2+L3):
```bash
python3 -c "
import json, jsonschema
schema = json.load(open('schema/bilingual_record.schema.json', encoding='utf-8'))
v = jsonschema.Draft7Validator(schema)
d = json.load(open('data/track1_hannom_only/<doc_id>.json', encoding='utf-8'))
print('schema errors:', len(list(v.iter_errors(d))))
"
python3 scripts/build_dashboard.py
git add data/track1_hannom_only/<doc_id>.json dashboard/index.html dashboard/status.json
git commit -m "Hoàn thiện <doc_id>: đủ L1+L2+L3 cho N/N trang"
git push
```

## Vấn đề đã biết & đã sửa (đừng lặp lại)

1. **Treo vô hạn** khi gọi Gemini/Google Vision không timeout — ĐÃ SỬA
   (commit `4b46ad1`), dùng `call_with_timeout()` trong
   `scripts/ocr_adapters/base.py`, 90s/lệnh.
2. **`l0_image` sai/thiếu** cho phần lớn trang mới merge từ vote cũ (do
   `build_record.py` tạo trang mới với `l0_image=None`) — ĐÃ SỬA cho tất cả
   tài liệu hiện có (commit `4b46ad1`, `f969fb7`).
3. **1 trang ma mỗi tài liệu** (catalog `page_count` = 2× số ảnh thật) — ĐÃ
   LOẠI BỎ cho các tài liệu đã đụng tới. **Các tài liệu CHƯA đụng tới
   (nom-84, nom-557, nom-147, nom-833, nom-208, nom-207) đã được sửa sẵn
   trong commit `f969fb7`** — không cần làm lại.
4. Chỉ ghi file sau MỖI TRANG (không phải cuối cả batch) trong
   `phien_am.py`/`dich_nghia.py` — ĐÃ SỬA (commit gần nhất) — giúp thấy tiến
   độ thật + không mất dữ liệu nếu crash giữa chừng.
5. `google_vision` không phản hồi ổn định (thường 4/5 engine thay vì 5/5) —
   không chặn tiến độ, không cần điều tra thêm trừ khi cố tình muốn đủ 5/5.

## Việc CHƯA làm được / cần quyết định thêm

- **3 tài liệu pdf-*** (`pdf-1000-mai`, `pdf-1001-la`, `pdf-1005-tran`): hiện
  record chỉ có 3 trang mẫu (đầu/giữa/cuối), CHƯA có đủ page entries cho
  toàn bộ tài liệu như 12 tài liệu nomfoundation kia. Cần: (a) đếm số ảnh
  thật trong thư mục `data/00_raw/du_lieu_han_nom_moi/13_8_2026/<doc_id>/pages/`,
  (b) tạo đủ page entries (giống cấu trúc hiện có), (c) mới chạy được 3 bước
  ở trên. **Việc này cần làm trước khi chạy pipeline cho 3 tài liệu này.**
- **Phân loại + mã định danh** cho TẤT CẢ tài liệu (kể cả 5 tài liệu đã xong
  L1-L3): cần đọc trực tiếp ảnh gốc để xác định `quy_mo`, `hinh_thuc`, `ho`,
  `dia_danh`, `nien_dai` rồi tính `ma_dinh_danh` theo công thức đã chốt với
  thầy (xem README.md mục "doc_id vs ma_dinh_danh"). **Không tự động hoá
  được** — việc đọc + phân tích thủ công, làm dần từng tài liệu.

## Phân công đề xuất (tránh 2 bên cùng sửa 1 file)

- Nếu chạy song song nhiều "thợ" (Cursor, phiên Claude khác, tự tay): **mỗi
  bên nhận trọn 1-2 tài liệu**, không chia nhỏ theo trang — vì mỗi tài liệu
  là 1 file JSON riêng, chia theo tài liệu tránh xung đột Git hoàn toàn.
- File `dashboard/index.html` + `dashboard/status.json` là **sinh tự động**
  — nếu `git pull` báo conflict ở 2 file này, không cần merge tay, chạy lại
  `python3 scripts/build_dashboard.py` rồi commit đè.
- Luôn `git pull` trước khi bắt đầu 1 tài liệu mới, và trước khi push.

## Tiêu chí hoàn thành Track 1

- [ ] 6 tài liệu nomfoundation còn lại: đủ L1+L2+L3 (384 trang)
- [ ] `nom-429`+`nom-855`: chạy L3 (109 trang), cân nhắc chạy lại L1 với đủ
      5 engine (hiện chỉ có deepseek+google_vision)
- [ ] 3 tài liệu pdf-*: xác định đủ page entries + chạy đủ L1+L2+L3
- [ ] Toàn bộ 17 tài liệu: có `quy_mo`, `hinh_thuc`, `ho`, `dia_danh`,
      `nien_dai` (đọc trực tiếp, không suy đoán) — không còn tài liệu nào bị
      loại vĩnh viễn
- [ ] Tính `ma_dinh_danh` cho tài liệu nào đủ điều kiện (đã đọc xong 5 thành
      phần + xác định được ID tăng dần)
- [ ] `python3 scripts/build_dashboard.py` chạy sạch, dashboard hiện đúng
      100% tài liệu đủ L1/L2/L3
