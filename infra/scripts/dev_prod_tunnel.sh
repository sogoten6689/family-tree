#!/usr/bin/env bash
# Chạy backend LOCAL nối vào dữ liệu PRODUCTION qua SSH tunnel (không mở cổng ra Internet).
#   DB   : 127.0.0.1:13309 -> VPS mysql 3309  (tài khoản family_ro, CHỈ ĐỌC)
#   MinIO: 127.0.0.1:19002 -> VPS minio 9002  (khoá của backend production: ĐỌC + GHI THẬT)
# Cần: alias SSH `vps-caohoc` trong ~/.ssh/config và file nlp_family_extractor/.env.prod-tunnel
# (gitignored, do người có quyền tạo — xem docs). READ_ONLY_MODE=1 bỏ qua mọi bootstrap/ALTER lúc khởi động.
#
#   ./infra/scripts/dev_prod_tunnel.sh start    # mở tunnel nền
#   ./infra/scripts/dev_prod_tunnel.sh backend  # chạy uvicorn local cổng 8002 (cần tunnel đang mở)
#   ./infra/scripts/dev_prod_tunnel.sh status | stop
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT/nlp_family_extractor/.env.prod-tunnel"
PIDFILE="${TMPDIR:-/tmp}/family-tree-prod-tunnel.pid"
HOST="${VPS_SSH_ALIAS:-vps-caohoc}"

is_up() { [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; }

case "${1:-}" in
  start)
    if is_up; then echo "Tunnel đã chạy (pid $(cat "$PIDFILE"))"; exit 0; fi
    ssh -f -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o BatchMode=yes \
        -L 13309:127.0.0.1:3309 -L 19002:127.0.0.1:9002 "$HOST"
    pgrep -f "ssh -f -N .*13309:127.0.0.1:3309" | head -1 > "$PIDFILE"
    echo "Tunnel mở: MySQL 127.0.0.1:13309, MinIO 127.0.0.1:19002 (pid $(cat "$PIDFILE"))" ;;
  stop)
    if is_up; then kill "$(cat "$PIDFILE")" && rm -f "$PIDFILE" && echo "Đã đóng tunnel"; else echo "Tunnel không chạy"; fi ;;
  status)
    if is_up; then echo "Tunnel đang chạy (pid $(cat "$PIDFILE"))"; else echo "Tunnel không chạy"; exit 1; fi ;;
  backend)
    is_up || { echo "Chưa mở tunnel: chạy '$0 start' trước"; exit 1; }
    [ -f "$ENV_FILE" ] || { echo "Thiếu $ENV_FILE"; exit 1; }
    cd "$ROOT/nlp_family_extractor"
    set -a; . "$ENV_FILE"; set +a
    echo "Backend local -> DB production CHỈ ĐỌC, MinIO production ĐỌC+GHI. Ctrl+C để dừng."
    exec uvicorn api:app --reload --port 8002 ;;
  *) echo "Dùng: $0 {start|backend|status|stop}"; exit 2 ;;
esac
