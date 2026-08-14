#!/usr/bin/env bash
# Установка зависимостей на чистый Debian/Ubuntu.
# Использование: ./install.sh
set -e

cd "$(dirname "$0")"

echo "==> apt: системные пакеты"
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git curl

echo "==> venv + pip-зависимости"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

echo "==> инициализация БД"
PYTHONPATH=. .venv/bin/python -m scripts.seed_db || true

echo "==> готово. Скопируйте .env.example в .env и заполните BOT_TOKEN."
