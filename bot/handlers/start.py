"""`/start` и регистрация/рефералы."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards.keyboards import main_menu_keyboard
from bot.utils.visual import send_visual
from shared.config import config

router = Router(name="start")


def _extract_ref_payload(args: str | None) -> str | None:
    if not args:
        return None
    for token in args.split():
        if token.startswith("ref_"):
            return token[4:]
    return None


@router.message(CommandStart(deep_link=True))
@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, shop_service, state: FSMContext) -> None:
    await state.clear()
    ref_code = _extract_ref_payload(command.args)
    full_name = (message.from_user.full_name or "").strip() or "Игрок"
    await shop_service.get_or_create_user(
        telegram_id=message.from_user.id,
        full_name=full_name,
        username=message.from_user.username,
        referrer_code=ref_code,
    )

    text = (
        "👋 Привет, <b>{name}</b>!\n\n"
        "Я — бот-магазин цифровых товаров: подписки, ключи игр, аккаунты и прокат.\n"
        "Нажмите кнопку <b>🛍 Открыть магазин</b> или используйте меню ниже."
    ).format(name=full_name)

    await send_visual(
        message,
        caption=text,
        keyboard=None,                # reply-кнопка уйдёт отдельно
        image="menu_main.png",
        edit=False,
    )
    await message.answer(
        "Главное меню 👇",
        reply_markup=main_menu_keyboard(config.twa_url),
    )
