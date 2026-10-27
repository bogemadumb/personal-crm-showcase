#!/bin/sh
# Проверка после выкладки: health отвечает 200, SPA отдаёт index.html, API без входа закрыт.
set -eu
URL=${1:-http://127.0.0.1:8080}
curl -fsS -m 10 "$URL/api/v2/health" | grep -q '"ok":true' && echo "health ok"
curl -fsS -m 10 "$URL/" | grep -q '<div id="root">' && echo "spa ok"
code=$(curl -s -o /dev/null -w '%{http_code}' -m 10 "$URL/api/v2/tasks")
[ "$code" = "401" ] && echo "auth ok (401 без входа)" || { echo "auth FAIL: $code"; exit 1; }
