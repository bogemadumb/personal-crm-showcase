#!/bin/sh
# Создаёт случайные секреты для docker compose, если их ещё нет. Значения не печатаются.
# Каталог — 700 (с хоста их читает только владелец), сами файлы — 644: compose монтирует их как есть,
# а API в контейнере работает не от root.
set -eu
cd "$(dirname "$0")/.."
mkdir -p secrets
chmod 700 secrets
for name in pg_password jwt_secret; do
  [ -s "secrets/$name" ] || openssl rand -hex 32 > "secrets/$name"
  chmod 644 "secrets/$name"
done
# .env с ключом для MCP и сквозных тестов (ключ с ролью agent заводится при первом старте базы)
if [ ! -f .env ]; then
  umask 077
  sed "s/^DEMO_API_KEY=.*/DEMO_API_KEY=crm_$(openssl rand -hex 24)/" .env.example > .env
fi
echo "secrets ready: $(ls secrets | tr '\n' ' '); .env: DEMO_API_KEY задан"
