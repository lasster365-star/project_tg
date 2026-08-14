"""Меню магазина: категории → товары → карточка → в корзину."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.keyboards.keyboards import (
    categories_inline,
    product_card_inline,
    products_inline,
)
from bot.utils.visual import send_visual
from shared.config import config
from shared.services import (
    CartLine,
    EmptyCart,
    InsufficientFunds,
    UserNotFound,
)

router = Router(name="shop")


# Назад / В главное меню — общие навигационные действия
@router.callback_query(F.data == "nav:home")
async def nav_home(call: CallbackQuery, shop_service) -> None:
    from bot.keyboards.keyboards import main_menu_keyboard

    await call.answer()
    text = (
        "🏠 <b>Главное меню</b>\n\n"
        "🛍 Каталог — нажмите в Mini App для удобной навигации.\n"
        "👤 В личном кабинете — пополнение баланса и история.\n"
        "💬 Поддержка всегда рядом."
    )
    await send_visual(
        call,
        caption=text,
        keyboard=None,
        image="menu_main.png",
        edit=True,
    )
    await call.message.answer(
        "Вы в главном меню.",
        reply_markup=main_menu_keyboard(config.twa_url),
    )


@router.callback_query(F.data == "nav:back")
async def nav_back(call: CallbackQuery, shop_service) -> None:
    """Универсальный «Назад»: возвращает к списку категорий."""
    await call.answer()
    cats = await shop_service.list_categories()
    await send_visual(
        call,
        caption="<b>Магазин</b>\nВыберите категорию:",
        keyboard=categories_inline(cats, config.twa_url),
        image="menu_main.png",
        edit=True,
    )


# ---------- Категория → список товаров ----------
@router.callback_query(F.data.startswith("shop:cat:"))
async def shop_category(call: CallbackQuery, shop_service) -> None:
    await call.answer()
    try:
        cat_id = int(call.data.split(":")[2])
    except (ValueError, IndexError):
        return
    category = await shop_service.get_category(cat_id)
    if category is None:
        await call.answer("Категория не найдена", show_alert=True)
        return
    products = await shop_service.list_products(category_id=cat_id)
    if not products:
        await send_visual(
            call,
            caption=f"<b>{category.title}</b>\nПока пусто.",
            keyboard=None,
            image=f"menu_{category.kind.value}.png",
            edit=True,
        )
        return
    await send_visual(
        call,
        caption=f"<b>{category.title}</b>\n{len(products)} товаров:",
        keyboard=products_inline(products, config.twa_url),
        image=f"menu_{category.kind.value}.png",
        edit=True,
    )


# ---------- Карточка товара ----------
@router.callback_query(F.data.startswith("shop:prod:"))
async def shop_product(call: CallbackQuery, shop_service, current_user) -> None:
    await call.answer()
    try:
        prod_id = int(call.data.split(":")[2])
    except (ValueError, IndexError):
        return
    product = await shop_service.get_product(prod_id)
    if product is None:
        await call.answer("Товар не найден", show_alert=True)
        return
    in_cart = 0
    if current_user is not None:
        cart = await shop_service.get_cart(current_user.telegram_id)
        for line in cart.lines:
            if line.product.id == product.id:
                in_cart = line.quantity
                break
    text = (
        f"🎮 <b>{product.title}</b>\n\n"
        f"💵 {product.price} ₽\n"
        f"⭐ {product.rating:.2f}  ·  💬 {product.reviews_count} отзывов\n\n"
        f"{product.description}\n\n"
        f"📦 В наличии: {'∞' if product.stock < 0 else product.stock}"
    )
    await send_visual(
        call,
        caption=text,
        keyboard=product_card_inline(product.id, in_cart),
        image=f"card_{product.kind.value}.png",
        edit=True,
    )


# ---------- Добавить в корзину ----------
@router.callback_query(F.data.startswith("cart:add:"))
async def cart_add(call: CallbackQuery, shop_service, current_user) -> None:
    if current_user is None:
        await call.answer("Сначала нажмите /start", show_alert=True)
        return
    try:
        prod_id = int(call.data.split(":")[2])
    except (ValueError, IndexError):
        return
    try:
        qty = await shop_service.add_to_cart(current_user.telegram_id, prod_id, 1)
    except UserNotFound:
        await call.answer("Сначала нажмите /start", show_alert=True)
        return
    except ValueError:
        await call.answer("Товар недоступен", show_alert=True)
        return
    await call.answer(f"Добавлено. В корзине: {qty}", show_alert=False)
    product = await shop_service.get_product(prod_id)
    if product is not None:
        text = (
            f"🎮 <b>{product.title}</b>\n\n"
            f"💵 {product.price} ₽\n"
            f"⭐ {product.rating:.2f}  ·  💬 {product.reviews_count} отзывов\n\n"
            f"{product.description}"
        )
        await send_visual(
            call,
            caption=text,
            keyboard=product_card_inline(product.id, qty),
            image=f"card_{product.kind.value}.png",
            edit=True,
        )
