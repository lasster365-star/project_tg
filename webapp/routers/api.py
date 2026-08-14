"""
REST-API для Mini App.

`/api/public/*` — гостевой публичный доступ (без initData).
`/api/*` — под /api/cart, /api/orders, /api/me — требуется initData (TMA).
`/api/admin/*` — заголовок X-Admin-Token == ADMIN_TOKEN env.
"""
from __future__ import annotations

import secrets
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from shared.models import OrderItem, ProductKind, User
from shared.services import (
    EmptyCart,
    InsufficientFunds,
    ShopService,
    UserNotFound,
    shop_service,
)
from webapp.deps.auth import require_db_user, require_tg_user
from webapp.deps.serializers import (
    cart_item_dto,
    category_dto,
    order_dto,
    product_dto,
    topup_dto,
    user_dto,
)


router = APIRouter(prefix="/api", tags=["api"])
public = APIRouter(prefix="/api/public", tags=["public"])
admin = APIRouter(prefix="/api/admin", tags=["admin"])


def _service() -> ShopService:
    return shop_service


def _admin_token_checker(
    x_admin_token: Annotated[Optional[str], Header(alias="X-Admin-Token")] = None,
):
    import os

    expected = os.getenv("ADMIN_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="ADMIN_TOKEN not configured")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=401, detail="bad admin token")
    return True


# ---------------- Public (для витрины и предпросмотра) ----------------

@public.get("/health")
async def health_public() -> dict[str, str]:
    return {"status": "ok"}


@public.get("/products")
async def public_products(
    service: Annotated[ShopService, Depends(_service)],
    categoryId: int | None = Query(default=None),
    kind: str | None = Query(default=None),
) -> dict:
    pkind: ProductKind | None = None
    if kind:
        try:
            pkind = ProductKind(kind)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid kind") from exc
    products = await service.list_products(category_id=categoryId, kind=pkind)
    return {"products": [product_dto(p) for p in products]}


@public.get("/product/{product_id}")
async def public_product(
    product_id: int,
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    p = await service.get_product(product_id)
    if p is None:
        raise HTTPException(status_code=404, detail="product not found")
    return {"product": product_dto(p)}


@router.get("/product/{product_id}")
async def auth_product(
    product_id: int,
    user: Annotated[User, Depends(require_db_user)],  # noqa: ARG001
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    p = await service.get_product(product_id)
    if p is None:
        raise HTTPException(status_code=404, detail="product not found")
    return {"product": product_dto(p)}


@public.get("/categories")
async def public_categories(
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    cats = await service.list_categories()
    return {"categories": [category_dto(c) for c in cats]}

@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/me")
async def me(
    user: Annotated[User, Depends(require_db_user)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    refs = await service.count_referrals(user.id)
    return {"user": user_dto(user, refs)}


@router.get("/cart")
async def get_cart(
    user: Annotated[User, Depends(require_db_user)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    cart = await service.get_cart(user.telegram_id)
    return {
        "lines": [cart_item_dto(l.product, l.quantity) for l in cart.lines],
        "total": cart.total,
    }


class CartAction(BaseModel):
    productId: int
    quantity: int = 1


@router.post("/cart/add")
async def cart_add(
    payload: CartAction,
    user: Annotated[User, Depends(require_db_user)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    try:
        qty = await service.add_to_cart(user.telegram_id, payload.productId, payload.quantity)
    except UserNotFound:
        raise HTTPException(status_code=404, detail="user not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"quantity": qty}


@router.post("/cart/qty")
async def cart_qty(
    payload: CartAction,
    user: Annotated[User, Depends(require_db_user)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    await service.set_cart_qty(user.telegram_id, payload.productId, payload.quantity)
    return {"ok": True}


@router.post("/cart/remove")
async def cart_remove(
    payload: CartAction,
    user: Annotated[User, Depends(require_db_user)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    await service.remove_from_cart(user.telegram_id, payload.productId)
    return {"ok": True}


@router.post("/cart/clear")
async def cart_clear(
    user: Annotated[User, Depends(require_db_user)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    await service.clear_cart(user.telegram_id)
    return {"ok": True}


class TopUpPayload(BaseModel):
    amount: float


@router.post("/balance/topup")
async def topup(
    payload: TopUpPayload,
    user: Annotated[User, Depends(require_db_user)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    try:
        updated = await service.topup_balance(
            user.telegram_id, payload.amount, method="twa"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    refs = await service.count_referrals(updated.id)
    return {"user": user_dto(updated, refs)}


@router.post("/orders/checkout")
async def checkout(
    user: Annotated[User, Depends(require_db_user)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    try:
        order = await service.create_order(user.telegram_id)
    except EmptyCart:
        raise HTTPException(status_code=400, detail="cart is empty")
    items = await service.list_order_items(order.id)
    return {"order": order_dto(order, items=items)}


@router.post("/orders/{order_id}/pay")
async def pay_order(
    order_id: int,
    user: Annotated[User, Depends(require_db_user)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    try:
        order = await service.pay_order(user.telegram_id, order_id)
    except InsufficientFunds:
        raise HTTPException(status_code=402, detail="insufficient funds")
    except (UserNotFound, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    items = await service.list_order_items(order.id)
    return {"order": order_dto(order, items=items)}


@router.post("/orders/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    user: Annotated[User, Depends(require_db_user)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    try:
        order = await service.cancel_order(user.telegram_id, order_id)
    except (UserNotFound, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    items = await service.list_order_items(order.id)
    return {"order": order_dto(order, items=items)}


@router.get("/orders")
async def list_orders(
    user: Annotated[User, Depends(require_db_user)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    orders = await service.list_orders(user.telegram_id)
    out = []
    for o in orders:
        items = await service.list_order_items(o.id)
        out.append(order_dto(o, items=items))
    return {"orders": out}


@router.get("/topups")
async def list_topups(
    user: Annotated[User, Depends(require_db_user)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    rows = await service.list_topups(user.telegram_id)
    return {"topups": [topup_dto(t) for t in rows]}


# ---------------- Admin (X-Admin-Token) ----------------

class AdminProductCreate(BaseModel):
    categoryId: int
    title: str
    description: str = ""
    price: float
    kind: str
    rentalDays: int | None = None
    stock: int = -1
    rating: float = 4.8
    reviewsCount: int = 0


class AdminProductUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: float | None = None
    stock: int | None = None
    isActive: bool | None = None


class AdminTopUp(BaseModel):
    telegramId: int
    amount: float
    method: str = "admin"


@admin.get("/products")
async def admin_list_products(
    _: Annotated[bool, Depends(_admin_token_checker)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    products = await service.list_products()
    return {"products": [product_dto(p) for p in products]}


@admin.post("/products")
async def admin_create_product(
    payload: AdminProductCreate,
    _: Annotated[bool, Depends(_admin_token_checker)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    try:
        kind = ProductKind(payload.kind)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid kind") from exc
    from shared.models import Product

    p = Product(
        category_id=payload.categoryId,
        title=payload.title,
        description=payload.description,
        price=Decimal(str(payload.price)),
        kind=kind,
        rental_days=payload.rentalDays,
        stock=payload.stock,
        rating=Decimal(str(payload.rating)),
        reviews_count=payload.reviewsCount,
        is_active=True,
    )
    pid = await service.create_product(p)
    return {"id": pid, "product": product_dto(p)}


@admin.patch("/products/{product_id}")
async def admin_update_product(
    product_id: int,
    payload: AdminProductUpdate,
    _: Annotated[bool, Depends(_admin_token_checker)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    try:
        p = await service.update_product(
            product_id,
            title=payload.title,
            description=payload.description,
            price=payload.price,
            stock=payload.stock,
            is_active=payload.isActive,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"product": product_dto(p)}


@admin.delete("/products/{product_id}")
async def admin_delete_product(
    product_id: int,
    _: Annotated[bool, Depends(_admin_token_checker)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    ok = await service.deactivate_product(product_id)
    return {"ok": ok}


@admin.post("/users/topup")
async def admin_topup_user(
    payload: AdminTopUp,
    _: Annotated[bool, Depends(_admin_token_checker)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    try:
        user = await service.topup_balance(
            payload.telegramId, payload.amount, method=payload.method
        )
    except (UserNotFound, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"user": user_dto(user)}
