#!/usr/bin/env bash
# Fetch 10 new Nom Foundation volumes confirmed for review corpus expansion.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/data/hannom/nomfoundation"
cd "$ROOT/nlp_family_extractor"

fetch() {
  local collection="$1"
  local volume="$2"
  echo "=== Fetch collection=$collection volume=$volume ==="
  python3 -m tools.fetch_nomfoundation \
    --collection "$collection" \
    --volume "$volume" \
    --output-dir "$OUT" \
    --delay-seconds 0.5 \
    --image-variant jpeg
}

# Collection 2 — genealogy (6)
fetch 2 1256
fetch 2 147
fetch 2 207
fetch 2 833
fetch 2 854
fetch 2 865

# Collection 1 — genealogy (4)
fetch 1 84
fetch 1 557
fetch 1 563
fetch 1 1158

echo "Done. Volumes in $OUT/volumes/"
