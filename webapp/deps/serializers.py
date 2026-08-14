"""Хелпер: сериализация моделей для JSON-ответов."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from shared.models import (
    Category,
    Order,
    OrderItem,
    Product,
    TopUp,
    User,
)


def _money(v: Decimal | float | int | str) -> str:
    d = Decimal(str(v))
    sign = "" if d >= 0 else "-"
    d = abs(d).quantize(Decimal("0.01"))
    return f"{sign}{d}"


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat()


def category_dto(c: Category) -> dict[str, Any]:
    return {
        "id": c.id,
        "slug": c.slug,
        "title": c.title,
        "kind": c.kind.value,
        "description": c.description,
    }


def product_dto(p: Product) -> dict[str, Any]:
    return {
        "id": p.id,
        "categoryId": p.category_id,
        "title": p.title,
        "description": p.description,
        "price": _money(p.price),
        "kind": p.kind.value,
        "rating": float(p.rating),
        "reviewsCount": p.reviews_count,
        "stock": p.stock,
        "rentalDays": p.rental_days,
        "imagePath": p.image_path,
    }


def cart_item_dto(product: Product, quantity: int) -> dict[str, Any]:
    return {
        "product": product_dto(product),
        "quantity": quantity,
        "subtotal": _money(Decimal(str(product.price)) * quantity),
    }


def user_dto(u: User, refs: int = 0) -> dict[str, Any]:
    return {
        "id": u.id,
        "telegramId": u.telegram_id,
        "fullName": u.full_name,
        "username": u.username,
        "balance": _money(u.balance),
        "refCode": u.ref_code,
        "referrals": refs,
    }


def order_item_dto(it: OrderItem) -> dict[str, Any]:
    return {
        "id": it.id,
        "title": it.title_snapshot,
        "price": _money(it.price_snapshot),
        "quantity": it.quantity,
        "subtotal": _money(Decimal(str(it.price_snapshot)) * it.quantity),
    }


def order_dto(o: Order) -> dict[str, Any]:
    return {
        "id": o.id,
        "status": o.status.value,
        "total": _money(o.total_amount),
        "createdAt": iso(o.created_at),
        "paidAt": iso(o.paid_at),
        "items": [order_item_dto(i) for i in o.items],
    }


def topup_dto(t: TopUp) -> dict[str, Any]:
    return {
        "id": t.id,
        "amount": _money(t.amount),
        "method": t.method,
        "createdAt": iso(t.created_at),
    }
