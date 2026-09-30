# Jenkins — backup + pull dữ liệu mới hàng tuần

CI/CD hiện tại của repo dùng **GitHub Actions** (`.github/workflows/`) cho
build/deploy khi push lên `master`/`main`. Hai job dưới đây chạy trên
**Jenkins** (`cicd.kimtudien.com.vn`), tách riêng vì là job định kỳ
(cron), không gắn với sự kiện push code.

| Job | File | Lịch | Việc làm |
|---|---|---|---|
| `family-tree-backup-weekly` | [`Jenkinsfile.backup`](./Jenkinsfile.backup) | CN ~02:00 | Dump MySQL (`family_tree`) + tar volume MinIO, lưu trên VPS (`~/backups/family-tree/`), tự xoá backup > 60 ngày |
| `family-tree-vgp-pull-weekly` | [`Jenkinsfile.vgp-pull`](./Jenkinsfile.vgp-pull) | CN ~03:00 (sau backup) | Gọi lại `POST /api/vietnamgiapha/crawl-sync` đã có sẵn để tìm + đồng bộ cây gia phả mới trên VietnamGiaPha |

**Phạm vi đã xác nhận với Lâm (2026-09):** backup chỉ cần nằm sẵn trên VPS,
chưa cần tự động tải đi máy khác. Muốn tải về máy khác thì `scp`/`rsync`
thủ công từ VPS sau.

## Vì sao 2 job tách riêng, không gộp 1

- Backup nên chạy trước, không phụ thuộc mạng ngoài (chỉ đọc/ghi local).
- Pull VGP gọi ra internet (site nguồn) + Kim Hán Nôm nếu `attach_documents`
  kích hoạt OCR — có thể chậm/lỗi mạng, không nên chặn backup nếu nó fail.

## Thiết lập lần đầu trên Jenkins UI

1. **Tạo 2 credentials** (Manage Jenkins → Credentials → System → Global):
   - `vps-ssh-key` — loại **SSH Username with private key**. Username =
     user SSH thật trên VPS (mặc định script giả định `ubuntu`, đổi qua
     tham số `VPS_USER` nếu khác). Private key = key đã cho phép SSH vào
     VPS (có thể dùng lại đúng key trong secret `VPS_SSH_KEY` của GitHub
     Actions nếu cùng VPS).
     ⚠️ SSH trên VPS này không nghe ở cổng 22 mặc định — đổi tham số
     `VPS_SSH_PORT` khi build cho khớp cổng thật (khớp `secrets.VPS_PORT`
     trong GitHub Actions nếu đã có).
   - `vgp-admin-password` — loại **Secret text**. Mật khẩu tài khoản admin
     **production** thật (KHÔNG phải `Admin@123456` mặc định trong
     `infra/docker-compose.yml`, đó chỉ để dev local).
     ⚠️ Nếu mật khẩu chứa dấu nháy đơn (`'`), đổi mật khẩu khác — script
     `vgp_pull_sync.sh` bọc giá trị này trong `'...'` khi gửi qua SSH, dấu
     nháy đơn bên trong sẽ làm gãy câu lệnh.

2. **Tạo 2 job kiểu Pipeline**, mỗi job:
   - New Item → Pipeline
   - Definition: **Pipeline script from SCM**
   - SCM: Git, trỏ URL repo này (`https://github.com/sogoten6689/family-tree`),
     branch `master` (hoặc branch bạn muốn Jenkins theo dõi — có thể khác
     branch deploy code, vì 2 script này ít đổi)
   - Script Path: `infra/jenkins/Jenkinsfile.backup` (job 1) hoặc
     `infra/jenkins/Jenkinsfile.vgp-pull` (job 2)
   - Không cần tick thêm trigger nào trong UI — lịch cron đã khai báo
     trong chính file Jenkinsfile (`triggers { cron(...) }`).

3. **Chạy tay 1 lần đầu** (Build Now) cho cả 2 job để Jenkins đăng ký
   trigger cron (giới hạn đã biết của Jenkins Pipeline-from-SCM: cron
   trong file chỉ có hiệu lực sau lần build đầu tiên).

4. **Xác nhận trên VPS** trước khi tin job chạy đúng:
   - `infra/scripts/backup.sh` và `infra/scripts/vgp_pull_sync.sh` đã có
     quyền thực thi (`chmod +x`, đã set sẵn khi tạo file — kiểm tra lại
     sau khi `git pull` trên VPS vì git không phải lúc nào cũng giữ bit
     `+x` qua mọi thao tác).
   - VPS có `.env` ở root repo chứa `MYSQL_ROOT_PASSWORD` (dùng bởi
     `backup.sh`) — không commit file này (đã có trong `.gitignore`).
   - User SSH (`VPS_USER`) có quyền chạy `docker`/`docker compose` không
     cần `sudo` (hoặc sửa script thêm `sudo` nếu VPS yêu cầu).

## Việc CHƯA làm (nói rõ để khỏi hiểu nhầm là đã xong)

- **Chưa test chạy thật** — không có Jenkins/VPS thật trong môi trường
  Claude Code để verify. Đã kiểm tra: `bash -n` cú pháp sạch cho cả 2
  script `.sh`; logic gọi `/api/vietnamgiapha/crawl-sync` khớp đúng
  request/response schema đọc trực tiếp từ `nlp_family_extractor/api.py`
  (không đoán field). Groovy của Jenkinsfile chưa có cách lint trong môi
  trường này — cần Jenkins thật xác nhận cú pháp `pipeline{}` chạy được.
- **Chưa tự động hoá việc chọn `VGP_START_ID`/`VGP_END_ID` theo dữ liệu
  hiện có** — đang để cố định 1..3000 (rộng hơn ~2.152 cây đã biết).
  `skip_unchanged=true` làm việc quét rộng vẫn rẻ (bỏ qua cây không đổi
  nội dung), nhưng nếu VGP vượt quá 3000 cây thì cần tăng `VGP_END_ID`
  thủ công qua tham số job.
- **Chưa có thông báo khi job fail** (Slack/email) — `post { failure { ... } }`
  hiện chỉ in ra Jenkins console log. Thêm dễ nếu bạn cho biết kênh báo
  (email SMTP đã cấu hình trên Jenkins, hay webhook Slack/Telegram).
