"""Корневой роутер бота. Импортируется из bot.py."""
from __future__ import annotations

from aiogram import Router

from bot.handlers import admin, cart, profile, shop, start, support


def setup_routers() -> Router:
    root = Router(name="root")
    root.include_router(start.router)
    root.include_router(shop.router)
    root.include_router(cart.router)
    root.include_router(profile.router)
    root.include_router(support.router)
    root.include_router(admin.router)
    return root
