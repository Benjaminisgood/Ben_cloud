#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:9000}"
COOKIE_FILE="$(mktemp /tmp/benlab-automation-smoke.XXXXXX.cookie)"
USER_SUFFIX="$(date +%s)_$RANDOM"
USERNAME="${SMOKE_USERNAME:-e2e_${USER_SUFFIX}}"
PASSWORD="${SMOKE_PASSWORD:-E2E-pass-2026}"
DISPLAY_NAME="${SMOKE_DISPLAY_NAME:-E2E Bot}"

cleanup() {
  rm -f "$COOKIE_FILE"
}
trap cleanup EXIT

fail() {
  echo "[automation-smoke] ERROR: $*" >&2
  exit 1
}

echo "[automation-smoke] BASE_URL=$BASE_URL"

health_json="$(curl -fsS "$BASE_URL/health")" || fail "health check failed"
[ "$health_json" = '{"status":"ok"}' ] || fail "unexpected /health response: $health_json"
echo "[automation-smoke] health ok"

register_status="$(
  curl -sS -o /dev/null -w '%{http_code}' -c "$COOKIE_FILE" \
    -X POST "$BASE_URL/register" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode "name=$DISPLAY_NAME" \
    --data-urlencode "username=$USERNAME" \
    --data-urlencode "password=$PASSWORD" \
    --data-urlencode 'contact=automation-smoke' \
    --data-urlencode 'next=/'
)"
if [ "$register_status" != "303" ]; then
  fail "register expected 303, got $register_status"
fi
echo "[automation-smoke] register ok (303) username=$USERNAME"

account_after_register="$(curl -fsS -b "$COOKIE_FILE" "$BASE_URL/api/account")" || fail "account check after register failed"
registered_user="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["current_user"]["username"])' <<< "$account_after_register")"
[ "$registered_user" = "$USERNAME" ] || fail "account mismatch after register: expected $USERNAME, got $registered_user"
echo "[automation-smoke] account after register ok"

create_post_resp="$(
  curl -fsS -b "$COOKIE_FILE" \
    -X POST "$BASE_URL/api/records" \
    -H 'Content-Type: application/json' \
    -d '{"text":"Benlab automation smoke post","visibility":"private","tags":["nanobot","smoke"]}'
)" || fail "create post failed"
record_id="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<< "$create_post_resp")"
[ -n "$record_id" ] || fail "missing record_id"
echo "[automation-smoke] create post ok id=$record_id"

list_posts_resp="$(curl -fsS -b "$COOKIE_FILE" "$BASE_URL/api/records?limit=10")" || fail "list posts failed"
python3 - <<'PY' "$record_id" "$list_posts_resp"
import json
import sys

record_id = int(sys.argv[1])
payload = json.loads(sys.argv[2])
ids = [int(row["id"]) for row in payload.get("items", [])]
if record_id not in ids:
    raise SystemExit("record id not found in list")
PY

echo "[automation-smoke] list posts contains id=$record_id"

create_comment_resp="$(
  curl -fsS -b "$COOKIE_FILE" \
    -X POST "$BASE_URL/api/records/$record_id/comments" \
    -H 'Content-Type: application/json' \
    -d '{"body":"automation smoke comment"}'
)" || fail "create comment failed"
comment_id="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<< "$create_comment_resp")"
[ -n "$comment_id" ] || fail "missing comment_id"
echo "[automation-smoke] create comment ok id=$comment_id"

list_comments_resp="$(curl -fsS -b "$COOKIE_FILE" "$BASE_URL/api/records/$record_id/comments")" || fail "list comments failed"
python3 - <<'PY' "$comment_id" "$list_comments_resp"
import json
import sys

comment_id = int(sys.argv[1])
payload = json.loads(sys.argv[2])
ids = [int(row["id"]) for row in payload.get("items", [])]
if comment_id not in ids:
    raise SystemExit("comment id not found in list")
PY

echo "[automation-smoke] list comments contains id=$comment_id"

delete_status="$(curl -sS -o /dev/null -w '%{http_code}' -b "$COOKIE_FILE" -X DELETE "$BASE_URL/api/records/$record_id")"
[ "$delete_status" = "204" ] || fail "delete post expected 204, got $delete_status"
echo "[automation-smoke] delete post ok (204)"

logout_status="$(curl -sS -o /dev/null -w '%{http_code}' -b "$COOKIE_FILE" "$BASE_URL/logout")"
[ "$logout_status" = "303" ] || fail "logout expected 303, got $logout_status"
echo "[automation-smoke] logout ok (303)"

login_status="$(
  curl -sS -o /dev/null -w '%{http_code}' -c "$COOKIE_FILE" \
    -X POST "$BASE_URL/login" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode "username=$USERNAME" \
    --data-urlencode "password=$PASSWORD" \
    --data-urlencode 'next=/'
)"
[ "$login_status" = "303" ] || fail "login expected 303, got $login_status"
echo "[automation-smoke] login ok (303)"

account_after_login="$(curl -fsS -b "$COOKIE_FILE" "$BASE_URL/api/account")" || fail "account check after login failed"
login_user="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["current_user"]["username"])' <<< "$account_after_login")"
[ "$login_user" = "$USERNAME" ] || fail "account mismatch after login: expected $USERNAME, got $login_user"
echo "[automation-smoke] account after login ok"

echo "[automation-smoke] PASS"
