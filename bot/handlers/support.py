"""Кнопка «Поддержка» — текст со ссылкой на чат."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message

from bot.keyboards.keyboards import support_inline
from bot.utils.visual import send_visual
from shared.config import config

router = Router(name="support")


@router.message(F.text == "💬 Поддержка")
async def support_button(message: Message) -> None:
    await send_visual(
        message,
        caption=(
            "💬 <b>Поддержка</b>\n\n"
            f"Нажмите кнопку ниже — откроется чат с поддержкой ({config.support_chat_id}).\n"
            "Ответ обычно в течение 15 минут в рабочее время."
        ),
        keyboard=support_inline(),
        image="menu_support.png",
    )
