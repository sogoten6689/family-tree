# infra

Nginx, Docker Compose, script build/deploy.

Từ **root repo**:

```bash
./infra/scripts/compose.sh up -d --build
./infra/scripts/build-all.sh --up
```

File compose: `infra/docker-compose.yml` (path build/volume vẫn tính từ root; `.env` cũng ở root).

## Các job Jenkins (`cicd.kimtudien.com.vn`)

Trang Jenkins cần đăng nhập. Job `family-tree` không tự chạy khi merge (ví dụ PR #68 ngày 14/11/2026 phải bấm **Build Now**).

| Job | Trang Jenkins | Trang web | Nguồn (nhánh · Jenkinsfile) | Cổng host |
|---|---|---|---|--:|
| `family-tree` | [job/family-tree](https://cicd.kimtudien.com.vn/job/family-tree/) | [giapha.kimtudien.com.vn](https://giapha.kimtudien.com.vn) | repo này · `master` · `Jenkinsfile` | 87 |
| `deploy-hannom-dashboard` | [job/deploy-hannom-dashboard](https://cicd.kimtudien.com.vn/job/deploy-hannom-dashboard/) | [thongke-giapha.kimtudien.com.vn](https://thongke-giapha.kimtudien.com.vn) | repo này · `claude/busy-planck-bb0lwd` · `research/hannom-bilingual-dataset/Jenkinsfile` | 89 |
| `talking-picture` | [job/talking-picture](https://cicd.kimtudien.com.vn/job/talking-picture/) | [taking-picture.kimtudien.com.vn](https://taking-picture.kimtudien.com.vn) | `lananhdl/talking-picture` · `main` | 85 |
| `vietnet-food` | [job/vietnet-food](https://cicd.kimtudien.com.vn/job/vietnet-food/) | [vietnet-food.kimtudien.com.vn](https://vietnet-food.kimtudien.com.vn) | `PVBHai/VietNet-Food` · `main` | 86 |

`talking-picture` và `vietnet-food` thuộc repo khác, chỉ dùng chung máy Jenkins; ghi ở đây để tra link. Số liệu đọc ngày 14/11/2026.

## Backup + pull dữ liệu mới (chạy tay)

Hai job Jenkins chạy hàng tuần (`family-tree-backup-weekly`, `family-tree-vgp-pull-weekly`)
đã xoá ngày 14/11/2026: backup lỗi liên tục từ 11/10 vì VPS không còn `.env` chứa
`MYSQL_ROOT_PASSWORD`, pull VGP đã tắt từ 30/09. Hiện **không có backup tự động**.
Hai script vẫn chạy tay được trên VPS, trong `~/projects/family-tree`:

- `MYSQL_ROOT_PASSWORD=... ./infra/scripts/backup.sh`: dump MySQL + tar volume MinIO vào
  `~/backups/family-tree/`, tự xoá bản cũ hơn 60 ngày.
- `ADMIN_PASSWORD=... ./infra/scripts/vgp_pull_sync.sh`: gọi `/api/vietnamgiapha/crawl-sync`.
