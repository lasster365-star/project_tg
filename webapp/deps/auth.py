"""
Аутентификация по initData для эндпоинтов /api/*.
initData приходит либо в `Authorization: tma <initData>`, либо в `X-Init-Data`.
"""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from shared.config import config
from shared.models import User
from shared.services import ShopService, shop_service
from shared.tma_auth import TelegramUser, extract_user, validate_init_data


def _extract_init_data(authorization: Optional[str], x_init_data: Optional[str]) -> str:
    if x_init_data:
        return x_init_data
    if not authorization:
        raise HTTPException(status_code=401, detail="missing initData")
    parts = authorization.split(None, 1)
    if len(parts) == 2 and parts[0].lower() in {"tma", "bearer"}:
        return parts[1]
    if len(parts) == 1:
        # клиент прислал голый initData без схемы
        return parts[0]
    raise HTTPException(status_code=401, detail="bad Authorization header")


async def require_tg_user(
    authorization: Annotated[Optional[str], Header()] = None,
    x_init_data: Annotated[Optional[str], Header(alias="X-Init-Data")] = None,
) -> TelegramUser:
    raw = _extract_init_data(authorization, x_init_data)
    try:
        parsed = validate_init_data(
            raw, config.bot_token, ttl_seconds=config.initdata_ttl_seconds
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=f"invalid initData: {exc}") from exc

    tg_user = extract_user(parsed)
    if tg_user is None:
        raise HTTPException(status_code=401, detail="no user in initData")
    return tg_user


async def require_db_user(
    tg_user: Annotated[TelegramUser, Depends(require_tg_user)],
    service: Annotated[ShopService, Depends(lambda: shop_service)],
) -> User:
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
        raise HTTPException(status_code=500, detail=f"db error: {exc}") from exc
