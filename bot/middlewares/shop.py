"""
Мидлварь aiogram, который гарантирует, что в каждом сообщении / коллбэке
есть уже зарегистрированный пользователь и сервис.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.exc import SQLAlchemyError

from shared.services import ShopService, shop_service


class ShopMiddleware(BaseMiddleware):
    """
    Подмешивает в хэндлеры:
      - shop_service: готовая фабрика сервиса
      - current_user: либо существующий User из БД, либо None
    """

    def __init__(self, service: ShopService | None = None) -> None:
        self.service = service or shop_service

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["shop_service"] = self.service
        user_obj = getattr(event, "from_user", None)
        data["current_user"] = None
        if user_obj is not None:
            try:
                data["current_user"] = await self.service.get_user_by_telegram(
                    user_obj.id
                )
            except SQLAlchemyError:
                data["current_user"] = None
        return await handler(event, data)
