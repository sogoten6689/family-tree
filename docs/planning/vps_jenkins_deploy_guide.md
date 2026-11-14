# Hướng dẫn deploy lên VPS qua Jenkins (đã cài sẵn)

Phần 1 cũ (dashboard thống kê `hannom-dashboard`, domain `thongke-giapha.kimtudien.com.vn`)
đã bỏ ngày 14/11/2026: xoá job Jenkins, container, nginx và code. Còn lại app chính
`family-tree` (domain `giapha.kimtudien.com.vn`).

## Phần 2 — `family-tree` (app chính, domain `giapha.kimtudien.com.vn`)

**Fact (đọc trực tiếp code trong session này):** repo đã có sẵn 2 cơ chế liên
quan, không cần tạo mới:

- `.github/workflows/deploy.yml` — GitHub Actions, khi push `master`/`main`:
  SSH vào VPS (`secrets.VPS_HOST/VPS_USER/VPS_SSH_KEY/VPS_PORT`, environment
  tên `VPS_HOST`), `cd ~/projects/family-tree && git reset --hard
  origin/master && ./infra/scripts/build-all.sh --up`, rồi
  `curl http://localhost:87/health`.
- `infra/docker-compose.yml` + `infra/nginx/conf.d/giapha.kimtudien.com.vn.conf`
  — nginx (host port **87**) → frontend/backend container, domain
  `giapha.kimtudien.com.vn` đã cấu hình sẵn trong repo (TLS/reverse-proxy tầng
  ngoài trên VPS thật thế nào thì tôi không xác nhận được từ xa — nếu site đã
  chạy HTTPS thật, tầng đó nằm ngoài repo này).

**Mới thêm trong session này:** `Jenkinsfile` ở **root** repo (không phải
trong `research/`) — chạy đúng logic `deploy.yml` (`./infra/scripts/build-all.sh
--up` + health check port 87), để bạn có thêm 1 pipeline Jenkins song song với
GitHub Actions, theo đúng yêu cầu "cần cả GitHub Actions và Jenkins".

**Bạn đã chọn: tự merge branch `claude/busy-planck-bb0lwd` (chứa UI Guest) vào
`master` — tôi không tạo PR lần này.** Cả GitHub Actions và Jenkins job dưới
đây chỉ deploy đúng UI mới SAU KHI bạn merge xong (cả 2 cơ chế đều trỏ vào
`master`/`main`).

### B1 — Kích hoạt GitHub Actions (chỉ cần làm 1 lần)

`deploy.yml` dùng `environment: VPS_HOST` — secrets phải khai báo trong
**Settings → Environments → VPS_HOST** (không phải "Repository secrets"
thường, trừ khi bạn đổi `environment:` trong file). Cần 4 secret:

| Secret | Giá trị |
|---|---|
| `VPS_HOST` | IP hoặc hostname VPS (lấy từ `~/.ssh/config`, mục `Host vps-caohoc` → `HostName ...`) |
| `VPS_USER` | user SSH (mục `User ...` trong config đó) |
| `VPS_SSH_KEY` | **nội dung** private key SSH dùng để login (không phải password) |
| `VPS_PORT` | port SSH, nếu khác 22 (optional, mặc định 22) |

Kiểm tra nhanh giá trị thật từ máy đã có alias `vps-caohoc`:

```bash
ssh -G vps-caohoc | grep -E '^(hostname|user|port) '
```

Tôi **không có tool để tự set GitHub Actions secrets** (không nằm trong bộ
MCP GitHub hiện có) — bạn tự thêm qua GitHub UI, hoặc nếu máy local có `gh`
CLI đã đăng nhập:

```bash
gh secret set VPS_HOST --env VPS_HOST --body "<ip-hoac-hostname>"
gh secret set VPS_USER --env VPS_HOST --body "<ssh-user>"
gh secret set VPS_SSH_KEY --env VPS_HOST < ~/.ssh/<private-key-file>
```

### B2 — Đảm bảo `~/projects/family-tree` đã tồn tại trên VPS

`deploy.yml` giả định repo đã **clone sẵn từ trước** ở `~/projects/family-tree`
trên VPS (chỉ `git reset --hard`, không `git clone`). Kiểm tra qua SSH:

```bash
ssh vps-caohoc "test -d ~/projects/family-tree/.git && echo OK || echo MISSING"
```

Nếu `MISSING`, clone lần đầu:

```bash
ssh vps-caohoc "mkdir -p ~/projects && cd ~/projects && git clone https://github.com/sogoten6689/family-tree.git"
```

(dùng credential đọc được repo nếu private — PAT hoặc SSH deploy key, tương tự
Phần 1 Bước 1).

### B3 — Thêm Jenkins job cho family-tree (song song GitHub Actions)

Trong Jenkins UI (`cicd.kimtudien.com.vn`): **New Item** → tên vd
`family-tree` → **Pipeline** → OK.

- Pipeline script from SCM → Git
- Repository URL: `https://github.com/sogoten6689/family-tree.git`
- Credentials: chọn nếu repo private, "- none -" nếu public
- Branch Specifier: `*/master` (sau khi bạn merge UI Guest vào master)
- Script Path: `Jenkinsfile` (mặc định, ở root — khác với Phần 1)

**Điều kiện quan trọng, khác Phần 1:** stage `Build & Deploy` gọi
`./infra/scripts/build-all.sh --up`, tự chạy `docker compose build/up` — cần
Jenkins **agent chạy trên chính VPS này** (không phải agent khác), vì lệnh đó
giả định `mysql`/`minio`/`nginx` container đã sẵn đang chạy trên máy đó (chỉ
rebuild/restart backend+frontend, không khởi tạo lại toàn bộ stack). Nếu
Jenkins agent của bạn không cùng máy VPS, cần đổi kiến trúc (agent label, hoặc
SSH-based deploy step) — báo lại nếu rơi vào trường hợp này.

Build Now → theo dõi Console Output đến khi qua `Health check` (curl
`localhost:87/health` trả 200).

### B4 — Xác nhận domain thật

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://giapha.kimtudien.com.vn/
# Kỳ vọng: 200, và UI hiển thị đúng Guest layout mới (sidebar, vào thẳng màn
# hình upload, không còn trang giới thiệu HomePage cũ ở "/")
```

**Lưu ý xung đột có thể xảy ra (chưa quan sát được, chỉ dự đoán theo logic
code):** nếu cả GitHub Actions và Jenkins cùng trigger gần nhau (vd cả 2 đều
nghe push vào `master`), `docker compose build/up --force-recreate` chạy song
song từ 2 checkout khác nhau có thể đua nhau ghi đè cùng container name — nếu
gặp lỗi lạ khi cả 2 chạy cùng lúc, đây là nguyên nhân khả năng cao, không phải
bug code.

---

## Ghi chú độ tin cậy

- **High confidence** (đọc trực tiếp code, đã test logic Python ngoài Docker
  trong session này): stage thứ tự, đường dẫn `data/` trong container, fix
  `_repo_paths.py` hoạt động đúng.
- **Moderate confidence** (theo hành vi chuẩn của Jenkins/Docker, chưa quan
  sát trực tiếp VPS của bạn): tên user chạy Jenkins là `jenkins`, cú pháp UI
  "Manage Jenkins → Credentials" (đúng cho Jenkins bản 2.x hiện đại, có thể
  lệch nếu bạn dùng bản rất cũ hoặc theme UI khác).
- **Unresolved (cần bạn xác nhận, tôi không có cách kiểm chứng từ xa):**
  `family-tree` public hay private trên GitHub; Jenkins đã có plugin `Git` +
  `Pipeline` (thường có sẵn theo mặc định, nhưng không chắc 100% nếu cài tối
  giản); `~/projects/family-tree` đã tồn tại trên VPS theo đúng giả định của
  `deploy.yml` hay chưa (Phần 2, B2); Jenkins agent chạy trên cùng máy VPS
  đang chạy docker-compose stack family-tree hay không (Phần 2, B3); tầng
  reverse-proxy/TLS ngoài cùng thật cho `giapha.kimtudien.com.vn` (nằm ngoài
  repo, không đọc được từ đây).

Báo lại kết quả từng bước (đặc biệt Console Output nếu có stage đỏ) để tôi
chẩn đoán tiếp — tôi không thấy được VPS của bạn trực tiếp.
