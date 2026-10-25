#!/usr/bin/env bash
# Harness tích hợp: chạy API thật qua HTTP.
#   scripts/harness.sh           -> tầng không DB (tự khởi động uvicorn, giống CI)
#   scripts/harness.sh db        -> tầng đầy đủ: MySQL TẠM (container harness-mysql, không volume,
#                                   không đụng family-tree-mysql), chạy API, test CRUD, dọn dẹp
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/nlp_family_extractor"
export PYTHONPATH=.

if [[ "${1:-}" != "db" ]]; then
  exec python3 -m pytest tests/integration -q "${@:1}"
fi

docker info >/dev/null 2>&1 || { echo "Docker daemon chưa chạy"; exit 1; }
DB_PORT=3319
API_PORT=18002
docker rm -f harness-mysql >/dev/null 2>&1 || true
docker run -d --name harness-mysql --tmpfs /var/lib/mysql -p "$DB_PORT:3306" \
  -e MYSQL_ROOT_PASSWORD=root_password -e MYSQL_DATABASE=family_tree \
  -e MYSQL_USER=family_user -e MYSQL_PASSWORD=family_password mysql:8.4 >/dev/null
API_PID=""
cleanup() { [[ -n "$API_PID" ]] && kill "$API_PID" 2>/dev/null; docker rm -f harness-mysql >/dev/null 2>&1 || true; }
trap cleanup EXIT
until docker exec harness-mysql mysql -ufamily_user -pfamily_password -h127.0.0.1 -e 'select 1' family_tree >/dev/null 2>&1; do sleep 2; done

MYSQL_HOST=127.0.0.1 MYSQL_PORT=$DB_PORT MYSQL_USER=family_user MYSQL_PASSWORD=family_password \
JWT_SECRET_KEY=harness-secret python3 -m uvicorn api:app --port "$API_PORT" >/tmp/harness-uvicorn.log 2>&1 &
API_PID=$!
HARNESS_API_URL="http://127.0.0.1:$API_PORT" python3 -m pytest tests/integration -q "${@:2}"
