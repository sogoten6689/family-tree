# Làm việc trên máy mới (pull code, dữ liệu, Jira)

Tạo ngày 19/10/2026. Mục đích: ngồi ở máy khác, kéo về là làm tiếp được.
Quy ước chung: xem [CLAUDE.md](../CLAUDE.md). Bản đồ repo: [REPO_MAP.md](./REPO_MAP.md). Chạy và deploy: [readme.md](../readme.md).

> **Đọc trước:** một phần công việc gần đây **chưa nằm trên GitHub** (mục 7). Phải push phần đó từ máy cũ, nếu không máy mới sẽ không thấy.

---

## 1. Repo

Dự án gồm **hai repo**. Repo dữ liệu được gitignore trong repo code và nằm lồng bên trong `data/`.

| Repo | Địa chỉ | Nhánh chính | Nội dung |
|---|---|---|---|
| `family-tree` (code + tài liệu) | `sogoten6689/family-tree` | `master` | UI, API, research, docs |
| `family-tree-data` (dữ liệu) | `sogoten6689/family-tree-data` | `main` | corpus `00_raw` … `05_ops`, PDF qua Git LFS |

```bash
# 1. Code
git clone git@github.com:sogoten6689/family-tree.git
cd family-tree
git checkout feat/train-sikubert      # nhánh đang làm; PR #38 đang mở, chưa merge

# 2. Dữ liệu (cần Git LFS trước)
git lfs install
git clone git@github.com:sogoten6689/family-tree-data.git data
```

Lưu ý:
- Máy cũ dùng alias SSH `github-sogoten` trong `~/.ssh/config`. Máy mới dùng URL `git@github.com:...` như trên, hoặc tự đặt alias.
- Clone repo dữ liệu về **đúng thư mục `data/`** trong repo code, vì code dùng đường dẫn `data/...`.
- Nhánh đang có: `feat/train-sikubert` (PR #38, dữ liệu NER Hán và notebook Colab), `master`. Các nhánh `docs/*`, `fix/*` đã merge.
- Máy cũ có nhiều worktree trong `.claude/worktrees/`. Máy mới **không cần**, chỉ cần một bản clone.

### Cài môi trường

| Phần | Lệnh | Ghi chú |
|---|---|---|
| Node | `node -v` phải ≥ 18.18 (khuyên dùng 22) | Trên máy cũ shell của Claude hay lấy nhầm nvm v14 |
| Frontend | `cd family-saga-io && npm install && npm run dev` | Cổng 8080 |
| Backend | `cd nlp_family_extractor && python -m venv .venv && .venv/bin/pip install -r requirements.txt` | CI dùng Python 3.11, `.venv` local là 3.10 |
| PaddleOCR | venv riêng, `pip install -r nlp_family_extractor/requirements-paddleocr.txt` | Python 3.11, chỉ dùng cho OCR lab, **không** gộp vào requirements chính |
| Chạy API | `uvicorn api:app --reload --port 8002` | Từ `nlp_family_extractor/` |
| Docker | `docker compose` (xem readme.md) | nginx 87, backend 8002, mysql 3309, minio 9002/9003 |

Kiểm tra sau khi cài (khớp CI):

```bash
cd family-saga-io && npm run test && npm run build
cd nlp_family_extractor && PYTHONPATH=. python -m pytest tests/ --ignore=tests/test_family_tree_api.py -q
```

---

## 2. Khoá và biến môi trường (không nằm trong git)

Tên file đã bị gitignore, **phải tự chép tay** từ máy cũ hoặc tạo lại. Không dán nội dung khoá vào chat, tài liệu hay commit.

| File | Dùng cho | Mẫu |
|---|---|---|
| `.env.local` (gốc repo) | Jira: `JIRA_EMAIL`, `JIRA_API_TOKEN` | không có, xem mục 3 |
| `nlp_family_extractor/.env` | API: DB, MinIO, `HANNOM_*` (Kim Hán Nôm), Gemini | `.env.example` |
| `research/label_studio_pipeline/.env` | Gán nhãn, Gemini/relay | `.env.example` |
| `research/source_discovery/.env` | Tìm nguồn | `.env.example` |
| `research/hannom-bilingual-dataset/.env` | Dữ liệu song ngữ | `.env.example` |
| `family-saga-io/.env`, `.env.production` | URL API cho UI | tự tạo |
| `nlp_family_extractor/app/hannom/text_engines_local.py` | Adapter phiên âm/dịch riêng | tự chép |

Mọi thứ gọi **Kim Hán Nôm OCR, Gemini, Colab GPU, RunPod** đều **tốn tiền**, phải hỏi trước (quy tắc trong CLAUDE.md).

---

## 3. Jira

| Mục | Giá trị |
|---|---|
| Site | https://giapha.atlassian.net |
| Project | **GP** (script mặc định là `SCRUM`, nên phải đặt `JIRA_PROJECT=GP`) |
| Công cụ | `research/tools/jira_cli.py` (lệnh ghi cần `--yes`) |

```bash
# .env.local ở gốc repo (không commit):
#   JIRA_EMAIL=...        JIRA_API_TOKEN=...   (tạo token ở id.atlassian.com → Security → API tokens)
set -a; source .env.local; set +a
export JIRA_PROJECT=GP
python research/tools/jira_cli.py whoami
python research/tools/jira_cli.py list
python research/tools/jira_cli.py get GP-3
```

Các thẻ đang theo dõi:

| Thẻ | Việc | Trạng thái (19/10) |
|---|---|---|
| GP-3 | Tìm dữ liệu gia phả Hán Nôm | đang làm |
| GP-17 | Subtask của GP-3: đăng tìm gia phả ở nhóm gia phả Việt Nam | chưa chuyển In Progress |
| GP-16 | Thẻ trùng của GP-17 | **anh Lâm tự xoá** |
| GP-7/8/9 | Huấn luyện SikuBERT và NER Hán | xem Jira |
| GP-14 | Báo cáo tuần (12/10 cần làm mới cuối tuần) | xem Jira |
| GP-15 | Bản dịch song song | xem Jira |
| GP-5/6/10/11 | còn To Do | |

Không thể đổi Task thành Subtask bằng API, phải tạo mới (loại Subtask, id 10002, có `parent`).

---

## 4. Tài liệu (đọc theo thứ tự này)

| Muốn biết | Mở |
|---|---|
| Quy ước, lệnh, điều cấm | [CLAUDE.md](../CLAUDE.md) |
| Mục lục tài liệu | [docs/README.md](./README.md) |
| Cấu trúc repo | [docs/REPO_MAP.md](./REPO_MAP.md) |
| Chạy và deploy | [readme.md](../readme.md) |
| Kiến trúc API | [nlp_family_extractor/ARCHITECTURE.md](../nlp_family_extractor/ARCHITECTURE.md) |
| Kế hoạch tìm dữ liệu Hán Nôm | `docs/planning/han_nom_gia_pha_data_discovery.md` (**chưa commit**, mục 7) |
| Rà nguồn Hán Nôm | [docs/planning/han_nom_source_search_2026-10-13.md](./planning/han_nom_source_search_2026-10-13.md) |
| NER Hán Nôm | [han_nom_ner_and_collection_analysis.md](./planning/han_nom_ner_and_collection_analysis.md), [hannom_ner_model_upgrade_proposal.md](./planning/hannom_ner_model_upgrade_proposal.md) |
| Mã định danh | [docs/planning/ma_dinh_danh_tu_dong.md](./planning/ma_dinh_danh_tu_dong.md) và `docs/lab/note_meeting_weekly/31_08_2026/` |
| Huấn luyện lại | [docs/planning/RETRAIN_RUNBOOK.md](./planning/RETRAIN_RUNBOOK.md), [NER_PROJECT_SUMMARY.md](./planning/NER_PROJECT_SUMMARY.md) |
| Họp với thầy | `docs/lab/note_meeting_weekly/` |
| Báo cáo tuần | `docs/reports/` |
| Luận văn | `docs/thesis/` |

---

## 5. Kiến trúc

Một câu: ảnh hoặc chữ gia phả → cây người → web.

```text
Ảnh Hán Nôm ─► OCR (Kim Hán Nôm / PaddleOCR) ─► phiên âm / dịch ─► NER + RE ─► cây gia phả ─► MySQL ─► UI
Chữ / Word  ─────────────────────────────────────────────────────┘
```

| Thư mục | Vai trò |
|---|---|
| `family-saga-io/` | UI: React + Vite + TypeScript, test bằng vitest |
| `nlp_family_extractor/` | API FastAPI. `app/` chạy thật, `tools/` là lab OCR |
| `research/label_studio_pipeline/` | Dựng dữ liệu, gán nhãn, Colab. Gồm `build_han_*`, `han_llm_prelabel`, `build_han_colab_notebook` |
| `research/source_discovery/` | Tìm và tải nguồn |
| `research/tools/jira_cli.py` | Công cụ Jira |
| `infra/` | nginx, docker compose, script build |
| `work/` | Việc tạm (ví dụ `work/facebook_group/` chứa ảnh nhóm Facebook) |

Hướng NER Hán hiện tại: mức ký tự, kiểm chéo 5 phần theo sách, so **SikuBERT** với **XLM-R-base**. Nhãn là Gemini silver (chưa phải gold). Có 15 trang giữ riêng để người soát.

---

## 6. Dữ liệu

Nằm trong repo `family-tree-data`, **khoảng 5,3 GB** khi đầy đủ.

| Tầng | Dung lượng | Ý nghĩa |
|---|---|---|
| `00_raw` | 2,6 GB | Tư liệu gốc, chỉ thêm, không sửa |
| `01_interim` | 147 MB | Máy sinh ra (Gemini, rule), chạy lại được |
| `02_gold` | 8 MB | Người đã duyệt, **số liệu bài lấy đây** |
| `03_derived` | 728 MB | Tập huấn luyện/kiểm thử, gói review |
| `04_external` | 174 MB | Sách, PDF tham khảo |
| `05_ops` | 5,7 MB | Label Studio, URL discovery |

Bộ dữ liệu Hán đang dùng, trong `data/03_derived/`: `han_pilot_v1`, `han_full_v1`, `han_llm_trial`, `han_review_v1`, `han_test_v1`, `han_ner_v1` (có notebook Colab). Chi tiết: `data/README.md`, `data/DATA_INVENTORY.md`, `data/INCOMING.md`.

Mẹo: không cần kéo hết 5,3 GB nếu chỉ code. Có thể `GIT_LFS_SKIP_SMUDGE=1 git clone ...` rồi `git lfs pull` khi cần PDF.

---

## 7. Điều CHƯA nằm trên GitHub (kiểm tra ngày 19/10)

Các mục sau chỉ có ở máy cũ. Cần commit và push, và việc commit/push cần anh Lâm cho phép.

**Repo code** (nhánh `feat/train-sikubert`, worktree `han-genealogy-data-collection-4d42b6`):

| File | Trạng thái |
|---|---|
| `research/label_studio_pipeline/build_han_colab_notebook.py` | sửa chưa commit |
| `docs/planning/han_nom_gia_pha_data_discovery.md` | mới, chưa commit |
| `docs/SETUP_MAY_MOI.md` (file này) | mới, chưa commit |
| `research/notebooks/train_ner_sweep_embedded_colab.ipynb`, `..._nodrive_colab.ipynb` | mới, chưa commit |
| `work/facebook_group/` (ảnh bìa, ảnh bài viết, `make_assets.py`) | mới, chưa commit |
| `.claude/` | cấu hình local, không commit |

**Repo dữ liệu** (`data/`, nhánh `main`):
- Đang **ahead 1 commit** so với `origin/main`, chưa push.
- Có file sửa chưa commit: `00_raw/hannom/books_catalog.json`, `nomfoundation/catalog.json`, `nomfoundation/summary.json`.
- Có thư mục mới chưa theo dõi: `00_raw/hannom/bulac/`, `00_raw/hannom/nlv_veridian/`, và một số `nomfoundation/volumes/*` (308, 309, 595, 716, và `pages/` của 429, 855).
- Các bộ `03_derived/han_*` **chưa thấy** trong danh sách file đã theo dõi, nên có thể chưa lên GitHub.
- Notebook `data/03_derived/han_ner_v1/train_han_ner_colab_v2.ipynb` có nhúng dữ liệu, chưa rõ nên đưa lên repo nào.

---

## 8. Checklist máy mới

**Chuẩn bị**
- [ ] Máy cũ: push mọi thứ ở mục 7 (có sự đồng ý của anh Lâm)
- [ ] Có khoá SSH GitHub, quyền vào cả hai repo
- [ ] Cài Git, Git LFS, Node ≥ 18.18, Python 3.11, Docker (nếu chạy compose)

**Kéo về**
- [ ] Clone `family-tree`, checkout `feat/train-sikubert` (hoặc `master` nếu PR #38 đã merge)
- [ ] `git lfs install`, clone `family-tree-data` vào `data/`
- [ ] `git status` ở cả hai repo sạch, `git log` thấy commit mới nhất

**Cài đặt**
- [ ] `npm install` trong `family-saga-io/`
- [ ] `.venv` cho `nlp_family_extractor/`, cài `requirements.txt`
- [ ] (Nếu cần OCR lab) venv PaddleOCR riêng
- [ ] Chép các file `.env` ở mục 2 từ máy cũ

**Kiểm tra**
- [ ] `npm run test && npm run build` qua
- [ ] pytest backend qua
- [ ] `npm run dev` mở được cổng 8080, API cổng 8002 trả lời

**Jira**
- [ ] Tạo `.env.local`, chạy `jira_cli.py whoami` ra đúng tài khoản
- [ ] `list` với `JIRA_PROJECT=GP` thấy GP-3, GP-17

**Việc đang chờ (tính đến 19/10)**
- [ ] Quyết định chạy lại SikuBERT so với XLM-R trên Colab (khoảng 40–70 phút GPU, tốn tiền, cần hỏi trước)
- [ ] Đóng tab Colab thừa và kiểm tra không còn phiên T4 chạy
- [ ] Merge PR #38
- [ ] Commit tài liệu kế hoạch tìm dữ liệu
- [ ] Tải PDF danh mục của Jo Hoyeon (Kyoto) và đối chiếu với kho hiện có
- [ ] Xoá thẻ trùng GP-16; chuyển GP-17 sang In Progress khi bắt đầu đăng nhóm
- [ ] Kiểm tra ảnh bìa nhóm Facebook trên điện thoại
- [ ] Điền `[liên hệ]` vào các mẫu tin nhắn
- [ ] Báo cáo tuần 12/10 làm mới cuối tuần
