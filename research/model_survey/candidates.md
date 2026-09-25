# T1 — Danh sách ứng viên mô hình/dataset gia phả Hán (Trung Quốc)

> Kết quả T1 của [`../../docs/planning/chinese_genealogy_model_hunt_plan.md`](../../docs/planning/chinese_genealogy_model_hunt_plan.md).
> Thực hiện: agent nghiên cứu Claude, phiên 25/9/2026. Báo cáo đầy đủ (fact/inference/confidence): [`BAO_CAO_DANH_GIA_CHAT_MODELS.md`](./BAO_CAO_DANH_GIA_CHAT_MODELS.md).

**Từ khoá đã dùng:** "家谱 NER 知识图谱", "GuwenBERT genealogy", "OCR vertical classical Chinese old book scans", "族谱数字化 知识图谱", "classical-chinese GitHub topics", "kinship extraction classical Chinese", "genealogy chart generation NLP".

**Kết luận khảo sát quan trọng nhất:** không tìm thấy mô hình/dataset nào giải quyết trực tiếp bài toán "gia phả Hán TQ → cây gia phả có cấu trúc" — đây là fact từ tìm kiếm có hệ thống, không phải do tìm chưa đủ kỹ (xem báo cáo đầy đủ §1, §5.2 mục 4).

## (a) OCR cổ văn Hán / dọc

| Tên | Link | Có code chạy được? | License | Ghi chú |
|---|---|---|---|---|
| **CHAT_models** ✅ đã chạy thử (T2) | https://github.com/colibrisson/CHAT_models | Có — weight nằm trực tiếp trong git repo | CC BY-NC 4.0 | Kraken seg+rec, huấn luyện 1.7M dòng Hán cổ TQ 10th–20th c. |
| CnOCR | https://github.com/breezedeus/cnocr | Có | MIT lõi (một số model phái sinh có điều kiện) | OCR TQ tổng quát, không chuyên Hán cổ |
| chinese-pdf-ocr-toolkit | https://github.com/MH-API/chinese-pdf-ocr-toolkit | Có, nhưng cần VLM API key ngoài | Chưa kiểm tra | Không chạy độc lập offline hoàn toàn |
| sanskrit-ocr (tham khảo kiến trúc) | https://github.com/ihdia/sanskrit-ocr | — | — | Không phải tiếng Trung, chỉ tham khảo |

## (b) NER cổ văn — tên người / chức quan / quan hệ thân tộc

| Tên | Link | Có code chạy được **trong sandbox này**? | License |
|---|---|---|---|
| guwen-ner (GuwenBERT) | https://github.com/Ethan-yt/guwen-models (weight: https://huggingface.co/ethanyt/guwen-ner) | ❌ Không — HuggingFace Hub bị chặn egress proxy (403 connect_rejected, org policy) | Apache-2.0 |
| GuwenBERT base/large | https://github.com/Ethan-yt/guwenbert | ❌ Không — HF Hub bị chặn | Apache-2.0 |
| SikuBERT/SikuRoBERTa | https://huggingface.co/SIKU-BERT/sikubert | ❌ Không — HF Hub bị chặn | Chưa rõ |
| Jiayan (甲言) | https://github.com/jiaeyan/Jiayan | ❌ Không — weight host Google Drive/Baidu NetDisk, bị chặn | MIT |
| UD-Kanbun | https://github.com/KoichiYasuoka/UD-Kanbun | Chưa thử | Chưa kiểm tra |

**→ Loại khỏi T2** (không có code chạy được trong môi trường này, không phải vì chất lượng kém): guwen-ner, GuwenBERT, SikuBERT, Jiayan. Lý do là hạ tầng (proxy egress chặn HF/ModelScope/Google Drive/Zenodo), không phải lỗi của các repo này — cần thử lại khi có môi trường mạng khác.

## (c) Trích xuất quan hệ / knowledge graph nhân vật

| Tên | Link | Ghi chú | License |
|---|---|---|---|
| PersonRelationKnowledgeGraph | https://github.com/liuhuanyong/PersonRelationKnowledgeGraph | KG quan hệ nhân vật tiếng Trung **hiện đại**, không phải cổ văn/gia phả | Không ghi rõ (rủi ro pháp lý) |
| PersonGraphDataSet | https://github.com/liuhuanyong/PersonGraphDataSet | Dataset ~100k cặp quan hệ, tiếng Trung hiện đại | Không ghi rõ |
| DeepKE (zjunlp) | https://github.com/zjunlp/DeepKE | Toolkit NER/RE tổng quát, nhưng cần tải pretrained model từ HF | MIT (phụ thuộc HF) |

## (d) Công cụ quản lý cây gia phả (không phải NLP — chỉ tham khảo schema)

- https://github.com/snssv/jiapu — schema cha/con/vợ-chồng/con nuôi, không phải NLP.
- https://github.com/KirigiriSuzumiya/family-tree — nhận diện khuôn mặt + gia phả, không liên quan xử lý văn bản.

## Shortlist cho T2 (loại khỏi HF/Google Drive vì lý do hạ tầng, không phải chất lượng)

1. ~~guwen-ner/GuwenBERT~~ — lý thuyết phù hợp nhất nhưng không tải được.
2. ~~Jiayan~~ — MIT, đầy đủ toolkit nhưng không tải được.
3. **CHAT_models** — ứng viên duy nhất có weight nằm ngay trong git repo → **chọn chạy thử ở T2**.
