# Hướng dẫn deploy lên VPS qua Jenkins (đã cài sẵn)

Gồm 2 phần độc lập: **Phần 1** — dashboard thống kê `hannom-bilingual-dataset`
(domain `thongke-giapha.kimtudien.com.vn`). **Phần 2** — app chính
`family-tree` (domain `giapha.kimtudien.com.vn`), thêm Jenkins CI/CD song song
với GitHub Actions đã có sẵn.

## Phần 1 — `hannom-dashboard`

**Bối cảnh (fact, đã xác nhận qua đọc trực tiếp code trong session này):**
Sau khi gộp `hannom-bilingual-dataset` vào `family-tree` (2026-09-29), pipeline
build/deploy dashboard giờ nằm ở:

```
family-tree/research/hannom-bilingual-dataset/Jenkinsfile
```

thay vì repo `hannom-bilingual-dataset` cũ (giờ chỉ còn `data/`, `runs/`,
private). Jenkins job hiện tại (nếu có, trỏ vào repo cũ) **cần cấu hình lại**
để trỏ vào file mới này.

**Giả định chưa kiểm chứng được từ xa (label rõ — tôi không có SSH vào VPS
của bạn, nên các bước dưới đây dựa trên hành vi Jenkins/Docker chuẩn, không
phải quan sát trực tiếp môi trường của bạn):**
- Jenkins đã cài, đang chạy, bạn có quyền admin trên UI (theo bạn xác nhận).
- Docker đã cài trên VPS và Jenkins (user chạy jenkins service) có quyền gọi
  `docker` — **cần bạn tự kiểm chứng ở Bước 0**, vì đây là nguyên nhân fail
  phổ biến nhất (`permission denied` khi Jenkinsfile gọi `docker build`).
- Bạn có (hoặc sẽ tạo) 1 GitHub Personal Access Token (PAT) có quyền đọc repo
  private `sogoten6689/hannom-bilingual-dataset`.

---

## Bước 0 — Kiểm tra điều kiện trên VPS (chạy qua SSH của bạn)

```bash
# Jenkins đang chạy?
systemctl status jenkins --no-pager | head -5

# User chạy Jenkins là ai? (thường "jenkins")
ps -ef | grep -m1 '[j]enkins.war\|[j]enkins\.jar' | awk '{print $1}'

# User đó có gọi được docker không? (thay "jenkins" nếu lệnh trên ra tên khác)
sudo -u jenkins docker ps
```

Nếu lệnh cuối báo `permission denied` (không phải "no such file"): user
`jenkins` chưa nằm trong group `docker`. Sửa bằng:

```bash
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
```

Chờ Jenkins UI load lại (thường 30–60s) trước khi qua bước sau.

---

## Bước 1 — Tạo credential Jenkins cho repo dữ liệu private

Repo `sogoten6689/hannom-bilingual-dataset` (chứa `data/`, ~82MB) là **private**
— `git clone` ẩn danh sẽ bị từ chối. Jenkinsfile mới (đã sửa trong commit này)
dùng credential id cố định `hannom-data-repo-pat` để nhúng token vào URL clone
tại runtime, không hardcode token trong file.

1. Tạo PAT trên GitHub (nếu chưa có): https://github.com/settings/tokens →
   **Generate new token (classic)** → scope tối thiểu `repo` (đọc private repo
   là đủ, không cần quyền ghi) → copy token (chỉ hiện 1 lần).
2. Trong Jenkins UI: **Manage Jenkins → Credentials → System → Global
   credentials (unrestricted) → Add Credentials**
   - Kind: **Username with password**
   - Scope: Global
   - Username: tên tài khoản GitHub của bạn (vd `sogoten6689`)
   - Password: dán PAT vừa tạo ở bước 1
   - **ID: `hannom-data-repo-pat`** ← phải khớp chính xác chuỗi này, Jenkinsfile
     tham chiếu đúng id này.
   - Description: "PAT đọc repo dữ liệu hannom-bilingual-dataset (private)"
3. Save.

**Nếu `family-tree` (repo chứa Jenkinsfile) cũng là private:** job Jenkins tự
checkout repo này cần credential riêng (khác cái ở trên) — tạo tương tự (có
thể cùng PAT nếu token có quyền đọc cả 2 repo), rồi chọn nó ở ô "Credentials"
trong phần cấu hình SCM ở Bước 2. Tôi không xác nhận được từ xa `family-tree`
public hay private — nếu Bước 2 báo lỗi checkout/clone khi Build Now, đây là
nguyên nhân khả năng cao nhất.

---

## Bước 2 — Trỏ Jenkins job vào Jenkinsfile mới

**Nếu bạn đã có job cũ trỏ vào repo `hannom-bilingual-dataset`:** mở job đó →
**Configure**, sửa 2 chỗ dưới. **Nếu chưa có job:** Dashboard → **New Item** →
đặt tên (vd `hannom-dashboard`) → chọn **Pipeline** → OK, rồi cấu hình như sau:

Trong phần **Pipeline**:
- Definition: **Pipeline script from SCM**
- SCM: **Git**
- Repository URL: `https://github.com/sogoten6689/family-tree.git`
- Credentials: chọn credential đọc `family-tree` nếu private (xem cuối Bước 1),
  hoặc "- none -" nếu repo public.
- Branch Specifier: `*/claude/busy-planck-bb0lwd` (branch hiện đang có
  Jenkinsfile đã sửa; đổi sang `*/master` sau khi PR này merge vào master, để
  tránh phải đổi lại job mỗi lần build thử)
- **Script Path: `research/hannom-bilingual-dataset/Jenkinsfile`** ← đây là
  chỗ đổi quan trọng nhất, khác đường dẫn cũ (`Jenkinsfile` ở root repo cũ).

Save.

---

## Bước 3 — Build thử và xác nhận

Trong job, bấm **Build Now**. Theo dõi **Console Output** — 4 stage phải chạy
tuần tự: `Checkout OK` → `Fetch data...` → `Build Dashboard Image` →
`Deploy`.

**Nếu stage `Fetch data` fail với `fatal: Authentication failed` hoặc `403`:**
credential `hannom-data-repo-pat` sai username/token, hoặc PAT không có quyền
đọc repo đó — quay lại Bước 1, kiểm tra lại token trên GitHub (Settings →
Developer settings → Personal access tokens → xem token còn hạn/đủ scope).

**Nếu stage `Build Dashboard Image` fail với lỗi liên quan `docker: command
not found` hoặc `permission denied`:** quay lại Bước 0.

Sau khi cả 4 stage xanh, xác nhận trên VPS (qua SSH):

```bash
docker ps --filter name=hannom-dashboard
# Kỳ vọng: 1 container "hannom-dashboard", STATUS "Up ...", PORTS "0.0.0.0:89->80/tcp"

curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:89
# Kỳ vọng: 200
```

Nếu VPS có firewall (`ufw`/cloud security group), mở port 89 ra ngoài nếu bạn
muốn truy cập từ máy khác:

```bash
sudo ufw allow 89/tcp   # chỉ nếu dùng ufw; bỏ qua nếu dùng cloud firewall riêng
```

Rồi truy cập `http://<IP-VPS-của-bạn>:89` từ browser để xem dashboard thật.

---

---

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
  `_repo_paths.py`/`build_dashboard.py` hoạt động đúng.
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
