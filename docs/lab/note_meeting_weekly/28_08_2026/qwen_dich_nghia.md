# Qwen dịch nghĩa — một trang kế ước

> 2026-08-28 · **trạng thái: BLOCKED** (không phải output model)

## Yêu cầu tuần (P0)

Một trang **dịch nghĩa Qwen** trên Hán đã hiệu đính, so Ô.cố. Ưu tiên kế ước Hương, không tế văn. **Không** fine-tune 37B.

## Quan sát

| Điều kiện | Hiện trạng |
|-----------|------------|
| API Qwen / DashScope / tương đương trong repo | **Không** — `nlp_family_extractor/.env.example` chỉ `HANNOM_*` |
| Hán hiệu đính 15 trang Hương | **Không** — lab phiên âm 0/15 `access_denied` |
| Gold dịch sát chữ | **Không** — Ô.cố là Quốc ngữ paraphrase; §5 lệch tên |

## Kết luận

Không gọi Qwen tuần này. File này là bằng chứng đã kiểm tra điều kiện, không phải bản dịch giả.

Khi có API + 1 trang Hán đã sửa (đề xuất **p.9** 阮有朋→阮玉珠, OCR sạch hơn p.0 thảo): ghi `qwen_page09.md` cạnh OCR và đoạn Ô.cố §2.

## Không thay bằng

- Dịch tay gọi là Qwen.  
- Chạy Qwen trên OCR thô p.0 (thảo, chưa hiệu đính).  
- Fine-tune.

Tế văn 24/08 đã có dịch tay trong `24_08_2026/test/ket_qua.md` — giữ làm mẫu thể loại khác, không đếm là P0 kế ước.
