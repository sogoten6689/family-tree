# Kiến trúc thông tin ở root — phân tích (góc nghiên cứu)

> **Ngày:** 2026-08-26  
> **Trạng thái:** R1–R5 đã thực hiện (docs/ theo thể loại; bộ máy không dời).  
> **Đối tượng:** thư mục gốc repo `family-tree` (không phải `data/` — corpus đã tách tầng).  
> **Câu hỏi:** Root đang làm *giao diện khoa học* hay *kho chứa chưa phân loại*?

---

## 1. Đối tượng và giả thuyết

Root của một repo nghiên cứu–kỹ thuật là **mặt phân cách** (interface): người đọc (bạn, GVHD, Cursor, reviewer) quyết định *đây là gì* trong vài giây.

**Giả thuyết:** rối ở root không phải vì thiếu file, mà vì **trộn thể loại** (genre mixing) cùng một độ sâu. Cùng cấp `ls` hiện: claim luận văn, spec sản phẩm, plan crawl, theme UI, sổ lab, Docker, hai app, corpus.

Trong khoa học thông tin, một thư mục gốc lành mạnh tách được ba lớp:

| Lớp | Câu hỏi | Ví dụ |
|-----|---------|--------|
| **Giao diện** | Tôi đang đứng đâu? Chạy thế nào? | `readme.md`, `docs/REPO_MAP.md`, `infra/docker-compose.yml` |
| **Bộ máy** | Cái gì *chạy được*? | `family-saga-io/`, `nlp_family_extractor/`, `nginx/` |
| **Tri thức** | Cái gì *đọc được* (bài, spec, sổ lab)? | hiện đang rải 8 file `.md` + `planning/` + `note_meeting_weekly/` |

Corpus (`data/`) đã có tầng 00–05. Root **chưa** có phép tương ứng cho tài liệu.

---

## 2. Phân loại thể loại (ontology)

Mỗi artifact ở root được gán **một** thể loại. Không gán hai.

| Artifact | Thể loại | Người đọc chính | Vòng đời |
|----------|----------|-----------------|----------|
| `business.md` | **Claim** (đề tài, mục tiêu) | GVHD, chương 1 | Ít đổi |
| `RESEARCH_SOURCES.md` | **Corpus note** (nguồn, bản quyền) | Chương dữ liệu | Khi thêm nguồn |
| `PROJECT.md` | **Architecture** (chạy hệ thống) | Dev, Cursor | Khi API/route đổi |
| `FEATURES.md` | **Requirements** (spec role) | Dev, kiểm thử | Khi ship feature |
| `DESIGN_SYSTEM_GUIDELINES.md` | **Design language** | FE | Khi theme đổi |
| `CRAWL_PLAN.md` | **Method / ingest** | Lab crawl | Trùng `planning/vietnamgiapha_crawl_v2_plan.md` |
| `REPO_MAP.md` | **Orientation** | Mọi người | Khi IA đổi |
| `readme.md` | **Runbook** | Deploy | Khi cổng/env đổi |
| `planning/` | **Working memory** | Đang làm | Cao |
| `note_meeting_weekly/` | **Lab notebook** | Bạn + GVHD | Append-only |
| `family-saga-io/`, `nlp_family_extractor/` | **Apparatus** | Runtime | Không chuyển thư mục |
| `label_studio_pipeline/`, `source_discovery/` | **Research code** | Lab | Không chuyển — `python -m` |
| `data/` | **Research data** (repo riêng) | Luận văn | Đã tổ chức |
| `schemas/` | **Contract** | BE/FE | Ít đổi |
| `old_code/` | **Archive** | Không đọc hàng ngày | Đóng băng |
| `docker-compose.yml`, `nginx/`, `scripts/` | **Ops** | Deploy | Ít đổi |
| `deploy.ps1`, `build-and-commit.ps1` | **Ops script** | Lẫn ở root | Nên vào `scripts/` |
| `.venv*`, `.paddlex-cache` | **Local cache** | gitignore | Không “tổ chức” |

**Mệnh đề:** tám file markdown ở root đang **cạnh tranh cùng một slot nhận thức**. Não phải phân loại mỗi lần mở Finder.

---

## 3. Ràng buộc — không được phá bộ máy thí nghiệm

Chuyển `family-saga-io/` hay `nlp_family_extractor/` = đổi Docker `build.context`, CI `working-directory`, import Python. **Chi phí ≠ lợi ích khoa học.** Cùng lý do không nhét `label_studio_pipeline/` vào `research/` lúc này.

Tổ chức root = tổ chức **lớp tri thức + archive**, giữ **lớp bộ máy** im.

Cursor rule `00-read-first.mdc` neo `PROJECT.md` ở root — nếu chuyển file, phải cập nhật rule (không để stub rỗng làm SSOT).

---

## 4. Kiến trúc đích

### 4.1. Root sau khi làm sạch (giao diện ≤ 4 thứ “đọc”)

```text
family-tree/
  README.md              runbook (GitHub)
  docs/REPO_MAP.md       bản đồ nhớ
  docker-compose.yml
  docs/                  toàn bộ tri thức đã phân thể loại
  planning/              việc đang làm (workbench — không trộn với luận văn)
  …
  [bộ máy không đổi]
```

### 4.2. `docs/` theo thể loại, không theo “tên file lịch sử”

```text
docs/
  README.md                 cách đọc (1 trang)
  thesis/                   claim + nguồn
    business.md
    RESEARCH_SOURCES.md
  product/                  hệ thống chạy được
    PROJECT.md
    FEATURES.md
    DESIGN_SYSTEM_GUIDELINES.md
  methods/                  quy trình thu thập / crawl
    CRAWL_PLAN.md
  lab/                      sổ lab
    note_meeting_weekly/
```

`planning/` **ở lại root**: đó là bàn làm việc (task OPEN), khác thể loại với `docs/thesis` (ít đổi, có thể trích dẫn trong bài).

### 4.3. Archive

```text
archive/old_code/          nguyên old_code/
```

### 4.4. Stub ở chỗ cũ

Mỗi file markdown đã chuyển để lại **5 dòng trỏ đường mới** — citation cũ không gãy. Nội dung thật chỉ còn một bản (tránh hai SSOT).

---

## 5. Lộ trình thực hiện

| Bước | Việc | Rủi ro |
|------|------|--------|
| R1 | Tạo `docs/{thesis,product,methods,lab}` + `docs/README.md` | Không |
| R2 | `git mv` 6 file md + `note_meeting_weekly` + `old_code` | Link tương đối |
| R3 | Stub ở root; sửa link trong file vừa chuyển; `planning/*.md` `../X.md` → `../docs/...` | Trung bình |
| R4 | Cập nhật `.cursor/rules/00-read-first.mdc`, `REPO_MAP.md`, `readme.md` | Thấp |
| R5 | `deploy.ps1`, `build-and-commit.ps1` → `scripts/` | Thấp nếu không ai gọi path cũ |
| R6 | *Không làm:* dời Python package, dời `data/`, dời `planning/` | — |

**Không** gộp `CRAWL_PLAN.md` vào `vietnamgiapha_crawl_v2_plan.md` trong bước này (đó là chỉnh nội dung, không phải IA).

---

## 6. Tiêu chí xong (đánh giá)

1. `ls` ở root: markdown chỉ còn `readme.md`. Bản đồ nằm ở `docs/REPO_MAP.md`.  
2. Mở `docs/README.md` biết đọc file nào cho claim / kiến trúc / sổ lab.  
3. Cursor đọc `docs/product/PROJECT.md` khi hỏi route/API.  
4. `docker compose` / CI không đổi context.  
5. Một claim chỉ một file (stub không chứa nội dung trùng).

---

## 7. Việc cố ý không làm

- Đổi tên `BalkanNode`, chuyển app vào `apps/`.  
- Viết lại 24 file `planning/` (workbench).  
- Sửa từng dòng `note_meeting_weekly` (sổ lab append-only; chỉ chuyển folder).
