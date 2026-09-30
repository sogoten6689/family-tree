#!/usr/bin/env bash
set -euo pipefail

# Backup MySQL (family_tree) + MinIO (minio_data volume) cho VPS production.
# Chạy trực tiếp trên VPS (không cần chạy trong container) — script tự gọi
# `docker compose exec`/`docker run` để thao tác với các container đang chạy.
#
# Dùng bởi Jenkins job "family-tree-backup-weekly" (infra/jenkins/Jenkinsfile.backup)
# qua SSH, nhưng cũng chạy tay được: ./infra/scripts/backup.sh
#
# Không tự đẩy backup đi đâu khác — chỉ lưu trên VPS, dưới BACKUP_DIR (xem dưới).
# Theo yêu cầu 2026-09: "chỉ cần backup nằm sẵn trên VPS, chưa cần tự động
# pull đi đâu" — muốn tải đi máy khác thì làm thủ công (scp/rsync) sau.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="infra/docker-compose.yml"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/family-tree}"
RETENTION_DAYS="${RETENTION_DAYS:-60}"   # giữ ~8 tuần backup hàng tuần
# Cho phép Jenkins truyền STAMP từ ngoài vào để biết chính xác tên file vừa
# tạo (dùng scp lấy về workspace rồi archiveArtifacts cho tải qua UI).
STAMP="${STAMP:-$(date +%Y%m%d-%H%M%S)}"

mkdir -p "$BACKUP_DIR"

echo "== 1/3 Backup MySQL (family_tree) =="
# Đọc mật khẩu root từ .env ở root repo (đúng biến MYSQL_ROOT_PASSWORD trong
# infra/docker-compose.yml) — KHÔNG hardcode mật khẩu vào script này.
if [ -z "${MYSQL_ROOT_PASSWORD:-}" ] && [ -f .env ]; then
  # shellcheck disable=SC1091
  MYSQL_ROOT_PASSWORD="$(grep -E '^MYSQL_ROOT_PASSWORD=' .env | tail -n1 | cut -d= -f2-)"
fi
if [ -z "${MYSQL_ROOT_PASSWORD:-}" ]; then
  echo "LỖI: thiếu MYSQL_ROOT_PASSWORD (đặt trong .env ở root repo hoặc export trước khi chạy)." >&2
  exit 1
fi

MYSQL_DUMP_FILE="$BACKUP_DIR/mysql-family_tree-$STAMP.sql.gz"
docker compose -f "$COMPOSE_FILE" --project-directory . exec -T mysql \
  mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" \
    --single-transaction --quick --routines --events \
    family_tree | gzip > "$MYSQL_DUMP_FILE"
echo "  -> $MYSQL_DUMP_FILE ($(du -h "$MYSQL_DUMP_FILE" | cut -f1))"

echo "== 2/3 Backup MinIO (volume family-tree_minio_data) =="
MINIO_VOLUME="$(docker compose -f "$COMPOSE_FILE" --project-directory . config --format json 2>/dev/null \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['volumes']['minio_data']['name'])" 2>/dev/null \
  || echo "family-tree_minio_data")"
MINIO_BACKUP_FILE="$BACKUP_DIR/minio-$STAMP.tar.gz"
docker run --rm \
  -v "${MINIO_VOLUME}:/data:ro" \
  -v "$BACKUP_DIR:/backup" \
  alpine:3.20 \
  tar czf "/backup/$(basename "$MINIO_BACKUP_FILE")" -C /data .
echo "  -> $MINIO_BACKUP_FILE ($(du -h "$MINIO_BACKUP_FILE" | cut -f1))"

echo "== 3/3 Dọn backup cũ hơn $RETENTION_DAYS ngày =="
find "$BACKUP_DIR" -maxdepth 1 -name 'mysql-family_tree-*.sql.gz' -mtime "+$RETENTION_DAYS" -print -delete
find "$BACKUP_DIR" -maxdepth 1 -name 'minio-*.tar.gz' -mtime "+$RETENTION_DAYS" -print -delete

echo "Xong. Backup nằm tại: $BACKUP_DIR"
ls -lh "$BACKUP_DIR" | tail -n +2
