"""
Сервис отправки «фото + подпись + клавиатура» с кэшированием file_id.
"""
from __future__ import annotations

import os
from pathlib import Path

from aiogram.exceptions import TelegramAPIError
from aiogram.types import (
    FSInputFile,
    InputMediaPhoto,
    InlineKeyboardMarkup,
    Message,
)

from shared.services import ShopService
from shared.config import config


ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = ROOT / "twa" / "assets"

# (относительный путь в assets/, описание, подпись/пусто)
GALLERY: dict[str, str] = {
    "logo.png": "Логотип магазина",
    "menu_main.png": "Главное меню магазина",
    "menu_profile.png": "Личный кабинет",
    "menu_cart.png": "Корзина",
    "menu_support.png": "Поддержка",
    "menu_subscriptions.png": "Подписки",
    "menu_accounts.png": "Аккаунты",
    "menu_keys.png": "Ключи игр",
    "menu_rental.png": "Прокат",
    "card_default.png": "Карточка товара",
}


def asset_path(name: str) -> Path | None:
    p = ASSETS_DIR / name
    return p if p.exists() else None


async def send_visual(
    message_or_call,
    *,
    caption: str,
    keyboard: InlineKeyboardMarkup | None = None,
    image: str | None = "logo.png",
    edit: bool = False,
) -> Message | None:
    """
    Универсальная отправка «картинка + подпись + клавиатура».
    image: имя файла из twa/assets/. Если файла нет — Telegram не получит фото (только текст).
    edit=True — редактируем текущее сообщение (call.message).
    """
    chat_id = message_or_call.message.chat.id if hasattr(message_or_call, "message") else message_or_call.chat.id
    bot = message_or_call.bot if hasattr(message_or_call, "bot") else (message_or_call.message.bot if hasattr(message_or_call, "message") else message_or_call.bot)
    service: ShopService | None = getattr(message_or_call, "shop_service", None)

    async def _send_photo(photo, caption_text: str, kb):
        if edit and hasattr(message_or_call, "message"):
            try:
                # editMessageMedia поддерживает только медиа; клавиатуру обновим вторым вызовом
                from aiogram.types import InlineKeyboardMarkup

                media = InputMediaPhoto(media=photo, caption=caption_text)
                await bot.edit_message_media(
                    media=media,
                    chat_id=chat_id,
                    message_id=message_or_call.message.message_id,
                    reply_markup=kb,
                )
                return
            except TelegramAPIError:
                pass
        return await bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=caption_text,
            reply_markup=kb,
        )

    image_file: Path | None = asset_path(image) if image else None
    if image_file is None:
        # шлём просто текстом, клавиатура останется inline
        if edit and hasattr(message_or_call, "message"):
            try:
                return await bot.edit_message_text(
                    text=caption,
                    chat_id=chat_id,
                    message_id=message_or_call.message.message_id,
                    reply_markup=keyboard,
                )
            except TelegramAPIError:
                pass
        return await bot.send_message(
            chat_id=chat_id, text=caption, reply_markup=keyboard
        )

    # Используем кэш file_id
    cached_id: str | None = None
    if service is not None:
        cached_id = await service.get_image_file_id(str(image_file))
    try:
        if cached_id:
            result_msg = await _send_photo(cached_id, caption, keyboard)
        else:
            result_msg = await _send_photo(FSInputFile(str(image_file)), caption, keyboard)
            # Сохраним file_id для следующего раза
            if service is not None and result_msg is not None and result_msg.photo:
                largest = result_msg.photo[-1].file_id
                if largest:
                    await service.save_image_file_id(str(image_file), largest)
    except TelegramAPIError:
        # Если что-то с медиа — отправим текстом
        if edit and hasattr(message_or_call, "message"):
            try:
                return await bot.edit_message_text(
                    text=caption,
                    chat_id=chat_id,
                    message_id=message_or_call.message.message_id,
                    reply_markup=keyboard,
                )
            except TelegramAPIError:
                pass
        return await bot.send_message(
            chat_id=chat_id, text=caption, reply_markup=keyboard
        )
    return None
