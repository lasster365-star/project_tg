"""
REST-API для Mini App.
Все эндпоинты /api/* требуют initData.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from shared.services import (
    EmptyCart,
    InsufficientFunds,
    ShopService,
    UserNotFound,
    shop_service,
)
from shared.tma_auth import TelegramUser
from shared.utils import format_price
from webapp.deps.auth import require_db_user, require_tg_user
from webapp.deps.serializers import (
    cart_item_dto,
    category_dto,
    order_dto,
    product_dto,
    topup_dto,
    user_dto,
)
from shared.models import ProductKind, User
from shared.services import ShopService

router = APIRouter(prefix="/api", tags=["api"])


def _service() -> ShopService:
    return shop_service


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


@router.get("/categories")
async def list_categories(
    user: Annotated[User, Depends(require_db_user)],  # noqa: ARG001  (нужно для auth)
    service: Annotated[ShopService, Depends(_service)],
    kind: str | None = Query(default=None),
) -> dict:
    if kind:
        try:
            kinds = ProductKind(kind)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid kind") from exc
        cats = await service.list_categories(kinds)
    else:
        cats = await service.list_categories()
    return {"categories": [category_dto(c) for c in cats]}


@router.get("/products")
async def list_products(
    user: Annotated[User, Depends(require_db_user)],  # noqa: ARG001
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


@router.get("/product/{product_id}")
async def get_product(
    product_id: int,
    user: Annotated[User, Depends(require_db_user)],  # noqa: ARG001
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    p = await service.get_product(product_id)
    if p is None:
        raise HTTPException(status_code=404, detail="not found")
    return {"product": product_dto(p)}


@router.get("/cart")
async def get_cart(
    user: Annotated[User, Depends(require_db_user)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    cart = await service.get_cart(user.telegram_id)
    return {
        "lines": [
            cart_item_dto(l.product, l.quantity) for l in cart.lines
        ],
        "total": format_price(cart.total),
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
    return {"order": order_dto(order)}


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
    return {"order": order_dto(order)}


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
    return {"order": order_dto(order)}


@router.get("/orders")
async def list_orders(
    user: Annotated[User, Depends(require_db_user)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    orders = await service.list_orders(user.telegram_id)
    return {"orders": [order_dto(o) for o in orders]}


@router.get("/topups")
async def list_topups(
    user: Annotated[User, Depends(require_db_user)],
    service: Annotated[ShopService, Depends(_service)],
) -> dict:
    rows = await service.list_topups(user.telegram_id)
    return {"topups": [topup_dto(t) for t in rows]}
