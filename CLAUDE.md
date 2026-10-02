# CLAUDE.md

# Project: family-tree

Ảnh hoặc chữ gia phả Hán Nôm → cây người → web. Repo luận văn cao học.
Bản đồ: `docs/REPO_MAP.md` · Chạy/deploy: `readme.md` · Mục lục tài liệu: `docs/README.md`.

## Cấu trúc
- `family-saga-io/` — UI: React + Vite + TS, test bằng vitest
- `nlp_family_extractor/` — API FastAPI (`app/` chạy thật, `tools/` lab OCR), xem `ARCHITECTURE.md`
- `research/` gán nhãn · `data/` corpus 00_raw…05_ops (phần lớn bị gitignore) · `infra/` nginx + compose
- `docs/planning/` kế hoạch · `docs/lab/note_meeting_weekly/` biên bản họp với thầy

## Lệnh (khớp CI)
- Frontend: `cd family-saga-io && npm run test && npm run build` (lint: `npm run lint`, CI chỉ cảnh báo)
- Backend test: `cd nlp_family_extractor && PYTHONPATH=. python -m pytest tests/ --ignore=tests/test_family_tree_api.py -q`
- Dev: frontend `npm run dev` (cổng 8080) · backend `uvicorn api:app --reload --port 8002`
- Node: kiểm tra `node -v` ≥ 18.18 trước khi chạy tool (shell của Claude có thể dùng nvm v14)
- Python: CI dùng 3.11; `.venv` local là 3.10; `.venv-paddleocr` là 3.11, chỉ dùng cho PaddleOCR

## Quy ước khoa học (thầy xác nhận = nguồn sự thật, không tự đặt lại)
- `ma_dinh_danh` (mã F) ≠ `doc_id`. Nguồn quy ước: `docs/lab/note_meeting_weekly/31_08_2026/`.
- Từ 02/10/2026 (quyết định của Lâm, chưa ghi nhận thầy duyệt): mã **tự tạo** — chép nguyên văn mã
  đã chốt ở catalogue nghiên cứu, hoặc Gemini trích thông tin từ bản dịch; số 3 chữ số đánh **riêng
  theo chữ A–V**. Mã đã có không bao giờ ghi đè. Chi tiết: `docs/planning/ma_dinh_danh_tu_dong.md`.

## Cấm
- Không commit `.env`, `.claude/settings.local.json`, dữ liệu trong `data/`
- Gọi Kim Hán Nôm OCR, Gemini, Colab GPU = tốn tiền (R3), phải hỏi trước
- Có thể có phiên Claude khác đang sửa cùng lúc: trước khi commit, xem thời gian sửa file
  và chỉ commit những gì thuộc việc của mình

# Cách làm việc

Áp dụng skill `scientific-method` (`~/.claude/skills/scientific-method/SKILL.md`) khi điều tra lỗi, phân tích dữ liệu/kết quả, review, thiết kế thí nghiệm hoặc báo cáo kết luận. Tóm tắt:

- Tách rõ fact / quan sát / suy luận / giả thuyết / giả định; không trình bày giả định như sự thật.
- Ưu tiên bằng chứng trực tiếp (quan sát, test tái lập, source code) hơn suy luận.
- Debug theo giả thuyết: nêu nhiều nguyên nhân, thiết kế test phân biệt, tìm nguyên nhân gốc rồi sửa nhỏ nhất an toàn.
- Định lượng khi có thể; nêu mức tin cậy (cao / vừa / thấp) và điều còn chưa biết.
- Khi yêu cầu, tài liệu và code mâu thuẫn → báo mâu thuẫn trước khi sửa lớn.
