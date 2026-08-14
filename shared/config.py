"""
Единый конфиг для бота и сайта.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    # ВАЖНО: для Railway / TWA Telegram требует https://. Для локала — http://localhost:PORT.
    twa_url: str = os.getenv("TWA_URL", "http://localhost:8080")
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("PORT", os.getenv("API_PORT", "8080")))

    # DB — Railway даёт DATABASE_URL (postgres://...) или используем локальный sqlite.
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./shop.db",
    )

    # Telegram initData TTL
    initdata_ttl_seconds: int = int(os.getenv("INITDATA_TTL", "3600"))

    # Реферальная «вознаграждение»: сколько начислим рефереру за каждого,
    # кто зарегистрировался по его коду и сделал хотя бы один платёж.
    referral_bonus: int = int(os.getenv("REFERRAL_BONUS", "100"))

    support_chat_id: str = os.getenv("SUPPORT_CHAT", "@lasster_support")

    # Режим отладки
    debug: bool = _get_bool("DEBUG", False)

    @property
    def is_https_twa(self) -> bool:
        return self.twa_url.startswith("https://") or self.twa_url.startswith("http://localhost")


config = Config()
