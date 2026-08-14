"""
Аутентификация по initData для эндпоинтов /api/*.

initData приходит одним из способов:
- `Authorization: tma <initData>`
- `X-Init-Data: <initData>`
- `Authorization: <initData>` (без схемы)

Браузерный preview Mini App не имеет initData → middleware отдаёт 200 OK с
`tg_user=None`, чтобы клиент мог показать свою заглушку, а не ложное «сессия истекла».
"""
from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from shared.config import config
from shared.models import User
from shared.services import ShopService, shop_service
from shared.tma_auth import TelegramUser, extract_user, validate_init_data

log = logging.getLogger("webapp.auth")


def _extract_init_data(authorization: Optional[str], x_init_data: Optional[str]) -> str:
    if x_init_data:
        return x_init_data
    if not authorization:
        return ""
    parts = authorization.split(None, 1)
    if len(parts) == 2 and parts[0].lower() in {"tma", "bearer"}:
        return parts[1]
    if len(parts) == 1:
        return parts[0]
    return ""


async def try_get_tg_user(
    authorization: Annotated[Optional[str], Header()] = None,
    x_init_data: Annotated[Optional[str], Header(alias="X-Init-Data")] = None,
) -> TelegramUser | None:
    """
    Best-effort: возвращает TelegramUser или None, если initData отсутствует.
    Без исключения — для браузерного preview.
    """
    raw = _extract_init_data(authorization, x_init_data)
    if not raw:
        return None
    try:
        parsed = validate_init_data(
            raw, config.bot_token, ttl_seconds=config.initdata_ttl_seconds
        )
    except ValueError as exc:
        log.warning("initData validation failed: %s", exc)
        return None
    return extract_user(parsed)


async def require_tg_user(
    tg_user: Annotated[Optional[TelegramUser], Depends(try_get_tg_user)],
) -> TelegramUser:
    if tg_user is None:
        raise HTTPException(
            status_code=401,
            detail="initData missing or invalid — open the app through the Telegram bot",
        )
    return tg_user


async def try_get_db_user(
    tg_user: Annotated[Optional[TelegramUser], Depends(try_get_tg_user)],
    service: Annotated[ShopService, Depends(lambda: shop_service)],
) -> User | None:
    if tg_user is None:
        return None
    try:
        full_name = (
            f"{tg_user.first_name} {tg_user.last_name}".strip()
            or tg_user.username
            or "Игрок"
        )
        return await service.get_or_create_user(
            telegram_id=tg_user.id,
            full_name=full_name,
            username=tg_user.username,
        )
    except SQLAlchemyError as exc:
        log.exception("DB error in try_get_db_user: %s", exc)
        return None


async def require_db_user(
    user: Annotated[Optional[User], Depends(try_get_db_user)],
) -> User:
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="auth required — open the app through the Telegram bot",
        )
    return user
