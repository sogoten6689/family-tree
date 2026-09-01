# Plan — Mixing 2 OCR → dịch âm → dịch nghĩa → cây (Hương, ảnh Hán-Nôm gốc)

> **Ngày:** 2026-08-31  
> **Họp:** [24_08_2026.md](../lab/note_meeting_weekly/24_08_2026.md) — *OCR → dịch âm → dịch nghĩa → cây*  
> **Pilot:** `data/00_raw/du_lieu_han_nom_moi/25_8_2026/Hương/Nguyễn Kế Hán Nôm/`  
> **SSOT cây:** [output_formats_and_ui_plan.md](./output_formats_and_ui_plan.md) (`BalkanNode[]`)  
> **Lớp chữ:** [labeling_and_hannom_ocr_plan.md](./labeling_and_hannom_ocr_plan.md) §3.1 (L0–L3)  
> **Renderer:** `tools/render_family_tree.py` — HTML tĩnh từ `nodes.json`, 1 file/gia đình, không Docker/admin (quyết định 2026-08-31, xem [mix_translate_yeu_cau.md §B](./mix_translate_yeu_cau.md))

---

## 0. Ràng buộc

**Đọc** ảnh gốc + 2 file OCR máy (Paddle, lab).  

**Không đụng** kết quả của Hương (không sửa, không xoá, không ghi đè):

| Để yên | Path |
|--------|------|
| Ảnh gốc | `Nguyễn Kế Hán Nôm/pages/{0..14}.jpg` |
| OCR máy đã chạy | `paddleocr/*`, `pages/{n}-ocr-raw.json`, `{n}-boundingbox*` |
| Word / ghi chú Hương | `*.docx` (Ô.cố, bằng khoán Diên Khánh), mọi copy trong `Nguyễn Kế gia phả/` |
| Đối soát cũ | `doi_soat_*.md` |

Mọi artifact **mới** (mix, âm, nghĩa, cây) chỉ ghi vào:

```text
data/01_interim/huong_nguyen_ke/
```

Không tạo `dich/` trong thư mục Hương.

---

## 1. Chuỗi làm việc

```text
L0  ảnh gốc          pages/{n}.jpg                    ← đã có
L1a Paddle           paddleocr/{n}-paddleocr.txt      ← đã có
L1b Lab Kim Hán Nôm  pages/{n}-ocr-raw.json           ← đã có
        ↓ mix (bỏ phiếu chữ, giữ thứ tự cột lab)
L1*  chữ Hán đã mix  01_interim/.../mix/{n}.han.txt   ← bạn làm
        ↓ dịch âm (API lab run_transliteration)
L2   phiên âm        01_interim/.../l2/{n}.transcription.txt
        ↓ dịch nghĩa (Qwen 3.6)
L3   Quốc ngữ        01_interim/.../l3/{n}.modern_vn.md
        ↓ trích người / quan hệ
Cây  BalkanNode[]    01_interim/.../nguyen-ke.nodes.json
        ↓ render_family_tree.py (free-only, không Docker/admin)
Sơ đồ HTML tĩnh      01_interim/.../tree/{i}-gia-dinh-*.html — 1 file/gia đình
```

Mixing = **bỏ phiếu từng dòng/chữ**, không nối hai bản OCR thành một chuỗi dài.

Quy tắc mix (từ đối soát p.0): **thứ tự cột lấy lab** (`result_ocr_text`); chỗ lab/Paddle lệch thì giữ lab nếu conf cao, ghi `[paddle: …]` vào ghi chú. Paddle p.0 bị xáo dòng (bắt đầu từ đồ thờ) — không dùng làm khung đọc.

---

## 2. Hiện trạng — bạn chưa cần OCR lại

| Bước | Trạng thái |
|------|------------|
| L0 15 ảnh | Có |
| L1a Paddle 15/15 | Có |
| L1b Lab 15/15 + bbox | Có |
| Mix L1* | **Chưa** — chưa có CLI mix 2 engine |
| L2 phiên âm | Tool có (`dich_hannom_catalog.py`) nhưng ghi vào `dich/` sách — **đổi dest** sang `01_interim` |
| L3 Qwen | Tool có (`dich_qwen.py`) — cùng vấn đề dest; mặc định chỉ 1 trang Paddle |
| Cây | **Chưa** — `POST /api/family-tree/analyze` nhận **văn bản Quốc ngữ** (L3), không nhận chữ Hán |

p.9 ≡ p.13 (ảnh trùng): chỉ pipeline **một** tờ.

---

## 3. Việc bạn cần làm (theo thứ tự)

### 3.1. Key / máy — đã kiểm (2026-08-31)

Probe: lab login **OK**; phiên âm `阮文顛` → `nguyễn văn điên` **OK**. Gemini `generate_content` **401**. Docker daemon **tắt**.

| Thứ | Có thể chạy? | Ghi chú |
|-----|----------------|---------|
| `HANNOM_EMAIL` / `HANNOM_PASSWORD` | Có | Đủ cho L2 |
| `DASHSCOPE_API_KEY` / `QWEN_*` | **Không** | `.env` trống → `dich_qwen.py` thoát ngay |
| `GOOGLE_API_KEY` | Có file, **key hỏng** | 401 `ACCESS_TOKEN_TYPE_UNSUPPORTED` — L3 Gemini + `analyze` cây không chạy |
| Mix CLI | **Không** | Chưa có `tools/mix*.py` |
| Dest `01_interim/` | **Chưa tạo** | Catalog mặc định ghi `dich/` trong thư mục Hương — **đừng chạy** |
| Catalog `nguyen-ke-han-nom` | Có | 28 sách |
| MySQL / API / admin | **Không** | Docker tắt; `.env` extractor không có `MYSQL_*` |
| `HANNOM_OCR_ID` | Lệch | `.env` = **3**; file lab sẵn = **1** — không ảnh hưởng L2 (đừng OCR lại) |

### 3.2. P0 — 2 tờ sạch (không đụng Hương)

Chọn **p.0** và **p.2** (mean Paddle cao, khớp nhân danh).

1. Tạo thư mục `data/01_interim/huong_nguyen_ke/{mix,l2,l3}/`.
2. **Mix** từng trang: đọc lab `result_ocr_text` + Paddle `.txt` → ghi `mix/{n}.han.txt` (một dòng Hán / một dòng lab).
3. **Dịch âm:** gọi lab `run_transliteration` trên `mix/{n}.han.txt` → `l2/{n}.transcription.txt`.  
   CLI hiện có đọc Paddle và ghi `Nguyễn Kế Hán Nôm/dich/` — **đừng chạy nguyên lệnh catalog** trừ khi sửa `--out` sang `01_interim`.
4. **Dịch nghĩa:** Qwen với input = L1* + L2 → `l3/{n}.modern_vn.md`.  
   Không lấy Word Hương làm input.
5. **Cây:** ghép L3 hai trang thành một văn bản quan hệ (cha/mẹ/con) → `POST /api/family-tree/analyze` **hoặc** gõ tay `nguyen-ke.nodes.json` (`id`, `name`, `gender`, `fid`/`mid`/`pids`).
   `analyze` không cần MySQL/Docker — chỉ cần `GOOGLE_API_KEY` (đã có, đã test) và chạy `uvicorn`/`python main.py` local, hoặc gọi thẳng hàm `normalize_balkan_nodes()` bằng script.
6. **Vẽ sơ đồ:** `python nlp_family_extractor/tools/render_family_tree.py --nodes 01_interim/huong_nguyen_ke/nguyen-ke.nodes.json` → mở `tree/index.html` bằng trình duyệt (double-click, không cần server/Docker).

**P0 xong khi:** có `mix/` + `l2/` + `l3/` cho p.0 và p.2, có `nguyen-ke.nodes.json`, `tree/*.html` mở được trong trình duyệt — và **git status không có** `.docx` / `pages/*.jpg` bị sửa.

### 3.3. P1 — đủ 14 tờ độc lập

Lặp 3.2 cho `{1,3,4,5,6,7,8,9,10,11,12,14}` (bỏ 13 = trùng 9).  
Tờ thảo (3–8, 11): mix sẽ yếu — L3 đánh `[không chắc]`; **không** bịa đời/chi.

### 3.4. P2 — báo cáo thầy

L3 + cây từ pipeline **của mình**. Hương chỉ để đối chiếu miệng nếu thầy hỏi — không copy Word vào `l3/`.

---

## 4. Lệnh / tool (sau khi có dest `01_interim`)

Hiện **chưa** có một lệnh “chạy cả chuỗi”. Việc cần **sửa dest** (hoặc script mỏng) trước khi batch:

| Bước | Tool sẵn | Việc phải chỉnh |
|------|----------|-----------------|
| Mix | `nlp_family_extractor/tools/mix_hannom.py --book nguyen-ke-han-nom --pages 0,2` | ✅ Đã viết — lab `result_ocr_text` là văn bản chính, Paddle chỉ đối chiếu trong `*.mix_notes.md` |
| L2 | `nlp_family_extractor/tools/dich_hannom_catalog.py --book nguyen-ke-han-nom` | **Chưa** — cần thêm `--in-dir`/`--out` để đọc `mix/`, ghi `l2/`, **cấm** `dich/` trong lô Hương |
| L3 | `nlp_family_extractor/tools/dich_qwen.py --book nguyen-ke-han-nom --pages 0,2` | **Chưa** — cần thêm `--in-dir`/`--l2-dir`/`--out`; prompt nhận L1*+L2; ghi `l3/{n}.modern_vn.md` |
| Cây | `POST /api/family-tree/analyze` body = L3 | Trả `balkan_nodes` → lưu tay thành `nguyen-ke.nodes.json` (không cần persist DB) |
| Sơ đồ | `nlp_family_extractor/tools/render_family_tree.py --nodes nguyen-ke.nodes.json` | ✅ Đã viết & test — HTML tĩnh, 1 file/gia đình, không Docker |

P0 có thể mix **tay** 2 trang (lab `result_ocr_text` đã thành list) rồi chỉ chạy L2/L3, hoặc dùng `mix_hannom.py` đã có.

---

## 5. Artifact đích

```text
data/01_interim/huong_nguyen_ke/
  mix/{n}.han.txt                # văn bản Hán đã mix, sạch — feed cho L2/L3
  mix/{n}.mix_notes.md           # đối chiếu lab/Paddle — chỉ để người soát, không feed API
  l2/{n}.transcription.txt
  l3/{n}.modern_vn.md
  nguyen-ke.quoc_ngu.md          # ghép L3
  nguyen-ke.nodes.json           # BalkanNode[]
  tree/index.html                # danh sách gia đình
  tree/{i}-gia-dinh-*.html       # 1 sơ đồ HTML tĩnh / gia đình (free-only, không Docker)
```

`node_meta.source` = `hannom_ocr_mix` khi import.

---

## 6. Cây sẽ ra gì (fact từ L1 đã có)

OCR p.0–2 (lab) có hộ: cha **Nguyễn Văn Điên** (阮文顛), mẹ **Trần Thị Nghiêm** (陈氏嚴), con **Thái / Bằng / Châu** (阮泰 阮朋 阮珠), phủ Diên Khánh.  

Cây P0 = hộ này (và ai còn tên trên 2 tờ). Không kỳ vọng phả đồ nhiều đời như ảnh Quốc ngữ in (`Nguyễn Kế gia phả/`) — nguồn P0 là **15 tờ Hán-Nôm gốc**, không phải folder in.

---

## 7. Việc / không làm

| Làm | Không |
|-----|--------|
| Mix 2 OCR → âm lab → nghĩa Qwen → `nodes.json` | Sửa/xoá Word, ảnh gốc, OCR đã có của Hương |
| Ghi hết vào `01_interim/` | Ghi `dich/` hay `*-qwen.md` trong thư mục Hương |
| P0 = p.0 + p.2 | OCR lại 15 ảnh; fine-tune Qwen tuần này |
| Sơ đồ HTML tĩnh (`render_family_tree.py`) — free-only, không Docker | Balkan.js; admin `dom-classic`; bất kỳ dependency license trả phí |

---

## 8. Checklist

- [x] `.env`: HANNOM + DASHSCOPE + GOOGLE_API_KEY (đã test cả 3, 2026-08-31)
- [x] Thư mục `01_interim/huong_nguyen_ke/{mix,l2,l3}/`
- [x] `tools/mix_hannom.py` viết xong
- [x] `tools/render_family_tree.py` viết xong, test bằng dữ liệu mẫu (nhánh + nhiều đời) — OK
- [ ] Thêm `--in-dir`/`--out` cho `dich_hannom_catalog.py` (L2) và `dich_qwen.py` (L3)
- [ ] Mix p.0, p.2 (chạy `mix_hannom.py`)
- [ ] L2 p.0, p.2 (lab phiên âm)
- [ ] L3 p.0, p.2 (Qwen)
- [ ] `nguyen-ke.nodes.json` (từ `analyze` hoặc gõ tay) + chạy `render_family_tree.py` → mở `tree/index.html`
- [ ] Không có diff trên `*.docx` / `pages/*.jpg`

**Verify:** cây có Điên–Nghiêm–Thái/Bằng/Châu (hoặc phiên âm lab tương đương); Word Hương MD5 không đổi.

---

## 9. Liên quan

- **Key / biến cần điền:** [mix_translate_yeu_cau.md](./mix_translate_yeu_cau.md)
- L2/L3 taxonomy: [labeling_and_hannom_ocr_plan.md](./labeling_and_hannom_ocr_plan.md) §3  
- Analyze API: `POST /api/family-tree/analyze` (`nlp_family_extractor/api.py`)
