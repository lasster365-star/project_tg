"""Аутентификация по initData для эндпоинтов /api/*."""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import SQLAlchemyError

from shared.config import config
from shared.models import User
from shared.services import ShopService, shop_service
from shared.tma_auth import TelegramUser, extract_user, validate_init_data


bearer = HTTPBearer(auto_error=False)


def _parse_init_data(header_value: str | None) -> str:
    if not header_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing initData",
        )
    if header_value.startswith("tma "):
        return header_value[4:]
    if header_value.startswith("Bearer "):
        return header_value[7:]
    return header_value


async def require_tg_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer)],
    x_init_data: Annotated[Optional[str], Header(alias="X-Init-Data")] = None,
) -> TelegramUser:
    init_data = ""
    if credentials and credentials.scheme:
        init_data = credentials.credentials
    elif x_init_data:
        init_data = x_init_data
    else:
        # Совместимость: иногда боевые клиенты шлют просто строку в Authorization без схемы
        if credentials is not None:
            init_data = credentials.credentials

    if not init_data:
        raise HTTPException(status_code=401, detail="missing initData")

    try:
        parsed = validate_init_data(
            init_data, config.bot_token, ttl_seconds=config.initdata_ttl_seconds
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
