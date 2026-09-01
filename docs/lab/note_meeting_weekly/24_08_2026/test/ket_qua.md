# Kết quả xử lý: Vũ Lâm Thần Quan Tế Văn

**Nguồn:** `note_meeting_weekly/24_08_2026/test/`  
**Ngày chạy:** 2026-08-25  
**Ảnh:** `image.png` (2 tờ mở, chữ Hán thẳng hàng dọc, đọc phải → trái)  
**Tham chiếu sẵn có:** `text.txt` (phiên âm + dịch nghĩa)

---

## 1. Phân tích

| Mục | Nội dung |
|-----|----------|
| Thể loại | **Tế văn** (văn khấn / văn tế) — mẫu điền chỗ trống (`某`) |
| Nhan đề | **羽林神官祭文** — *Vũ Lâm Thần Quan Tế Văn* |
| Dịp | Tiết **Trung Nguyên** (中元令節) — cúng cô hồn / Vu Lan |
| Đối tượng khấn | **Vũ Lâm Thần Quan** (quan thần coi việc âm giới / hộ tống lễ vật) |
| Mục đích | Xin thần thu nhận vàng mã, áo giấy… giao cho vong nhân; không để tà thần / ngoại quỷ cướp đoạt |
| Đặc điểm | Mẫu công thức: niên hiệu, can chi, địa danh, hiếu tử/tôn, húy tổ phụ/mẫu — không phải gia phả nhân vật cụ thể |
| Layout ảnh | Hai trang cạnh nhau; cột dọc; dấu tròn nhỏ cạnh chữ; cuối có dòng *右…敬書* |

**Liên quan pipeline tuần 24/08:** OCR → dịch âm (lab) → dịch nghĩa → (sau) fine-tune Qwen; tài liệu này dùng để **thử end-to-end** trên mẫu tế văn Hán, không phải scan gia phả.

---

## 2. Plan đã thực hiện

```text
1. Phân loại tài liệu (tế văn mẫu / Trung Nguyên)
2. OCR PP-OCRv6 medium (onnxruntime trên macOS)
3. Sắp cột phải → trái (RTL) vì Paddle đọc trái → phải theo bbox
4. Phiên âm lab Kim Hán Nôm trên chuỗi OCR-RTL
5. Hiệu đính chữ Hán (OCR lỗi) → phiên âm + dịch nghĩa chuẩn
6. Đối chiếu với text.txt
7. Ghi file kết quả (file này)
```

**Công cụ**

| Bước | Tool |
|------|------|
| OCR | `.venv-paddleocr/bin/python nlp_family_extractor/tools/ocr_paddleocr.py` |
| Model | `PP-OCRv6_medium` + engine `onnxruntime` |
| Phiên âm | API lab Kim Hán Nôm (`run_transliteration`) |
| Dịch nghĩa | Hiệu đính thủ công từ OCR + `text.txt` (chưa gọi Qwen trong lần chạy này) |

**Artifact**

| File | Mô tả |
|------|--------|
| `1.png` | Bản copy đánh số trang để chạy `ocr_paddleocr.py` |
| `paddleocr/1-paddleocr.json` | OCR thô + bbox + score |
| `paddleocr/1-paddleocr.txt` | OCR theo thứ tự Paddle (trái → phải) |
| `paddleocr/1-paddleocr-rtl.txt` | OCR sắp cột phải → trái |
| `paddleocr/1-phien-am-lab.txt` | Phiên âm lab trên OCR-RTL |
| `ket_qua.md` | Báo cáo tổng hợp (file này) |

---

## 3. OCR (PaddleOCR)

- **17 dòng**, mean_score ≈ **0.914**, ~3.9s  
- Chất lượng nhận dạng khá tốt trên chữ khắc in; vẫn lệch một số chữ gần nhau (干/千, 次/火, 馬/禍/碼, 魂/塊, 邪/形…).

### 3.1. OCR thô — sắp cột phải → trái (dùng để dịch)

```text
羽林官祭文
維
皇號干年歲火干支某月建干支越朔日干支某日
干支某省府縣總社村孝子某或孝孫某痛念亡靈
祖父或祖母字號某親父或親母字號某由於某年
月日時頓拋塵世倏赴陰司今適值中元令節謹以
金銀芙酒財禍器具席品之儀敢祗奏于
羽林神官玉陛下
第集
位前曰至公至正乃聖乃神雖陰陽之有隔亦感應
以能伸茲逢中元令節財碼敬陳方圓大小畫形化
虛為寔赤白青黃各色變假成真伏望收於此物交
與亡人執付泉臺用作行裝之寶叛回陰界以為美
具之新勿使形神借奪外鬼妄分俾眾子皆得全其
孝念而亡塊亦得頓其鴻恩
謹告
右羽林神官祭文敬書
```

### 3.2. Lỗi OCR đáng chú ý (cần hiệu đính)

| OCR | Sửa đề xuất | Ghi chú |
|-----|-------------|---------|
| 干年 | 千年 | Thiên niên |
| 歲火 | 歲次 | Tuế thứ |
| 芙酒 | 肴酒 | Lễ vật (ăn uống) |
| 財禍 / 財碼 | 財馬 | Vàng mã / ngựa giấy |
| 席品 | 庶品 | Các phẩm vật |
| 收於 | 收拾 | Thu thập |
| 叛回 | 收回 | Thu hồi |
| 以為美 + 具之新 | 以為露具之新 | Nối hai cột |
| 形神借奪 | 邪神侵奪 | Tà thần xâm đoạt |
| 亡塊 | 亡魂 | Vong hồn |
| 第集 | *(nhiễu / ký hiệu trang)* | Không thuộc thân văn |

---

## 4. Chữ Hán hiệu đính (đề xuất)

```text
羽林神官祭文
維
皇號千年歲次干支某月建干支越朔日干支某日
干支某省府縣總社村孝子某或孝孫某痛念亡靈
祖父或祖母字號某親父或親母字號某由於某年
月日時頓拋塵世倏赴陰司今適值中元令節謹以
金銀肴酒財馬器具庶品之儀敢祗奏于
羽林神官玉陛下
位前曰至公至正乃聖乃神雖陰陽之有隔亦感應
以能伸茲逢中元令節財馬敬陳方圓大小畫形化
虛為寔赤白青黃各色變假成真伏望收拾此物交
與亡人執付泉臺用作行裝之寶收回陰界以為
露具之新勿使邪神侵奪外鬼妄分俾眾子皆得全其
孝念而亡魂亦得頓其鴻恩
謹告
右羽林神官祭文敬書
```

---

## 5. Dịch âm (phiên âm Hán Việt)

### 5.1. Lab Kim Hán Nôm (trên OCR-RTL, **chưa** hiệu đính)

> Engine: lab phiên âm — phản ánh đúng lỗi OCR (ví dụ *can niên*, *vong khối*, *tài hoạ*).

```text
vũ lâm quan tế văn
duy
hoàng hiệu can niên tuế hoả can chi mỗ nguyệt kiến can chi việt sóc nhật can chi mỗ nhật
can chi mỗ tỉnh phủ huyện tổng xã thôn hiếu tử mỗ hoặc hiếu tôn mỗ thống niệm vong linh
tổ phụ hoặc tổ mẫu tự hiệu mỗ thân phụ hoặc thân mẫu tự hiệu mỗ do ư mỗ niên
nguyệt nhật thì đốn phao trần thế thúc phó âm ti kim thích trị trung nguyên lệnh tiết cẩn dĩ
kim ngân phù tửu tài hoạ khí cụ tịch phẩm chi nghi cảm chi tấu vu
vũ lâm thần quan ngọc bệ hạ
đệ tập
vị tiền viết chí công chí chính nãi thánh nãi thần tuy âm dương chi hữu cách diệc cảm ứng
dĩ năng thân tư phùng trung nguyên lệnh tiết tài mã kính trần phương viên đại tiểu hoạ hình hoá
hư vi tẩm xích bạch thanh hoàng các sắc biến giả thành chân phục vọng thu ư thử vật giao
dữ vong nhân chấp phó tuyền đài dụng tác hành trang chi bảo phản hồi âm giới dĩ vi mỹ
cụ chi tân vật sử hình thần tá đoạt ngoại quỷ vọng phân tỉ chúng tử giai đắc toàn kì
hiếu niệm nhi vong khối diệc đắc đốn kì hồng ân
cẩn cáo
hữu vũ lâm thần quan tế văn kính thư
```

### 5.2. Phiên âm sau hiệu đính (chuẩn dùng)

```text
Vũ Lâm Thần Quan Tế Văn
Duy
Hoàng hiệu Thiên niên tuế thứ Can Chi, mỗ nguyệt kiến Can Chi, việt sóc nhật Can Chi, mỗ nhật
Can Chi mỗ tỉnh phủ huyện tổng xã thôn, hiếu tử mỗ hoặc hiếu tôn mỗ, thống niệm vong linh
tổ phụ hoặc tổ mẫu tự hiệu mỗ, thân phụ hoặc thân mẫu tự hiệu mỗ. Do ư mỗ niên
nguyệt nhật thì đốn phao trần thế, thúc phó âm ti. Kim thích trị Trung Nguyên lệnh tiết, cẩn dĩ
kim ngân, hào tửu, tài mã, khí cụ, thứ phẩm chi nghi, cảm chi tấu vu
Vũ Lâm Thần Quan ngọc bệ hạ.
Vị tiền viết: Chí công chí chính, nãi thánh nãi thần. Tuy âm dương chi hữu cách, diệc cảm ứng
dĩ năng thân. Tư phùng Trung Nguyên lệnh tiết, tài mã kính trần. Phương viên đại tiểu họa hình, hóa
hư vi thực; xích bạch thanh hoàng các sắc, biến giả thành chân. Phục vọng thu thập thử vật, giao
dữ vong nhân, chấp phó Tuyền Đài, dụng tác hành trang chi bảo; thu hồi âm giới dĩ vi
lộ cụ chi tân. Vật sử tà thần xâm đoạt, ngoại quỷ vọng phân. Tỷ chúng tử giai đắc toàn kỳ
hiếu niệm, nhi vong hồn diệc đắc đốn kỳ hồng ân.
Cẩn cáo.
Hữu Vũ Lâm Thần Quan Tế Văn kính thư.
```

---

## 6. Dịch nghĩa tiếng Việt

**Văn tế Quan Thần Vũ Lâm**

Kính cáo.

Nay thuộc niên hiệu [Thiên niên], năm Can Chi […], tháng […], ngày sóc Can Chi […], ngày […].  
Tại tỉnh / phủ / huyện / tổng / xã / thôn […], hiếu tử [tên] hoặc hiếu tôn [tên], thành kính tưởng nhớ vong linh ông / bà [tự hiệu], cha / mẹ [tự hiệu]. Vì vào năm… tháng… ngày… giờ… đã từ trần, linh hồn về âm ty. Nay đúng tiết Trung Nguyên, kính cẩn dâng lễ vật gồm vàng bạc, rượu thịt, vàng mã, đồ dùng và các phẩm vật, kính tấu lên dưới bệ ngọc Quan Thần Vũ Lâm.

Xin khấn rằng: Ngài chí công chí chính, vừa thánh vừa thần. Dẫu âm dương cách trở, vẫn cảm ứng thấu suốt. Nay gặp tiết Trung Nguyên, kính dâng tài mã. Hình vẽ tròn vuông, lớn nhỏ — xin hóa hư thành thực; các sắc đỏ, trắng, xanh, vàng — xin biến giả thành chân. Cúi xin thu nhận vật này, trao cho người đã khuất, mang tới Tuyền Đài làm hành trang; thu về âm giới làm lộ phí mới. Xin đừng để tà thần cướp đoạt, ngoại quỷ tranh giành. Ngõ hầu con cháu trọn lòng hiếu, vong hồn cũng được nhờ hồng ân lớn.

Kính cáo.  
Bên phải: kính ghi bài *Văn tế Quan Thần Vũ Lâm*.

---

## 7. Đối chiếu với `text.txt`

| Điểm | `text.txt` | OCR / ảnh lần này |
|------|------------|-------------------|
| Nhan đề | Vũ Lâm Thần Quan Tế Văn | Khớp (OCR thiếu chữ 神 ở dòng đầu: 羽林官祭文) |
| Người khấn | «Lý tử» | Ảnh/OCR: **孝子** (hiếu tử) — nên theo OCR |
| Lễ vật | kim ngân **minh y**, tài mã, **khố** phẩm | OCR gần: **肴酒**, tài mã, **庶** phẩm — biến thể công thức |
| «đốn vật / đốn phao» | đốn vật trần thế | OCR: **頓拋** (đốn phao) trần thế |
| Kết | đắc **lại** kỳ hồng ân | OCR/cổ văn thường: **頓** kỳ hồng ân |

Nhìn chung `text.txt` đã là bản phiên âm + dịch nghĩa tốt; lần chạy này **xác nhận** nội dung ảnh và bổ sung chuỗi OCR + phiên âm lab để A/B.

---

## 8. Kết luận & bước tiếp

1. **OCR ổn** cho mẫu chữ thẳng hàng dọc; bắt buộc **sắp cột RTL** trước khi dịch.  
2. **Lab phiên âm** chạy được nhưng **truyền lỗi OCR** → cần bước hiệu đính chữ Hán (hoặc post-edit) trước khi đưa vào dataset fine-tune.  
3. Tài liệu là **mẫu tế văn**, không sinh cây gia phả; hữu ích cho domain “hành chính / nghi lễ” khi fine-tune dịch nghĩa (Qwen).  
4. Gợi ý tiếp: tách 2 trang ảnh → OCR từng trang; thử thêm Google Vision / lab OCR để voting; đưa cặp (Hán hiệu đính, dịch nghĩa §6) vào dataset dịch nghĩa gia phả–nghi lễ.
