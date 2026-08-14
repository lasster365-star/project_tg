"""Корзина: просмотр, изменение количества, удаление, оплата."""
from __future__ import annotations

from decimal import Decimal

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.keyboards.keyboards import (
    cart_lines_inline,
    cart_product_inline,
    cart_root_inline,
    pay_confirm_inline,
)
from bot.states import CartFSM
from bot.utils.visual import send_visual
from shared.config import config
from shared.models import OrderStatus
from shared.services import (
    EmptyCart,
    InsufficientFunds,
    UserNotFound,
)
from shared.utils import format_price

router = Router(name="cart")


# ---------- Открыть корзину ----------
@router.callback_query(F.data == "cart:open")
@router.message(F.text == "🛒 Корзина")
async def cart_open(event, shop_service, current_user, state: FSMContext) -> None:
    if state is not None:
        await state.clear()
    if current_user is None:
        if hasattr(event, "answer"):
            await event.answer("Сначала нажмите /start", show_alert=True)
        return
    cart = await shop_service.get_cart(current_user.telegram_id)
    if not cart.lines:
        await send_visual(
            event,
            caption="🛒 <b>Корзина пуста</b>\n\nОткройте каталог:",
            keyboard=cart_root_inline(config.twa_url),
            image="menu_cart.png",
            edit=getattr(event, "message", None) is not None,
        )
        return
    lines = cart.lines
    await send_visual(
        event,
        caption=_cart_caption(cart.lines, cart.total, current_user.balance),
        keyboard=cart_lines_inline(lines),
        image="menu_cart.png",
        edit=getattr(event, "message", None) is not None,
    )


def _cart_caption(lines, total: Decimal, balance: Decimal) -> str:
    items = "\n".join(
        f"• {line.product.title} × {line.quantity} = {format_price(line.subtotal)}"
        for line in lines
    )
    return (
        f"🛒 <b>Ваша корзина</b>\n\n"
        f"{items}\n\n"
        f"💵 Итого: <b>{format_price(total)}</b>\n"
        f"💰 Баланс: <b>{format_price(balance)}</b>"
    )


# ---------- Просмотр товара в корзине ----------
@router.callback_query(F.data.startswith("cart:view:"))
async def cart_view(call: CallbackQuery, shop_service, current_user, state: FSMContext) -> None:
    await call.answer()
    if current_user is None:
        return
    try:
        prod_id = int(call.data.split(":")[2])
    except (ValueError, IndexError):
        return
    cart = await shop_service.get_cart(current_user.telegram_id)
    line = next((l for l in cart.lines if l.product.id == prod_id), None)
    if line is None:
        await call.answer("Этого товара уже нет в корзине", show_alert=True)
        return
    await state.set_state(CartFSM.viewing_product)
    text = (
        f"📦 <b>{line.product.title}</b>\n\n"
        f"💵 Цена: {format_price(line.product.price)}\n"
        f"🔢 В корзине: {line.quantity}\n"
        f"💰 За позицию: {format_price(line.subtotal)}\n\n"
        f"{line.product.description}"
    )
    await send_visual(
        call,
        caption=text,
        keyboard=cart_product_inline(line.product.id),
        image=f"card_{line.product.kind.value}.png",
        edit=True,
    )


# ---------- Управление количеством ----------
@router.callback_query(F.data.startswith("cart:inc:"))
async def cart_inc(call: CallbackQuery, shop_service, current_user) -> None:
    await cart_qty(call, shop_service, current_user, +1)


@router.callback_query(F.data.startswith("cart:dec:"))
async def cart_dec(call: CallbackQuery, shop_service, current_user) -> None:
    await cart_qty(call, shop_service, current_user, -1)


async def cart_qty(call: CallbackQuery, shop_service, current_user, delta: int) -> None:
    await call.answer()
    if current_user is None:
        return
    try:
        prod_id = int(call.data.split(":")[2])
    except (ValueError, IndexError):
        return
    cart = await shop_service.get_cart(current_user.telegram_id)
    line = next((l for l in cart.lines if l.product.id == prod_id), None)
    if line is None:
        await call.answer("Этого товара уже нет в корзине", show_alert=True)
        return
    new_qty = max(1, line.quantity + delta)
    await shop_service.set_cart_qty(current_user.telegram_id, prod_id, new_qty)
    cart = await shop_service.get_cart(current_user.telegram_id)
    if not cart.lines:
        await send_visual(
            call,
            caption="🛒 <b>Корзина пуста</b>",
            keyboard=cart_root_inline(config.twa_url),
            image="menu_cart.png",
            edit=True,
        )
        return
    await send_visual(
        call,
        caption=_cart_caption(cart.lines, cart.total, current_user.balance),
        keyboard=cart_lines_inline(cart.lines),
        image="menu_cart.png",
        edit=True,
    )


@router.callback_query(F.data.startswith("cart:rm:"))
async def cart_remove(call: CallbackQuery, shop_service, current_user) -> None:
    await call.answer()
    if current_user is None:
        return
    try:
        prod_id = int(call.data.split(":")[2])
    except (ValueError, IndexError):
        return
    await shop_service.remove_from_cart(current_user.telegram_id, prod_id)
    cart = await shop_service.get_cart(current_user.telegram_id)
    if not cart.lines:
        await send_visual(
            call,
            caption="🛒 <b>Корзина пуста</b>",
            keyboard=cart_root_inline(config.twa_url),
            image="menu_cart.png",
            edit=True,
        )
        return
    await send_visual(
        call,
        caption=_cart_caption(cart.lines, cart.total, current_user.balance),
        keyboard=cart_lines_inline(cart.lines),
        image="menu_cart.png",
        edit=True,
    )


@router.callback_query(F.data == "cart:clear")
async def cart_clear(call: CallbackQuery, shop_service, current_user) -> None:
    await call.answer()
    if current_user is None:
        return
    await shop_service.clear_cart(current_user.telegram_id)
    await send_visual(
        call,
        caption="🛒 <b>Корзина очищена</b>",
        keyboard=cart_root_inline(config.twa_url),
        image="menu_cart.png",
        edit=True,
    )


# ---------- Оплата ----------
@router.callback_query(F.data == "cart:pay")
async def cart_pay(call: CallbackQuery, shop_service, current_user, state: FSMContext) -> None:
    await call.answer()
    if current_user is None:
        return
    try:
        order = await shop_service.create_order(current_user.telegram_id)
    except EmptyCart:
        await call.answer("Корзина пуста", show_alert=True)
        return
    await state.set_state(CartFSM.confirming_pay)
    text = (
        f"🧾 <b>Заказ #{order.id}</b>\n"
        f"💵 К оплате: <b>{format_price(order.total_amount)}</b>\n"
        f"💰 Баланс: <b>{format_price(current_user.balance)}</b>\n\n"
        "Подтвердите списание с баланса:"
    )
    await send_visual(
        call,
        caption=text,
        keyboard=pay_confirm_inline(order.id),
        image="menu_cart.png",
        edit=True,
    )


@router.callback_query(F.data.startswith("pay:ok:"))
async def pay_confirm(call: CallbackQuery, shop_service, current_user, state: FSMContext) -> None:
    await call.answer()
    if current_user is None:
        return
    try:
        order_id = int(call.data.split(":")[2])
    except (ValueError, IndexError):
        return
    try:
        order = await shop_service.pay_order(current_user.telegram_id, order_id)
    except InsufficientFunds:
        await call.answer("Недостаточно средств. Пополните баланс.", show_alert=True)
        await state.clear()
        return
    except (UserNotFound, ValueError) as exc:
        await call.answer(f"Ошибка: {exc}", show_alert=True)
        await state.clear()
        return
    await state.clear()
    text = (
        f"✅ <b>Оплата прошла!</b>\n\n"
        f"🧾 Заказ #{order.id}\n"
        f"💵 Списано: <b>{format_price(order.total_amount)}</b>\n\n"
        f"Покупка появилась в истории."
    )
    await send_visual(
        call,
        caption=text,
        keyboard=cart_root_inline(config.twa_url),
        image="menu_cart.png",
        edit=True,
    )


@router.callback_query(F.data.startswith("pay:no:"))
async def pay_decline(call: CallbackQuery, shop_service, current_user, state: FSMContext) -> None:
    await call.answer()
    if current_user is None:
        return
    try:
        order_id = int(call.data.split(":")[2])
    except (ValueError, IndexError):
        return
    try:
        await shop_service.cancel_order(current_user.telegram_id, order_id)
    except (UserNotFound, ValueError):
        pass
    await state.clear()
    await call.answer("Заказ отменён", show_alert=False)
    await cart_open(call, shop_service, current_user, state)
