"""
Диагностический эндпоинт: показывает, что Telegram Mini App прислал на сервер.
Не требует авторизации — принимает сырой init-data (валидный или нет), и
возвращает разобранный/неразобранный вид.

GET /api/debug/initdata принимает:
- заголовок Authorization: tma <...>
- заголовок X-Init-Data: <...>
- query-параметр ?initdata=<...>  (на случай, когда фронт не может выставить header)

Не пишет в БД, не изменяет данные.
"""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Header, Query

from shared.config import config
from shared.tma_auth import extract_user, validate_init_data


router = APIRouter(prefix="/api/debug", tags=["debug"])


def _extract(authorization: Optional[str], x_init: Optional[str], qd: Optional[str]) -> str:
    if x_init:
        return x_init
    if authorization:
        parts = authorization.split(None, 1)
        if len(parts) == 2:
            return parts[1]
        if len(parts) == 1:
            return parts[0]
    if qd:
        return qd
    return ""


@router.get("/initdata")
async def debug_initdata(
    authorization: Annotated[Optional[str], Header()] = None,
    x_init_data: Annotated[Optional[str], Header(alias="X-Init-Data")] = None,
    initdata: Annotated[Optional[str], Query()] = None,
) -> dict:
    raw = _extract(authorization, x_init_data, initdata)
    out: dict = {
        "raw_present": bool(raw),
        "raw_len": len(raw),
        "raw_preview": raw[:120] + ("…" if len(raw) > 120 else ""),
        "bot_token_present": bool(config.bot_token),
        "validation_ok": False,
        "validation_error": None,
        "user": None,
        "auth_date": None,
        "extra": {},
    }
    if not raw:
        out["validation_error"] = "initData отсутствует — Telegram не передал данные. " \
            "Открой Mini App через reply-кнопку «🛍 Открыть магазин», а не из inline."
        return out
    try:
        parsed = validate_init_data(raw, config.bot_token, ttl_seconds=3600)
        out["validation_ok"] = True
        out["auth_date"] = parsed.get("auth_date")
        u = extract_user(parsed)
        if u is not None:
            out["user"] = {
                "id": u.id,
                "first_name": u.first_name,
                "username": u.username,
                "language_code": u.language_code,
            }
        # покажем все поля верхнего уровня
        out["extra"] = {k: parsed.get(k) for k in parsed.keys() if k not in {"user", "auth_date", "hash", "signature"}}
    except ValueError as exc:
        out["validation_error"] = str(exc)
        out["validation_ok"] = False
    except Exception as exc:  # noqa: BLE001
        out["validation_error"] = f"unexpected: {exc}"
    return out
