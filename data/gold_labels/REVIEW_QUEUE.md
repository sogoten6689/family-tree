# Gold Review Queue — stratified sample

> Generated: 2026-08-08T19:44:15.696389+00:00 · Protocol: stratified_gold_v1

## Tóm tắt

| Stratum | Số doc | Mục đích |
|---------|--------|----------|
| S1 | 8 | Relation-rich — review trước |
| S2 | 7 | Medium |
| S3 | 5 | Hard cases |
| S4 | 5 | **Held-out test — không sửa sau khi chốt** |
| Double κ | 5 | 2 annotator |

## Thứ tự review (ưu tiên)

| # | tree_id | Stratum | Split | Relations | Dòng họ | Double κ |
|---|---------|---------|-------|-----------|---------|----------|
| 1 | **122** | S1 | train | 32 | Họ Võ tại Tây Hồ - Diễn Phong - Diễ - Ng |  |
| 2 | **1684** | S1 | train | 15 | Ngô - Tây Ninh |  |
| 3 | **367** | S1 | train | 13 | Trần Phước (陳 福 - 富霑) - Quảng Nam |  |
| 4 | **321** | S1 | train | 9 | Thái - Đồng Tháp |  |
| 5 | **310** | S1 | train | 8 | Nguyễn Văn Lai Xá - Hà Tây |  |
| 6 | **1630** | S1 | train | 7 | HỌ - Nam Định |  |
| 7 | **277** | S1 | train | 6 | NGUYỄN CẢNH - Nghệ An |  |
| 8 | **1508** | S1 | train | 6 | NGUYỄN VIẾT - Thanh Hóa |  |
| 9 | **1622** | S4 | test | 5 | HOÀNG - Hải Dương | ✓ |
| 10 | **1454** | S4 | test | 0 | Doãn 尹 (nhánh Doãn Uẩn, Doãn Khuê) - Thá | ✓ |
| 11 | **544** | S4 | test | 0 | Nguyễn Đình - Hà Tĩnh | ✓ |
| 12 | **1813** | S4 | test | 0 | Họ Thân Làng Khê Thượng - Hà Tây | ✓ |
| 13 | **2346** | S4 | test | 0 | NGUYỄN VĂN - HOÀ VANG - Đà Nẵng | ✓ |
| 14 | **1537** | S2 | train | 3 | Nguyễn Văn - Quảng Nam |  |
| 15 | **1550** | S2 | train | 3 | Nguyễn Tộc Tứ Phái - Quảng Nam |  |
| 16 | **1546** | S2 | train | 3 | Văn Đình - Phái Nhì - Chi Nhất - Thừa Th |  |
| 17 | **255** | S2 | train | 2 | NGUYỄN XUYẾN - Quảng Ngãi |  |
| 18 | **396** | S2 | train | 2 | Nguyễn Phúc - Hải Dương |  |
| 19 | **1716** | S2 | train | 1 | Nguyễn văn- (Chi 3) - Hà Nam |  |
| 20 | **423** | S2 | train | 1 | TẠ ÐĂNG - Hà Tây |  |
| 21 | **617** | S3 | train | 0 | Nguyen - Hà Nam |  |
| 22 | **656** | S3 | train | 0 | Lê - Bình Định |  |
| 23 | **844** | S3 | train | 0 | Trần Huy - Hưng Yên |  |
| 24 | **1107** | S3 | train | 0 | ĐỖ Đức - Hải Phòng |  |
| 25 | **2339** | S3 | train | 0 | Phùng - Hưng Yên |  |

## Held-out test (S4) — giữ nguyên sau review

1622, 1454, 544, 1813, 2346

## Double annotation

544, 1454, 1622, 1813, 2346

## Hướng dẫn

1. Mở Label Studio project 3 → filter/search `tree_id`
2. Sửa pre-annotation Gemini/auto-gold theo [HUONG_DAN_GAN_NHAN.md](../label_studio_pipeline/HUONG_DAN_GAN_NHAN.md)
3. **Submit** (không chỉ Save draft) — cần `completed_by` hoặc `lead_time > 0`
4. Export: `python -m label_studio_pipeline.export_ls_gold`
