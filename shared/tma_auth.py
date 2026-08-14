"""
Валидация Telegram Mini App initData (HMAC-SHA256).
Согласно документации Telegram:
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl


@dataclass
class TelegramUser:
    id: int
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None
    is_premium: bool | None
    photo_url: str | None


def _build_data_check_string(pairs: list[tuple[str, str]]) -> str:
    items = [(k, v) for k, v in pairs if k != "hash"]
    items.sort(key=lambda kv: kv[0])
    return "\n".join(f"{k}={v}" for k, v in items)


def validate_init_data(init_data: str, bot_token: str, ttl_seconds: int = 3600) -> dict[str, Any]:
    """
    Возвращает dict c полями auth_date, user, query_id и пр.
    Бросает ValueError при невалидной подписи или просрочке.
    """
    if not init_data:
        raise ValueError("empty initData")

    pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=False)
    received_hash = None
    for k, v in pairs:
        if k == "hash":
            received_hash = v
            break
    if not received_hash:
        raise ValueError("hash not found")

    data_check_string = _build_data_check_string(pairs)
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise ValueError("invalid hash")

    parsed: dict[str, Any] = OrderedDict()
    for k, v in pairs:
        parsed[k] = v

    try:
        auth_date = int(parsed.get("auth_date", "0"))
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid auth_date") from exc
    if ttl_seconds > 0 and abs(int(time.time()) - auth_date) > ttl_seconds:
        raise ValueError("initData expired")

    user_raw = parsed.get("user")
    if user_raw:
        try:
            parsed["user"] = json.loads(user_raw)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid user json") from exc

    return parsed


def extract_user(parsed: dict[str, Any]) -> TelegramUser | None:
    raw = parsed.get("user")
    if not isinstance(raw, dict):
        return None
    try:
        return TelegramUser(
            id=int(raw["id"]),
            first_name=str(raw.get("first_name", "")),
            last_name=raw.get("last_name"),
            username=raw.get("username"),
            language_code=raw.get("language_code"),
            is_premium=raw.get("is_premium"),
            photo_url=raw.get("photo_url"),
        )
    except (KeyError, TypeError, ValueError):
        return None
