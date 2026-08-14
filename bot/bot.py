"""
Точка входа aiogram-бота.

Использование:
    python -m bot.bot
"""
from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.middlewares.shop import ShopMiddleware
from bot.routers import setup_routers
from shared.config import config
from shared.db import init_db

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO if not config.debug else logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("bot")


async def main() -> None:
    if not config.bot_token:
        raise RuntimeError("BOT_TOKEN env is empty")

    await init_db()

    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Мидлварь на каждое сообщение/коллбэк
    dp.message.middleware(ShopMiddleware())
    dp.callback_query.middleware(ShopMiddleware())

    dp.include_router(setup_routers())

    log.info("Bot polling started")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


def _graceful(*_args):
    log.info("Shutting down bot…")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, _graceful)
    asyncio.run(main())
