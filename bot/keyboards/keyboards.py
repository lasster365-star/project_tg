"""
Клавиатуры магазина. Под каждое меню зарезервирован слот для изображения
(вызывающий код шлёт фото + текст + клавиатуру).
"""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)


def main_menu_keyboard(twa_url: str) -> ReplyKeyboardMarkup:
    """Главное меню бота (replay keyboard). Сверху большая кнопка WebApp."""
    webapp = WebAppInfo(url=twa_url)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍 Открыть магазин", web_app=webapp)],
            [
                KeyboardButton(text="👤 Личный кабинет"),
                KeyboardButton(text="🛒 Корзина"),
            ],
            [
                KeyboardButton(text="💬 Поддержка"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Магазин цифровых товаров",
    )


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:back")],
        ]
    )


def to_main_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛍 В магазин (Mini App)",
                    web_app=WebAppInfo(url=""),  # переопределяется ниже
                )
            ],
            [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="nav:home")],
        ]
    )


def categories_inline(categories, twa_url: str) -> InlineKeyboardMarkup:
    rows = []
    for cat in categories:
        rows.append(
            [
                InlineKeyboardButton(
                    text=cat.title,
                    callback_data=f"shop:cat:{cat.id}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="🛍 Открыть в Mini App",
                web_app=WebAppInfo(url=twa_url),
            )
        ]
    )
    rows.append(
        [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="nav:home")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def products_inline(products, twa_url: str) -> InlineKeyboardMarkup:
    rows = []
    for p in products:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{p.title}  ·  {p.price} ₽",
                    callback_data=f"shop:prod:{p.id}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="🛍 Открыть в Mini App",
                web_app=WebAppInfo(url=twa_url),
            )
        ]
    )
    rows.append(
        [InlineKeyboardButton(text="⬅️ К категориям", callback_data="nav:back")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_card_inline(product_id: int, in_cart: int) -> InlineKeyboardMarkup:
    rows = []
    if in_cart > 0:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"✅ В корзине · {in_cart}",
                    callback_data="cart:open",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="➕ В корзину", callback_data=f"cart:add:{product_id}"
            ),
            InlineKeyboardButton(
                text="🛒 Открыть корзину", callback_data="cart:open"
            ),
        ]
    )
    rows.append(
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:back")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cart_root_inline(twa_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Продолжить покупки", callback_data="nav:back")],
            [InlineKeyboardButton(text="💳 Оплатить корзину", callback_data="cart:pay")],
            [
                InlineKeyboardButton(
                    text="🛍 Открыть в Mini App",
                    web_app=WebAppInfo(url=twa_url),
                )
            ],
            [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="nav:home")],
        ]
    )


def cart_lines_inline(lines) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for line in lines:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"📦 {line.product.title}",
                    callback_data=f"cart:view:{line.product.id}",
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="💳 Оплатить", callback_data="cart:pay")]
    )
    rows.append(
        [InlineKeyboardButton(text="🧹 Очистить корзину", callback_data="cart:clear")]
    )
    rows.append(
        [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="nav:home")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cart_product_inline(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➖ Уменьшить", callback_data=f"cart:dec:{product_id}"
                ),
                InlineKeyboardButton(
                    text="➕ Добавить", callback_data=f"cart:inc:{product_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить", callback_data=f"cart:rm:{product_id}"
                )
            ],
            [InlineKeyboardButton(text="⬅️ В корзину", callback_data="cart:open")],
        ]
    )


def profile_inline(twa_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="profile:topup")],
            [InlineKeyboardButton(text="📜 История покупок", callback_data="profile:history")],
            [
                InlineKeyboardButton(
                    text="🛍 Открыть магазин",
                    web_app=WebAppInfo(url=twa_url),
                )
            ],
            [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="nav:home")],
        ]
    )


def topup_amounts_inline() -> InlineKeyboardMarkup:
    rows = []
    presets = [300, 500, 1000, 2000, 5000]
    for amount in presets:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"Пополнить на {amount} ₽",
                    callback_data=f"topup:{amount}",
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="⬅️ В личный кабинет", callback_data="profile:open")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pay_confirm_inline(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить оплату", callback_data=f"pay:ok:{order_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отменить", callback_data=f"pay:no:{order_id}"
                ),
            ]
        ]
    )


def support_inline() -> InlineKeyboardMarkup:
    """Поддержка — просто ссылка на чат/пользователя."""
    from shared.config import config

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Написать в поддержку",
                    url=f"https://t.me/{config.support_chat_id.lstrip('@')}",
                )
            ],
            [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="nav:home")],
        ]
    )


def back_to_main_reply() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ В главное меню")]],
        resize_keyboard=True,
    )
