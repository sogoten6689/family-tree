# Xếp hạng tốt cho thống kê — kém cho tra cứu

A–Y / 01–25: tốt về biểu đồ (A = nhiều nhất), kém tra cứu (không nhớ A = Nguyễn).  
Chữ đầu họ: tốt tra cứu **nếu không đụng**, không nói được thứ hạng.

## Chỉ chữ cái đầu — không thành

Trong 25 họ, chỉ 3 họ không đụng chữ đầu: Bùi, Dương, Mai.

```text
N  Nguyễn / Ngô
T  Trần / Trương / Trịnh
L  Lê / Lương / Lưu / Lâm
P  Phạm / Phan
V  Vũ / Võ
H  Hoàng / Huỳnh / Hà / Hồ
Đ  Đỗ / Đặng / Đoàn / Đinh / Đào
```

Đó là lý do list 9 họ một chữ (D/G/H/N/P/T) không mở rộng được.

## Đề xuất — hai lớp, một ID

Tách xếp hạng và tra cứu. Không nhét cả hai vào một chữ.

```text
ID nói / mở file:   F - NG - 001
Hạng (field riêng): 01 … 25 | Z     (chỉ thống kê / biểu đồ)
```

`F-NG-001` đọc được là Nguyễn. `hang=01` = phổ biến nhất.  
`F-A-001` giữ thứ hạng nhưng mất tra cứu.

Mã tra cứu 2 chữ (chữ đầu khi được; thêm chữ 2 khi đụng):

| Hạng | Tra cứu | Họ | Hạng | Tra cứu | Họ |
|-----:|---------|-----|-----:|---------|-----|
| 01 | NG | Nguyễn | 14 | DN | Đoàn |
| 02 | TR | Trần | 15 | DI | Đinh |
| 03 | LE | Lê | 16 | VO | Võ |
| 04 | PH | Phạm | 17 | DU | Dương |
| 05 | VU | Vũ | 18 | MA | Mai |
| 06 | PN | Phan | 19 | DA | Đào |
| 07 | HA | Hoàng | 20 | HN | Hà |
| 08 | BU | Bùi | 21 | LG | Lương |
| 09 | GO | Ngô | 22 | TI | Trịnh |
| 10 | DO | Đỗ | 23 | LU | Lưu |
| 11 | DG | Đặng | 24 | LM | Lâm |
| 12 | TU | Trương | 25 | HO | Hồ |
| 13 | HY | Huỳnh | — | ZZ | còn lại |

GO = Ngô (N đã dùng Nguyễn; G như nGô).  
PN = Phan (P đã dùng Phạm).  
HN = Hà (HA đã dùng Hoàng).
