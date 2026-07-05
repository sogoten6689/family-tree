#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

UP=false

usage() {
  cat <<'EOF'
Usage: scripts/build-all.sh [--up]

Build backend and frontend Docker images.

Options:
  --up, -u   Restart backend + frontend containers after build
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

ARGS=()
if [[ "$UP" == true ]]; then
  ARGS=(--up)
fi

"$ROOT_DIR/scripts/build-backend.sh" "${ARGS[@]}"
"$ROOT_DIR/scripts/build-frontend.sh" "${ARGS[@]}"

echo "==> All builds complete."
