# Task — Cài đặt & chạy demo XunziLLM (Ancient Chinese LLM)

> **Ngày tạo:** 2026-09-28 · **Người thực thi dự kiến:** Cursor Agent/Composer (máy có thể truy cập ModelScope/HuggingFace — **không chạy trong Claude Code cloud sandbox**, đã xác nhận 2 lần độc lập là bị chặn egress tới cả 2 host này)
> **SSOT / nguồn liên quan:**
> - `docs/lab/note_meeting_weekly/21_09_2026/21_09_2026.md` §5 + `phan_tich_hop_21_09_2026.md` §3 (mô tả gốc về XunziLLM)
> - `docs/thesis/dinh_huong_nghien_cuu_theo_thay_2026-09.md` §3.3 (vai trò XunziLLM trong đề tài: ứng viên L1 dịch nghĩa + L2 trích xuất thực thể)
> - Nhánh song song `origin/claude/meeting-project-evaluation-eui68s`: `docs/planning/chinese_genealogy_model_hunt_plan.md` (task T1–T3 gốc, đã chạy Jiayan/guwen-ner/CHAT_models — **chưa có trên nhánh hiện tại**, xem §0 dưới)
> - `.cursor/rules/gia-pha-only-analysis.mdc` (phạm vi dữ liệu test), `.cursor/rules/free-only-visualization.mdc` (tinh thần license-gate, áp dụng tương tự cho model NLP)

---

## 0. Bối cảnh — vì sao giao cho Cursor, không phải Claude Code cloud

Đã thử trực tiếp trong Claude Code cloud session (2 lần, 2 session độc lập, 2026-09-28):

```
HuggingFace:  CONNECT tunnel failed, 403
ModelScope:   CONNECT tunnel failed, 403
```

XunziLLM host chính trên **ModelScope**; đây là hạn chế hạ tầng của sandbox, không phải vấn đề model. Cursor chạy trên máy có network bình thường nên **có thể tải/chạy được**.

**Việc khác không nằm trên nhánh hiện tại (`claude/busy-planck-bb0lwd`):** `research/model_survey/` và `docs/planning/chinese_genealogy_model_hunt_plan.md` đang nằm trên nhánh `claude/meeting-project-evaluation-eui68s` (một phiên Claude khác). Nếu Cursor làm việc trên checkout của nhánh đó, **đọc trực tiếp** 2 file này trước khi bắt đầu (đã có sẵn quy trình T1–T3 + bảng ứng viên khác để so sánh). Nếu Cursor làm trên nhánh này, tạo `research/model_survey/` mới ở đây và ghi rõ trong file kết quả rằng nhánh kia đã khảo sát các ứng viên khác (Jiayan, guwen-ner, CHAT_models) — không lặp lại việc đó, chỉ tập trung XunziLLM.

---

## 1. Mục tiêu

Cài đặt và chạy demo **XunziLLM** thật (không chỉ đọc README), đo trên câu mẫu gia phả, để trả lời 2 câu hỏi treo trong `dinh_huong_nghien_cuu_theo_thay_2026-09.md` §3.3:

1. **License thực tế là gì?** (README công khai lúc khảo sát 21/9–28/9 không ghi rõ) — có cho phép dùng trong luận văn (nghiên cứu, phi thương mại) không, có điều kiện gì (ghi công, chia sẻ tương tự, cấm redistribute weight...)?
2. **Chất lượng trích xuất thực tế trên câu gia phả Hán** — đặc biệt trên **chữ phồn thể** (đúng dạng Hán-Nôm Việt Nam sẽ dùng) — có tốt hơn `guwen-ner` không? (guwen-ner đã đo được 0/4 thực thể trên phồn thể, xem §3.3 của file định hướng.)

## 2. Giả thuyết (phải kiểm chứng bằng chạy thật, không suy đoán từ README)

- **H1** — XunziLLM nhận diện được thực thể người/chức quan trên câu gia phả phồn thể tốt hơn rõ rệt so với guwen-ner (which scored 0/4).
  - *Dự đoán nếu đúng:* trên câu test chuẩn (§4 dưới), XunziLLM trả về ≥3/4 thực thể đúng ở bản phồn thể (không cần ép giản thể).
  - *Dự đoán nếu sai:* XunziLLM cũng nhạy phồn/giản thể tương tự guwen-ner, hoặc miss phần lớn thực thể.
- **H2 (null)** — Model quá nặng (7B) để chạy được trên máy Cursor hiện có (thiếu GPU/RAM), hoặc license chặn hẳn việc dùng trong luận văn → không dùng được dù chất lượng tốt.
  - Đây là kết luận hợp lệ nếu xảy ra thật — **ghi lại nguyên văn lỗi/điều khoản license**, không bỏ qua bước.

## 3. Việc cần làm (theo thứ tự, dừng nếu bước trước fail)

### Bước 0 — License-gate (làm TRƯỚC KHI cài, không phải sau khi chạy thử xong)

- Đọc `LICENSE` (nếu có) trong repo GitHub `Xunzi-LLM-of-Chinese-classics/XunziALLM` và trang model card trên ModelScope.
- Ghi rõ: loại license, điều kiện thương mại/phi thương mại, điều kiện ghi công, điều kiện phân phối lại weight/output.
- **Bối cảnh đã xác nhận với người dùng (2026-09-28): đề tài chỉ phục vụ nghiên cứu khoa học/luận văn, không thương mại** — nên license non-commercial (kiểu CC BY-NC) KHÔNG phải rào cản. Chỉ dừng lại hỏi người dùng nếu license có điều kiện khác thường (ví dụ cấm hẳn cả nghiên cứu, yêu cầu xin phép trước, hoặc không rõ ràng đến mức rủi ro pháp lý thật).

### Bước 1 — Cài đặt

```bash
# Thử web demo trước nếu có (nhanh, không cần cài):
# https://xunziallm.njau.edu.cn/  — kiểm tra site còn hoạt động, ghi lại có/không dùng được

# Nếu cần tự host:
git clone https://github.com/Xunzi-LLM-of-Chinese-classics/XunziALLM research/model_survey/trial/XunziALLM
cd research/model_survey/trial/XunziALLM
# Theo README: model thường tải qua ModelScope SDK (modelscope.cn), không phải HuggingFace
python -m venv .venv && source .venv/bin/activate   # venv riêng, KHÔNG đụng venv chính của nlp_family_extractor
pip install -r requirements.txt   # hoặc theo hướng dẫn repo
```

- Nếu thiếu GPU/RAM (model ~7B) khiến không load được: ghi lại nguyên văn lỗi, thử bản quantized nếu README có đề cập, nếu vẫn không được → kết luận H2, dừng ở đây.

### Bước 2 — Chạy demo trên câu test chuẩn (để so sánh trực tiếp với kết quả đã có)

**Dùng đúng câu mẫu đã test với guwen-ner/Jiayan (giữ nguyên để so sánh công bằng):**

```
始祖諱文成官至知府娶阮氏生子一人諱德重
```

Chạy cả 2 bản: **phồn thể** (câu trên, đúng dạng Hán-Nôm thật) và **giản thể** (như đã làm với guwen-ner) — ghi rõ model trả ra thực thể gì, nhãn gì, score gì (nếu có) cho từng bản.

### Bước 3 — Chạy thêm 10–20 câu tự soạn dạng gia phả

Theo đúng ràng buộc `.cursor/rules/gia-pha-only-analysis.mdc`: **chỉ** câu tự viết dạng tộc phả/tông phả/phả ký (tên, quan hệ cha/mẹ/con/vợ chồng, đời, chức tước, quê quán, năm sinh/mất) — **không** dùng khế ước, tế văn, sắc phong, chiếu. Lưu câu test tại `research/model_survey/trial/xunzillm_sample_input.txt`, output thô tại `research/model_survey/trial/xunzillm_output_raw.json` (hoặc định dạng gốc model).

### Bước 4 — Thử tác vụ dịch nghĩa (nếu demo có endpoint dịch)

XunziLLM tự nhận làm được dịch nghĩa cổ văn — chạy thử dịch 2-3 câu gia phả Hán sang tiếng Việt, so sánh nhanh (không cần đánh giá BLEU chính thức ở bước này) với bản Gemini đã có sẵn trong `nlp_family_extractor/data/sample_relationship_document.txt` nếu trùng câu, để có cảm quan ban đầu — **không kết luận vượt trội chỉ từ vài câu**, chỉ ghi quan sát.

## 4. Ghi kết quả — theo đúng khuôn Fact/Suy luận/Độ tin cậy của repo

Tạo (hoặc bổ sung nếu đã có, nhớ kiểm tra cả 2 nhánh trước khi tạo trùng) `research/model_survey/xunzillm_evaluation.md` với cấu trúc:

```markdown
# XunziLLM — kết quả chạy thử thật (Cursor, <ngày>)

## Fact
- Cài đặt: thành công/thất bại, log lỗi nếu có
- License: <trích dẫn nguyên văn nguồn>
- Kết quả câu test chuẩn (phồn thể / giản thể): <output thô>
- Kết quả 10-20 câu tự soạn: <tóm tắt, link file raw>

## Suy luận (độ tin cậy: cao/trung bình/thấp)
- ...

## Kết luận H1/H2
- ...

## So sánh với guwen-ner/Jiayan (nếu có dữ liệu đối chiếu)
- ...
```

## 5. Ràng buộc — không được làm trong task này

- **Không sửa** bất kỳ file trong `nlp_family_extractor/app/` (pipeline chính) — task này chỉ khảo sát, tương tự ràng buộc T1–T3 của `chinese_genealogy_model_hunt_plan.md` gốc. Tích hợp vào pipeline chính là một task riêng, chỉ làm sau khi có kết luận rõ + người dùng duyệt.
- **Không** dùng dữ liệu ngoài phạm vi gia phả (khế ước, tế văn, sắc phong) để test.
- **Không bịa** số liệu/license nếu không chạy được — ghi "chưa xác định được" rõ ràng, kèm lý do (lỗi gì, chặn gì), giống cách `phan_tich_hop_21_09_2026.md` đã làm với các ứng viên khác.

## 6. Acceptance criteria

- [ ] License XunziLLM đã được xác định rõ (trích dẫn nguồn), hoặc ghi rõ vì sao chưa xác định được.
- [ ] Có log/output thật từ ít nhất 1 lần chạy inference (câu test chuẩn), không phải suy đoán từ README.
- [ ] Có so sánh trực tiếp (cùng câu) với kết quả guwen-ner đã có (0/4 phồn thể, 3/4 giản thể).
- [ ] Kết luận H1 hoặc H2 (hoặc cả hai một phần), có bằng chứng kèm theo.
- [ ] Kết quả được ghi vào `research/model_survey/xunzillm_evaluation.md`, không chỉ báo miệng/chat.
