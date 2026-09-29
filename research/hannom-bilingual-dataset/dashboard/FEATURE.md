# Feature: Dashboard xem & duyệt toàn bộ dataset

## Mục tiêu

1 trang xem tổng quan toàn bộ tài liệu trong repo — thay vì phải mở từng file
JSON hay chạy `scripts/status.py` mỗi lần. Dùng để **duyệt và update từ từ**
(user tự mở lại nhiều lần khi có thêm phân loại/OCR/dịch mới), không phải
báo cáo 1 lần rồi bỏ.

## Vị trí file

**Cập nhật 2026-09-21 — tách kiến trúc để hết lag.** Bản đầu nhúng NGUYÊN VĂN
nội dung toàn bộ 25 tài liệu / ~1.275 trang vào 1 file `index.html` — sau khi
vote lại bằng thuật toán câu/Levenshtein (dữ liệu `uncertain_spans` nặng hơn
nhiều), file này phình lên **111MB**, vừa lag nặng khi mở vừa vượt giới hạn
100MB của GitHub. Giờ tách thành khung nhẹ + dữ liệu tải riêng theo yêu cầu:

```
hannom-bilingual-dataset/
  scripts/build_dashboard.py   # sinh các file dưới, chỉ đọc dữ liệu có sẵn
                                # (KHÔNG gọi OCR/API nào)
  dashboard/
    FEATURE.md                 # file này
    Dockerfile                 # build 3 file dưới NGAY trong image (multi-stage),
                                # không commit — xem lý do trong .gitignore
    status.json                # số liệu tổng hợp (KHÔNG có nội dung từng trang)
    index.html                 # khung nhẹ (~40KB): danh sách tóm tắt 25 tài liệu
    data/<doc_id>.html         # nội dung đầy đủ 1 tài liệu — index.html fetch()
                                # file này khi người xem MỞ đúng tài liệu đó
    data/<doc_id>.json         # JSON gốc 1 tài liệu — fetch() khi bấm nút "JSON"
```

**Cần server tĩnh để xem** (vd. `python3 -m http.server` trong thư mục
`dashboard/`, hoặc qua Docker/nginx khi deploy) — mở trực tiếp bằng
double-click (`file://`) sẽ KHÔNG tải được `data/*.html`/`.json` vì trình
duyệt chặn `fetch()` tới file cục bộ. Đánh đổi này chấp nhận được vì lợi ích
(hết lag, không vượt giới hạn GitHub) lớn hơn nhiều so với bất tiện thêm 1
lệnh khi xem local.

`index.html`, `status.json`, `data/` đều **không commit** (gitignore) — tự
sinh lại bất cứ lúc nào bằng `python3 scripts/build_dashboard.py`, hoặc tự
sinh trong lúc build Docker image (xem `dashboard/Dockerfile`).

## Nguồn dữ liệu (input, chỉ đọc)

- `manifest/classification.json` — map doc_id → track 1/2/3
- `data/track1_hannom_only/*.json`, `data/track2_bilingual/*.json`,
  `data/track3_viet_only/*.json` — toàn bộ nội dung record (đã có sẵn
  `l1_ocr.engines{}`, `voted_text`, `uncertain_rate`, `l2_phien_am`,
  `l3_dich_nghia`, `pairs`, `ma_dinh_danh`)

## 3 nhóm hiển thị (theo đúng track đã có, đổi tên cho dễ hiểu)

| Track | Tên nhóm hiển thị |
|---|---|
| 1 | Hán Nôm thô |
| 2 | Hán Nôm đã dịch (chưa dóng hàng) |
| 3 | Tiếng Việt hiện đại |

## Cấu trúc `status.json` (rút gọn)

```jsonc
{
  "generated_at": "2026-09-11T...",
  "overall_stats": {
    "total_docs": 28,
    "by_group": {"1": 17, "2": 3, "3": 4},
    "excluded": 4,
    "with_ma_dinh_danh": 3,
    "l1_done_docs": 12, "l2_done_docs": 1, "l3_done_docs": 3
  },
  "documents": [
    {
      "doc_id": "nom-1255",
      "ma_dinh_danh": null,
      "group": 1,
      "title_han": "朱族譜記", "title_vn": "Chu tộc gia phả",
      "ho": null, "quy_mo": null, "hinh_thuc": null,
      "dia_danh": null, "nien_dai": null,
      "status": "l2_done",
      "stats": {
        "total_pages": 6, "pages_l1": 6, "pages_l2": 6, "pages_l3": 0,
        "engines_used": ["kim_hannom_lab","paddle_v6","deepseek","google_vision","gemini"],
        "avg_uncertain_rate": 0.25
      },
      "pages": [
        {
          "page_id": "001",
          "l0_image": "data/00_raw/.../001.jpg",
          "engines": { "kim_hannom_lab": "...", "paddle_v6": "...", "...": "..." },
          "voted_text": "...", "uncertain_rate": 0.208,
          "l2_phien_am": "...", "l3_dich_nghia": null,
          "pairs": []
        }
      ]
    }
  ]
}
```

`status.json.documents[].pages` KHÔNG còn tồn tại (đã tách sang
`data/<doc_id>.html`/`.json`) — cấu trúc `pages` ở trên vẫn đúng nhưng giờ chỉ
nằm trong `data/<doc_id>.json`, không nằm trong `status.json` nữa.

## Giao diện `index.html`

1. **Đầu trang** — thống kê tổng quan + hộp **Cách vote L1** (backbone, phiếu lẻ, gom cụm câu, fallback vị trí). Thẻ số thêm: trang vote câu, trang 1 phiếu, dòng ghi đè backbone.
2. **3 khối danh sách** theo 3 nhóm: doc_id, tên, mã định danh, badge trạng thái, kiểu vote (`vote câu` / `1 phiếu lẻ`), backbone chủ yếu, số dòng ghi đè, uncertain_rate. Mỗi dòng là 1 `<details>` — mở ra mới `fetch()` `data/<doc_id>.html` (lazy load).
3. **Chi tiết 1 tài liệu** (tải riêng, `data/<doc_id>.html`) — từng trang:
   - Tóm tắt `vote_method` đã giải (backbone nào, bao nhiêu engine khác, engine bị loại vì phiếu lẻ)
   - OCR từng engine: nhãn backbone / loại phiếu lẻ / trùng kết quả cả trang + `similarity_to_others`
   - `voted_text` và ghi rõ kết quả trùng nguyên text engine nào hay mix theo dòng
   - **Từng dòng bất đồng — vote từng câu VÀ từng chữ** (mới 2026-09-21): method (`Ghi đè` / `Giữ backbone` / `Hoà phiếu`), phiếu `n_agree/n_total`; câu thắng gạch chân đỏ ở chữ có bất đồng; câu của từng engine thua tô màu theo Levenshtein thật (đỏ=bị thay, vàng=chữ thừa, chấm mờ=chữ thiếu); nếu có fallback từng vị trí (`vote_line_positional`), hiện đủ danh sách vị trí + engine nào bỏ phiếu ký tự gì (trước đây chỉ hiện 1 con số đếm)
   - Phiên âm (`l2_phien_am`), dịch nghĩa (`l3_dich_nghia`), pairs

## Cách cập nhật khi có phân loại/dữ liệu mới

Chạy lại đúng 1 lệnh, ghi đè `status.json` + `index.html` + toàn bộ `data/`:
```bash
python3 scripts/build_dashboard.py
```

## Phạm vi lần đầu (v1) — để sau nếu chưa cần

- Không sửa được dữ liệu trực tiếp trên trang (chỉ xem, không edit) — muốn sửa
  vẫn phải sửa file JSON record như hiện tại.
- Không tìm kiếm/lọc nâng cao — chỉ xem theo 3 nhóm sẵn có.
- Không tự động chạy lại `build_dashboard.py` — phải tự chạy tay sau khi có
  thay đổi dữ liệu.
