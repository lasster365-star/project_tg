"""
Сидер каталога: 4 категории (подписки, аккаунты, ключи, прокат).
Цены — ориентиры из открытых источников (Steam, официальные страницы подписок).
Запускается скриптом `python -m scripts.seed_db`.

После установки таблиц этот скрипт можно дёргать из install.sh, чтобы прод
сразу был с непустым витриной.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from shared.db import get_session_factory, init_db
from shared.models import Category, Product, ProductKind


CATEGORIES: list[dict] = [
    {
        "slug": "subscriptions",
        "kind": ProductKind.subscription,
        "title": "🎮 Подписки",
        "description": "Доступ к сотням игр по подписке.",
        "sort": 10,
    },
    {
        "slug": "accounts",
        "kind": ProductKind.account,
        "title": "👤 Аккаунты",
        "description": "Готовые аккаунты с привязкой и инструкцией.",
        "sort": 20,
    },
    {
        "slug": "keys",
        "kind": ProductKind.key,
        "title": "🔑 Ключи игр",
        "description": "Цифровые ключи Steam и других платформ.",
        "sort": 30,
    },
    {
        "slug": "rental",
        "kind": ProductKind.rental,
        "title": "🕒 Прокат",
        "description": "Доступ к играм на ограниченный срок.",
        "sort": 40,
    },
]


PRODUCTS: list[dict] = [
    # ----- Подписки -----
    {
        "category": "subscriptions",
        "title": "Steam — Подарочные карты 1000 ₽",
        "description": "Цифровой код для пополнения кошелька Steam. Регион: Россия.",
        "price": "999.00",
        "rating": 4.9,
        "reviews": 312,
        "stock": 50,
    },
    {
        "category": "subscriptions",
        "title": "Xbox Game Pass Ultimate — 1 месяц",
        "description": "Доступ к сотням игр на ПК и Xbox, EA Play в комплекте.",
        "price": "799.00",
        "rating": 4.8,
        "reviews": 245,
        "stock": 35,
    },
    {
        "category": "subscriptions",
        "title": "PlayStation Plus Extra — 1 месяц",
        "description": "Каталог из сотен игр, мультиплеер, облачные сохранения.",
        "price": "749.00",
        "rating": 4.7,
        "reviews": 198,
        "stock": 30,
    },
    {
        "category": "subscriptions",
        "title": "EA Play — 12 месяцев",
        "description": "Годовая подписка EA, доступ к играм издательства.",
        "price": "1799.00",
        "rating": 4.6,
        "reviews": 112,
        "stock": 20,
    },
    {
        "category": "subscriptions",
        "title": "Ubisoft+ — 3 месяца",
        "description": "Каталог Ubisoft Classics, доступ к новинкам.",
        "price": "1199.00",
        "rating": 4.5,
        "reviews": 76,
        "stock": 25,
    },
    # ----- Аккаунты -----
    {
        "category": "accounts",
        "title": "Steam-аккаунт с библиотекой (10+ игр)",
        "description": "Готовый аккаунт с играми уровня CS2, Dota 2, GTA V и др.",
        "price": "2499.00",
        "rating": 4.6,
        "reviews": 89,
        "stock": 12,
    },
    {
        "category": "accounts",
        "title": "Аккаунт Steam с балансом 2000 ₽",
        "description": "Уже пополненный кошелёк, привязка к РФ-региону.",
        "price": "2199.00",
        "rating": 4.7,
        "reviews": 60,
        "stock": 8,
    },
    {
        "category": "accounts",
        "title": "Аккаунт PSN с играми PS4/PS5",
        "description": "Регион: Турция. Инструкция по смене данных прилагается.",
        "price": "3299.00",
        "rating": 4.5,
        "reviews": 41,
        "stock": 10,
    },
    {
        "category": "accounts",
        "title": "Аккаунт Epic Games (Fortnite, GTA V)",
        "description": "Стандартный набор популярных игр Epic.",
        "price": "1599.00",
        "rating": 4.6,
        "reviews": 73,
        "stock": 15,
    },
    # ----- Ключи -----
    {
        "category": "keys",
        "title": "Baldur's Gate 3 (Steam, RU/CIS)",
        "description": "Активация в Steam для региона RU/CIS.",
        "price": "1499.00",
        "rating": 4.9,
        "reviews": 502,
        "stock": 40,
    },
    {
        "category": "keys",
        "title": "Cyberpunk 2077 (Steam, RU/CIS)",
        "description": "Цифровой ключ, активация в Steam.",
        "price": "999.00",
        "rating": 4.8,
        "reviews": 381,
        "stock": 28,
    },
    {
        "category": "keys",
        "title": "Hogwarts Legacy (Steam, GLOBAL)",
        "description": "Глобальный ключ, без региональных ограничений.",
        "price": "1199.00",
        "rating": 4.7,
        "reviews": 224,
        "stock": 30,
    },
    {
        "category": "keys",
        "title": "Elden Ring (Steam, GLOBAL)",
        "description": "FromSoftware Action-RPG, цифровой ключ.",
        "price": "1599.00",
        "rating": 4.9,
        "reviews": 410,
        "stock": 22,
    },
    {
        "category": "keys",
        "title": "The Witcher 3 (GOG, GLOBAL)",
        "description": "Цифровой ключ для GOG-аккаунта.",
        "price": "499.00",
        "rating": 4.9,
        "reviews": 612,
        "stock": 50,
    },
    {
        "category": "keys",
        "title": "Red Dead Redemption 2 (Steam)",
        "description": "Цифровой ключ для Steam, RU/CIS.",
        "price": "699.00",
        "rating": 4.8,
        "reviews": 297,
        "stock": 35,
    },
    {
        "category": "keys",
        "title": "God of War (Steam, GLOBAL)",
        "description": "История Кратоса и Атрея, цифровой ключ.",
        "price": "1299.00",
        "rating": 4.8,
        "reviews": 215,
        "stock": 18,
    },
    # ----- Прокат -----
    {
        "category": "rental",
        "title": "Прокат Dota 2 Plus — 7 дней",
        "description": "Подписка Dota Plus на аккаунте на 7 дней.",
        "price": "199.00",
        "rating": 4.5,
        "reviews": 88,
        "stock": -1,
        "rental_days": 7,
    },
    {
        "category": "rental",
        "title": "Прокат PS Plus Extra — 14 дней",
        "description": "Доступ к каталогу PlayStation Plus Extra на 14 дней.",
        "price": "449.00",
        "rating": 4.4,
        "reviews": 42,
        "stock": -1,
        "rental_days": 14,
    },
    {
        "category": "rental",
        "title": "Прокат Xbox Game Pass Ultimate — 30 дней",
        "description": "Game Pass Ultimate на 30 дней с сохранением прогресса.",
        "price": "799.00",
        "rating": 4.7,
        "reviews": 110,
        "stock": -1,
        "rental_days": 30,
    },
    {
        "category": "rental",
        "title": "Прокат EA Play — 7 дней",
        "description": "Каталог EA на 7 дней.",
        "price": "179.00",
        "rating": 4.3,
        "reviews": 33,
        "stock": -1,
        "rental_days": 7,
    },
]


async def seed() -> None:
    await init_db()
    factory = get_session_factory()
    async with factory() as session:
        # 1) Категории
        slug_to_id: dict[str, int] = {}
        for cat in CATEGORIES:
            existing = await session.scalar(
                select(Category).where(Category.slug == cat["slug"])
            )
            if existing is None:
                obj = Category(
                    slug=cat["slug"],
                    kind=cat["kind"],
                    title=cat["title"],
                    description=cat["description"],
                    sort=cat["sort"],
                )
                session.add(obj)
                await session.flush()
                slug_to_id[cat["slug"]] = obj.id
            else:
                slug_to_id[cat["slug"]] = existing.id
                existing.title = cat["title"]
                existing.description = cat["description"]
                existing.sort = cat["sort"]

        # 2) Продукты: добавляем только те, которых ещё нет по title
        existing_titles = set(
            (await session.scalars(select(Product.title))).all()
        )
        for p in PRODUCTS:
            if p["title"] in existing_titles:
                continue
            session.add(
                Product(
                    category_id=slug_to_id[p["category"]],
                    title=p["title"],
                    description=p["description"],
                    price=Decimal(p["price"]),
                    kind=(
                        next(c for c in CATEGORIES if c["slug"] == p["category"])[
                            "kind"
                        ]
                    ),
                    rental_days=p.get("rental_days"),
                    stock=p.get("stock", -1),
                    rating=Decimal(str(p.get("rating", 4.8))),
                    reviews_count=int(p.get("reviews", 0)),
                    is_active=True,
                )
            )
        await session.commit()


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed())
