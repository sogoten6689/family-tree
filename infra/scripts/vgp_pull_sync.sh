#!/usr/bin/env bash
set -euo pipefail

# Gọi lại endpoint có sẵn POST /api/vietnamgiapha/crawl-sync (nlp_family_extractor/api.py)
# để tìm + đồng bộ cây gia phả mới trên VietnamGiaPha vào DB production — không
# viết lại logic crawl, chỉ tái sử dụng đúng pipeline v2 đã có (fetch + sync DB +
# attach document + sync pipeline 7 bước trong 1 lần gọi, tự skip cây đã có nội
# dung không đổi nhờ skip_unchanged=true).
#
# Chạy trực tiếp trên VPS (gọi localhost, không qua internet) qua Jenkins job
# "family-tree-vgp-pull-weekly" (infra/jenkins/Jenkinsfile.vgp-pull), hoặc chạy
# tay: ADMIN_PASSWORD=... ./infra/scripts/vgp_pull_sync.sh
#
# Biến môi trường:
#   BACKEND_URL     mặc định http://localhost:8002 (bypass nginx, gọi thẳng backend)
#   ADMIN_EMAIL     mặc định admin@giapha.com (khớp ADMIN_EMAIL trong docker-compose)
#   ADMIN_PASSWORD  BẮT BUỘC — không hardcode, lấy từ Jenkins credentials
#   VGP_START_ID    mặc định 1
#   VGP_END_ID      mặc định 3000 (đủ rộng hơn ~2.152 cây đã biết + biên độ tăng
#                   trưởng; skip_unchanged=true nên quét rộng vẫn rẻ)

BACKEND_URL="${BACKEND_URL:-http://localhost:8002}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@giapha.com}"
VGP_START_ID="${VGP_START_ID:-1}"
VGP_END_ID="${VGP_END_ID:-3000}"

if [ -z "${ADMIN_PASSWORD:-}" ]; then
  echo "LỖI: thiếu ADMIN_PASSWORD (truyền qua env, không hardcode)." >&2
  exit 1
fi

echo "== 1/2 Đăng nhập admin để lấy JWT =="
LOGIN_RESPONSE="$(curl -fsS -X POST "$BACKEND_URL/api/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}")"
TOKEN="$(echo "$LOGIN_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")"
if [ -z "$TOKEN" ]; then
  echo "LỖI: không lấy được access_token từ /api/login." >&2
  exit 1
fi

echo "== 2/2 Gọi crawl-sync (tree_id $VGP_START_ID..$VGP_END_ID) =="
RESPONSE="$(curl -fsS -X POST "$BACKEND_URL/api/vietnamgiapha/crawl-sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"start_id\":$VGP_START_ID,\"end_id\":$VGP_END_ID,\"crawl_version\":\"v2\",\"skip_unchanged\":true,\"sync_db\":true,\"sync_pipeline\":true,\"attach_documents\":true}")"

echo "$RESPONSE" | python3 -c "
import json, sys
r = json.load(sys.stdin)
print(f\"crawl:  success={r['crawl_success']} skipped={r['crawl_skipped']} skipped_unchanged={r['crawl_skipped_unchanged']} errors={r['crawl_errors']}\")
print(f\"sync:   upserted={r['sync_upserted']} skipped={r['sync_skipped']} errors={r['sync_errors']}\")
print(f\"text:   attached={r['text_attached']} skipped={r['text_attach_skipped']} errors={r['text_attach_errors']}\")
if r['error_details']:
    print(f\"CHI TIẾT LỖI ({len(r['error_details'])}):\")
    for e in r['error_details'][:20]:
        print(' ', e)
total_errors = r['crawl_errors'] + r['sync_errors'] + r['text_attach_errors']
sys.exit(1 if total_errors > 0 else 0)
"
