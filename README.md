# TG Shop Bot + Mini App

Телеграм-магазин: бот на **aiogram 3** + **SQLAlchemy 2 (async)** и Mini App на **FastAPI + vanilla JS** (одно приложение — статика + API).

## Что есть

- 🛍 **Магазин** с 4 категориями: подписки, аккаунты, ключи игр, прокат.
- 👤 **Личный кабинет**: имя, рефералы, баланс, история покупок, пополнения.
- 🛒 **Корзина** с просмотром товара, ±/удалить, оплатой через бот.
- 💬 **Поддержка** — переход в чат.
- 🌐 **Mini App** под корнем `/` — синхронизирован с ботом по `initData` (HMAC-SHA256).
  Кнопка «💳 Оплатить» в Mini App отправляет пользователя в бота для подтверждения, бот списывает баланс и фиксирует заказ в той же БД.
- 📦 Под каждое сообщение бота — слот для изображения (`twa/assets/`), в коде уже есть кэширование `file_id`.

## Структура

```
bot/               — aiogram-бот (handlers, FSM, клавиатуры)
webapp/            — FastAPI-приложение (API + Mini App статика)
shared/            — общие модели, сервисы, валидация initData
scripts/seed_db.py — сидер категорий/товаров
twa/               — Mini App (index.html, css, js, assets/)
install.sh         — установка на чистый Debian/Ubuntu
run.sh             — запуск API и бота
Procfile / railway.json — деплой на Railway
```

## Запуск локально

```bash
cp .env.example .env  # заполните BOT_TOKEN и TWA_URL
./install.sh
./run.sh
```

`install.sh` поставит Python 3.11+, venv, зависимости и прогонит сидер.  
`run.sh` поднимет API, проверит `/api/health` и запустит бота.

## Деплой на Railway

1. Залейте репозиторий (см. ниже шаги `git push` через HTTPS+PAT).
2. В Railway → New Project → Deploy from GitHub → выбрать `project_tg`.
3. В Variables задайте:
   - `BOT_TOKEN` — токен от @BotFather.
   - `TWA_URL` — `https://feisty-cooperation-production-4c04.up.railway.app`.
   - `DATABASE_URL` — Railway автоматически подставит, если добавить Postgres-плагин.
4. После деплоя откройте в Telegram бота и нажмите **🛍 Открыть магазин**.

`Procfile` запускает API как web и бот как worker; `run.sh` — единая команда для web-инстанса.

## Синхронизация «сайт ↔ бот»

- `twa/js/api.js` берёт `window.Telegram.WebApp.initData` и шлёт в `Authorization: tma <initData>`.
- Сервер (`site/deps/auth.py`) проверяет подпись, поднимает/создаёт `User`, отдаёт данные.
- Заказы создаются через `/api/orders/checkout`; в Mini App после нажатия «Оплатить» пользователь открывает бота через `?startapp=pay_<id>`, бот списывает баланс и оставляет запись в `orders`.
