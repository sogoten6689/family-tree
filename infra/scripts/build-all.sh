#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}") && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

UP=false

usage() {
  cat <<'EOF'
Usage: infra/scripts/build-all.sh [--up]

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

"$SCRIPT_DIR/build-backend.sh" "${ARGS[@]}"
"$SCRIPT_DIR/build-frontend.sh" "${ARGS[@]}"

echo "==> All builds complete."
