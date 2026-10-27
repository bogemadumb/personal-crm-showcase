#!/bin/bash
# Ежедневный бэкап: дамп базы → шифрование → ротация по счёту → биение в пульс CRM.
# Восстановление:
#   openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in crm-<дата>.dump.enc -pass file:$KEYFILE \
#     | docker compose exec -T postgres pg_restore -U crm -d crm --no-owner
# Бэкап, который ни разу не восстанавливали, — не бэкап: раз в месяц восстанавливать в пустой контейнер.
set -euo pipefail

APP_DIR=${APP_DIR:-/opt/personal-crm}
OUT=${OUT:-$APP_DIR/backup}
KEYFILE=${KEYFILE:-$APP_DIR/.backup-key}
CRM_URL=${CRM_URL:-http://127.0.0.1:8080}
CRM_KEY_FILE=${CRM_KEY_FILE:-$APP_DIR/.crm-bridge-key}
STAMP=$(date +%Y-%m-%d)
# копий держим по счёту, а не по возрасту: дамп растёт вместе с базой, а диск сервера — узкое место
KEEP=3
# дамп меньше 70 % прошлого — упала схема или pg_dump отдал не всё; это сбой, а не «успех»
MIN_SHARE=70

beat() {
  [ -s "$CRM_KEY_FILE" ] || return 0
  # ключ читается из файла внутри curl (-H @file), в командную строку и журнал не попадает
  printf 'X-API-Key: %s\n' "$(cat "$CRM_KEY_FILE")" | curl -fsS -m 10 -o /dev/null -H @- -H 'Content-Type: application/json' \
    -d "{\"source\":\"server-backup\",\"title\":\"Ежедневный бэкап\",\"machine\":\"server\",\"expect_every\":90000,\"status\":\"$1\",\"note\":\"$2\"}" \
    "$CRM_URL/api/v2/feed/beat" || true
}
trap 'beat fail "сбой на строке $LINENO"' ERR

mkdir -p "$OUT"
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT
cd "$APP_DIR"
docker compose exec -T postgres pg_dump -U crm -d crm -Fc > "$TMP"

SIZE=$(stat -c %s "$TMP")
PREV=$(ls -1t "$OUT"/crm-*.dump.enc 2>/dev/null | head -1 || true)
if [ -n "$PREV" ] && [ ! -f "$OUT/.allow-small" ]; then
  PREV_SIZE=$(stat -c %s "$PREV")
  if [ $((SIZE * 100)) -lt $((PREV_SIZE * MIN_SHARE)) ]; then
    beat fail "дамп $SIZE байт, прошлый $PREV_SIZE — подозрительно мало"
    exit 1
  fi
fi
rm -f "$OUT/.allow-small"

openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -in "$TMP" -out "$OUT/crm-$STAMP.dump.enc" -pass "file:$KEYFILE"
ls -1t "$OUT"/crm-*.dump.enc | tail -n +$((KEEP + 1)) | xargs -r rm -f

beat ok "дамп $((SIZE / 1048576)) МБ"
