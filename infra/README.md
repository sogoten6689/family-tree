# infra

Nginx, Docker Compose, script build/deploy.

Từ **root repo**:

```bash
./infra/scripts/compose.sh up -d --build
./infra/scripts/build-all.sh --up
```

File compose: `infra/docker-compose.yml` (path build/volume vẫn tính từ root; `.env` cũng ở root).

## Backup + pull dữ liệu mới định kỳ (Jenkins)

Xem [`infra/jenkins/README.md`](./jenkins/README.md) — 2 job chạy hàng tuần
trên `cicd.kimtudien.com.vn`: backup MySQL+MinIO, và pull cây gia phả mới
từ VietnamGiaPha (tái dùng endpoint `/api/vietnamgiapha/crawl-sync` có sẵn).
