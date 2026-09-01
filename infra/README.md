# infra

Nginx, Docker Compose, script build/deploy.

Từ **root repo**:

```bash
./infra/scripts/compose.sh up -d --build
./infra/scripts/build-all.sh --up
```

File compose: `infra/docker-compose.yml` (path build/volume vẫn tính từ root; `.env` cũng ở root).
