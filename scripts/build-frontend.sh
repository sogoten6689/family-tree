#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

UP=false

usage() {
  cat <<'EOF'
Usage: scripts/build-frontend.sh [--up]

Build Docker image for frontend (family-saga-io).

Options:
  --up, -u   Restart frontend container after build
  -h, --help Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --up | -u)
      UP=true
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    esac
done

export DOCKER_BUILDKIT=0

echo "==> Building frontend..."
docker compose build frontend

if [[ "$UP" == true ]]; then
  echo "==> Starting frontend..."
  docker compose up -d --force-recreate frontend
fi

echo "==> Frontend build complete."
