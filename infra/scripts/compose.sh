#!/usr/bin/env bash
# Wrapper so Compose stays under infra/ while paths and .env stay at repo root.
# Usage (from anywhere): ./infra/scripts/compose.sh up -d --build
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec docker compose -f "$ROOT/infra/docker-compose.yml" --project-directory "$ROOT" "$@"
