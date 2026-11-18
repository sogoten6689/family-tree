# Kiểm thử web nhóm `chua-giao` — 18/11/2026

Phạm vi: chỉ đọc (GET) trên https://giapha.kimtudien.com.vn, không sửa code, không ghi VPS, không gọi dịch vụ trả phí.
Phương pháp: tải toàn bộ `bo`, 20 TSV và **cả 726 trang** `/trang/<NNN>` của 10 cuốn rồi đối chiếu bằng script; duyệt giao diện bằng trình duyệt trong app (khổ desktop và 375×812).

## Tóm tắt

| Mục | Kết quả |
|---|---|
| 1. Số liệu `bo` | **ĐẠT** |
| 2. TSV sạch | **ĐẠT một phần** — 1 lỗi (còn "(không chắc)" ở bộ đã soát) |
| 3. Lỗi vote cũ đã gỡ | **ĐẠT** (kèm 1 điểm cần đối chiếu ảnh) |
| 4. Endpoint `/trang` | `cap` **ĐẠT**; `am` phủ **ĐẠT**; độ đúng âm **LỖI** (chữ nhiều âm) |
| 5. Thẻ "Xem trang song song" | **ĐẠT** (ảnh, bảng, hai chiều, nhãn, điện thoại) |
| 6. Lỗi giao diện/console | **ĐẠT** — console không lỗi, mọi request 200 |

## 1. Số liệu `bo` — ĐẠT
- tq-678: sua_vote 131 / chờ 12 / dich_lai 126 ✔; tq-693: 66/16/65 ✔; tq-696: 106/23/94 ✔; tq-859: 4/5/4 ✔.
- `dich_lai_con = 0` ở cả 10 cuốn ✔.
- Số cặp mang cờ `sua_chu` ở `/trang` = `dich_lai` (126/65/94/4), khớp.

## 2. TSV sạch
Đạt: mỗi dòng đúng 2 cột, không dòng rỗng, không vế rỗng, không trùng cặp, vế Việt không lẫn chữ Hán; số dòng TSV = `bo.may` / `bo.da_soat` ở cả 10 cuốn (ví dụ 678: 4529; 693: 2074; 696: 2025; 859: 1328 máy + 496 đã soát).

**LỖI L1 (thấp–vừa)** — còn ghi chú máy dịch "(không chắc)" trong **TSV đã soát** (`da-soat.tsv`):
- tq-950: 65 dòng (vd dòng 8 "Đời thứ 1: Vĩ Thập Nhất, … sau chuyển về Minh Châu (không chắc)", dòng 15).
- tq-859: 45 dòng (vd dòng 9, 15, 26 "Phái Hữu Nhân (Sắc ban) (không chắc)").
- tq-347: 1 dòng (dòng 90 "…năm sinh năm mất chờ khảo cứu…" chứa "(không chắc)").
- Mong đợi: không còn. Ghi chú: các bộ này là bản sinh viên nộp, nên có thể là ý muốn giữ; cần anh Lâm quyết định có lọc hay không. Bộ `may.tsv` thì sạch "(không chắc)" / "(bản gốc ghi…)".
- Còn lại hiếm: tq-693 dòng 593 và tq-696 dòng 33 có "(chú thích: …)" / "(nghiệp thiêu)" — là ghi chú trong bản dịch, không phải ghi chú máy; tq-950 dòng 1586 "(chú thích nhỏ)". Chỉ ghi nhận.
- "[?]" (chữ mờ không đọc được) xuất hiện cả ở vế Hán lẫn vế Việt (678: 158 dòng, 696: 53, 859: 57…): ký hiệu hợp lệ, không tính lỗi.

## 3. Lỗi vote cũ — ĐẠT
- Không còn chuỗi 方历 ở bất kỳ cuốn nào (0).
- 万历 chỉ còn ở tq-678 (11 dòng) — là chữ giản thể đúng của bản gốc, không phải thay sai.
- 妣 còn nhiều (678: 199, 693: 240, 696: 78); 殁 còn 405/9/9; 姚 ở 678 chỉ 1 lần (姚家鋪, chữ gốc); 園 ở 678 chỉ 1 lần (花園 hợp lệ), 696 là 大園, 葵園 hợp lệ.
- tq-693 có 15 chữ 姚 phần lớn là họ "姚氏" (hợp lệ).
- 任屋 có 18 (693) và 9 (696) dòng, Việt "Nhậm Ốc" ✔.
- **Cần đối chiếu ảnh (chưa kết luận lỗi):** 住屋 còn 11 dòng ở tq-693 và 16 dòng ở tq-696, đều dịch "nhà ở" (vd 693 dòng 882 "葬住屋後山" → "táng tại núi sau nhà ở"). Cách dùng khớp nghĩa "nhà ở" nên nhiều khả năng là chữ gốc; nhưng cặp cùng ngữ cảnh với "任屋後山" (693 dòng 691) nên nên đối chiếu vài dòng với ảnh để chắc 住/任 không lẫn.

## 4. Endpoint `/trang/<NNN>`
- **`cap` khớp TSV: ĐẠT.** Đủ 726 trang đều tải được; tập cặp (hán, việt) của mọi trang gộp lại = đúng tập dòng TSV (may + da_soat) ở cả 10 cuốn, 0 cặp lệch (tq-859: 1824 = 1328 + 496).
- **Phủ âm: ĐẠT.** Tổng 152.000 chữ Hán, thiếu âm 220 (≈0,15%), toàn chữ hiếm/dị thể. Mỗi cuốn: pham-kinh-vy 22/2879, tq-1035 6/4909, tq-347 6/2218 (塆 ×6), tq-588 19/7346, tq-678 34/29291 (垸 ×5, 堖 ×3…), tq-693 32/28514 (禑 ×3, 岽 ×3…), tq-696 41/27566 (栻, 炘 ×5; 酐 ×4…), tq-859 11/19338, tq-950 49/29240 (峘 ×5, 釪 ×3…), tq-978 0/1453. Mức độ: thấp.
- Trang `cap` rỗng (không phải lỗi, vì trang ảnh bìa/trống): pham-kinh-vy 12 trang chẵn 002–022 và 004…, tq-1035 9 trang, tq-347 trang 012, tq-588 4 trang (001, 002, 044, 045), tq-678 084, tq-693 086, tq-696 082, tq-859 002 và 127, tq-950 001/077/105, tq-978 002/024/041. Em khuyên anh Lâm xem nhanh pham-kinh-vy (12/23 trang rỗng): nếu đó là trang sách có chữ thì thiếu dữ liệu.
- Nhẹ: `/trang/999` (trang không tồn tại) vẫn trả HTTP 200 thay vì 404.

### LỖI L2 (vừa) — âm Hán Việt của chữ nhiều âm hay sai nghĩa
Tài liệu trên giao diện nói "chọn âm hay gặp trong bản dịch của kho", nhưng dữ liệu cho thấy âm chọn là âm đầu của từ điển, không theo ngữ cảnh. Các chữ thường gặp trong gia phả bị chọn sai gần như mọi lần:

| Chữ | Âm chọn | Số lần | Âm đúng thường gặp | Ví dụ |
|---|---|---|---|---|
| 卒 | tuất | 1255 | tốt (mất) | tq-678 tr.003 dòng 3 "娶卒甲方…" → "thú **tuất** giáp…" |
| 子 | tý | 3384 (100%) | tử (con) | tq-678 tr.003 dòng 7 "生子二" → "sinh **tý** nhị" |
| 行 | hàng | 535 (100%) | hành (thi hành, hành nhân, đức hạnh); hàng chỉ đúng khi nói thứ bậc | pham-kinh-vy "奉施行", tq-950 "行人司" (124 dòng mà vế Việt có "Hành/hạnh") |
| 長 | trưởng | 712 (100%) | trường (地名 長冲 "Trường Xung", 長虹堡 "Trường Hồng Bảo") | 93 dòng mà vế Việt có "Trường" |
| 重 | trọng | 58 | trùng (重修, 重險, 重圍) | 4 dòng vế Việt có "trùng" |
| 适 | quát | 142 | thích (giản thể của 適, vì 適 ở dữ liệu đã là "thích") | tq-678 tr.003 dòng 9 "长适刘正伦" → "trưởng **quát**" |
| 妻 | thế | 30 | thê | |
| 司 | ti | 46 | tư (tuỳ) | |

Các chữ khác soát mẫu ~40 chữ đúng (生 sinh, 譜 phả, 為 vi, 氏 thị, 娶 thú, 葬 táng, 殁 một, 母 mẫu…). Chữ nhiều âm có cờ `k` (các âm khác) hiện đủ để tra, nên đây là lỗi chất lượng chứ không làm hỏng giao diện. Tổng cộng 695 chữ có `k` mà âm chọn không xuất hiện trong vế Việt nhưng một âm khác có. Gợi ý: lấy âm theo vế Việt của cặp (nếu có trong `k`), và đặt bảng ưu tiên cho 卒子行長重适妻.

## 5. Giao diện "Xem trang song song" — ĐẠT
- Chỉ tq-347 có khung (11 trang). Ảnh hiện, chú thích "Định vị 113/113 chữ (100%)", bảng Hán | Âm Hán Việt | Nghĩa hiện đủ, kèm nhãn "đã soát".
- Bấm dòng bảng → dòng sáng; bấm khung trên ảnh → khung điền màu xanh đậm và dòng tương ứng sáng (xác nhận bằng DOM: dòng 54 đổi nền khi bấm khung thứ 60; trước đó khung `fill=none/1px`, sau đó fill xanh 0,28/2px).
- 9 cuốn còn lại hiện đúng "Trang này chưa có khung chữ; chỉ hiện ảnh gốc." (theo dự kiến, không tính lỗi); bảng vẫn hiện.
- Nhãn "sửa chữ" và "dịch lại" hiện trên cặp đã sửa: tq-678 trang 003 dòng 3 "娶卒甲方文除女" có cả hai nhãn ✔.
- Khổ 375×812: không cuộn ngang (scrollWidth = 375), ảnh co theo, bảng gọn, chữ gạch chấm hiện; dùng được.
- Quan sát nhẹ: trang đếm "1 / 12" (tq-347), "/ 84" (tq-678) tính cả trang ảnh không có chữ (trang cuối rỗng). Ở tq-678 ô thống kê đầu trang ghi "Cặp 0 / Đúng định dạng 0" (do chưa có file sinh viên nộp) trong khi bộ sạch có 4529 máy; có thể gây hiểu nhầm nhưng đúng theo thiết kế. Khi cửa sổ rộng 800px, thanh bên trái đè lên cột đầu của bảng cuốn (ảnh chụp lúc mở danh sách cuốn): nhỏ, chưa lặp lại ở 1024px.
- Nhập số trang vào ô rồi Enter chưa chuyển trang trong lần thử ở tq-678 (ô vẫn "1"); bấm nút "›" thì chuyển bình thường. Chưa chắc là lỗi (có thể ô chỉ nhận khi blur); mức thấp, nên xem lại.

## 6. Console / chuyển trang, chuyển cuốn — ĐẠT
Mở lần lượt tq-347 → tq-678 → tq-347 → tq-588, chuyển trang, chuyển tab: console không có lỗi (chỉ log thông tin i18next); toàn bộ request `/api/public/doi-chieu/...` (cuốn, trang, ảnh) trả 200. Ảnh `/anh/003` trả 200 ở cả 10 cuốn (170 KB–1,8 MB).

## Việc cần anh Lâm quyết định
1. L2 (âm Hán Việt sai nghĩa với 卒子行長重适): nên sửa trước khi nộp thầy vì lỗi lặp nhiều và dễ thấy (子 "tý" 3384 lần).
2. L1: có lọc "(không chắc)" ở `da-soat.tsv` của tq-950, tq-859 (và 1 dòng tq-347) hay không.
3. Soát ảnh vài dòng 住屋/任屋 ở tq-693, tq-696.
4. Xem lại 12 trang rỗng của pham-kinh-vy.
