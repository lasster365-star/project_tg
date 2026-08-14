#!/usr/bin/env bash
# Запуск сайта (FastAPI) и бота (aiogram).
# Использование: ./run.sh
set -e

cd "$(dirname "$0")"

if [ -f .env ]; then
  set -a; . ./.env; set +a
fi

# Подтянуть код/зависимости, если репо свежее
if [ -d .git ]; then
  git pull --rebase --autostash >/dev/null 2>&1 || true
fi

# Сидер: создаст таблицы (если их нет) и зальёт стартовый каталог.
# Идемпотентен — повторный запуск ничего не дублирует.
echo "==> Сидирование БД"
PYTHONPATH=. .venv/bin/python -m scripts.seed_db || true

# Health-чек API и старт бота
PYTHONPATH=. .venv/bin/python -m webapp.app &
SITE_PID=$!

# Ждём, пока API поднимется
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS "http://127.0.0.1:${PORT:-8080}/api/public/health" >/dev/null; then
    echo "==> API готов"
    break
  fi
  sleep 1
done

PYTHONPATH=. exec .venv/bin/python -m bot.bot
