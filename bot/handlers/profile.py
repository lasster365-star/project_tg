"""Личный кабинет: имя, рефералы, баланс, история, пополнение."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from bot.keyboards.keyboards import (
    profile_inline,
    topup_amounts_inline,
)
from bot.utils.visual import send_visual
from shared.config import config
from shared.utils import format_price

router = Router(name="profile")


PROFILE_TEXT = (
    "👤 <b>Личный кабинет</b>\n\n"
    "🆔 Имя: <b>{name}</b>\n"
    "🤝 Рефералов: <b>{refs}</b>\n"
    "💰 Баланс: <b>{balance}</b>\n"
    "🔗 Ваш код: <code>{ref}</code>"
)


async def render_profile(call_or_msg, shop_service, current_user) -> None:
    if current_user is None:
        if hasattr(call_or_msg, "answer"):
            await call_or_msg.answer("Сначала нажмите /start", show_alert=True)
        return
    refs = await shop_service.count_referrals(current_user.id)
    text = PROFILE_TEXT.format(
        name=current_user.full_name,
        refs=refs,
        balance=format_price(current_user.balance),
        ref=current_user.ref_code,
    )
    await send_visual(
        call_or_msg,
        caption=text,
        keyboard=profile_inline(config.twa_url),
        image="menu_profile.png",
        edit=getattr(call_or_msg, "message", None) is not None,
    )


@router.callback_query(F.data == "profile:open")
@router.message(F.text == "👤 Личный кабинет")
async def profile_open(event, shop_service, current_user) -> None:
    await render_profile(event, shop_service, current_user)


@router.callback_query(F.data == "profile:topup")
async def profile_topup(call: CallbackQuery, shop_service, current_user) -> None:
    await call.answer()
    if current_user is None:
        return
    await send_visual(
        call,
        caption="💳 <b>Пополнение баланса</b>\n\nВыберите сумму:",
        keyboard=topup_amounts_inline(),
        image="menu_profile.png",
        edit=True,
    )


@router.callback_query(F.data.startswith("topup:"))
async def topup_pick(call: CallbackQuery, shop_service, current_user) -> None:
    await call.answer()
    if current_user is None:
        return
    try:
        amount = int(call.data.split(":")[1])
    except (ValueError, IndexError):
        return
    user = await shop_service.topup_balance(
        current_user.telegram_id, amount, method="preset"
    )
    await call.answer(f"Баланс пополнен на {amount} ₽", show_alert=False)
    text = (
        f"✅ <b>Баланс пополнен на {amount} ₽</b>\n"
        f"💰 Новый баланс: <b>{format_price(user.balance)}</b>"
    )
    await send_visual(
        call,
        caption=text,
        keyboard=profile_inline(config.twa_url),
        image="menu_profile.png",
        edit=True,
    )


@router.callback_query(F.data == "profile:history")
async def profile_history(call: CallbackQuery, shop_service, current_user) -> None:
    await call.answer()
    if current_user is None:
        return
    orders = await shop_service.list_orders(current_user.telegram_id)
    if not orders:
        text = "📜 <b>История покупок</b>\n\nПока пусто — начните с каталога."
    else:
        lines = []
        for o in orders:
            status = {
                "pending": "⏳ ожидает",
                "paid": "✅ оплачен",
                "delivered": "📦 выдан",
                "cancelled": "❌ отменён",
            }.get(o.status.value, o.status.value)
            lines.append(
                f"🧾 №{o.id} · {format_price(o.total_amount)} · {status}"
            )
        text = "📜 <b>История покупок</b>\n\n" + "\n".join(lines)
    from bot.keyboards.keyboards import back_keyboard
    await send_visual(
        call,
        caption=text,
        keyboard=back_keyboard(),
        image="menu_profile.png",
        edit=True,
    )
