"""
Сервисный слой: пользователи, корзина, заказы, пополнение, CRUD товаров.
Используется и ботом, и FastAPI.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.db import get_session_factory
from shared.models import (
    CartItem,
    Category,
    ImageFile,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    ProductKind,
    TopUp,
    User,
)
from shared.utils import short_ref_code


@dataclass
class CartLine:
    product: Product
    quantity: int

    @property
    def subtotal(self) -> Decimal:
        return self.product.price * self.quantity


@dataclass
class CartSummary:
    lines: list[CartLine]
    total: Decimal


class UserNotFound(Exception):
    pass


class InsufficientFunds(Exception):
    pass


class EmptyCart(Exception):
    pass


class StaleRef(Exception):
    pass


class ShopService:
    """Все операции с магазином. Потокобезопасно через фабрику сессий."""

    def __init__(self, session_factory=None) -> None:
        self.session_factory = session_factory or get_session_factory()

    # -------------------- Users --------------------
    async def get_or_create_user(
        self,
        telegram_id: int,
        full_name: str,
        username: Optional[str] = None,
        referrer_code: Optional[str] = None,
    ) -> User:
        async with self.session_factory() as session:
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if user is not None:
                changed = False
                if user.full_name != full_name:
                    user.full_name = full_name
                    changed = True
                if username and user.username != username:
                    user.username = username
                    changed = True
                if changed:
                    await session.commit()
                return user

            ref_user_id: int | None = None
            if referrer_code:
                ref_user = await session.scalar(
                    select(User).where(User.ref_code == referrer_code.upper())
                )
                if ref_user and ref_user.telegram_id != telegram_id:
                    ref_user_id = ref_user.id

            new_user = User(
                telegram_id=telegram_id,
                full_name=full_name,
                username=username,
                ref_code=short_ref_code(),
                referrer_id=ref_user_id,
            )
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            return new_user

    async def get_user_by_telegram(self, telegram_id: int) -> User | None:
        async with self.session_factory() as session:
            return await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )

    async def count_referrals(self, user_id: int) -> int:
        async with self.session_factory() as session:
            return int(
                await session.scalar(
                    select(func.count(User.id)).where(User.referrer_id == user_id)
                )
                or 0
            )

    async def list_all_users(self, limit: int = 50) -> list[User]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(User).order_by(User.id.desc()).limit(limit)
            )
            return list(result.scalars().all())

    # -------------------- Catalog --------------------
    async def list_categories(self, kind: Optional[ProductKind] = None) -> list[Category]:
        async with self.session_factory() as session:
            stmt = select(Category).order_by(Category.sort, Category.id)
            if kind is not None:
                stmt = stmt.where(Category.kind == kind)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_products(
        self,
        category_id: Optional[int] = None,
        kind: Optional[ProductKind] = None,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> list[Product]:
        async with self.session_factory() as session:
            stmt = select(Product)
            if not include_inactive:
                stmt = stmt.where(Product.is_active.is_(True))
            if category_id is not None:
                stmt = stmt.where(Product.category_id == category_id)
            if kind is not None:
                stmt = stmt.where(Product.kind == kind)
            stmt = stmt.order_by(Product.id).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_product(self, product_id: int) -> Product | None:
        async with self.session_factory() as session:
            return await session.scalar(
                select(Product).where(Product.id == product_id, Product.is_active.is_(True))
            )

    async def get_category(self, category_id: int) -> Category | None:
        async with self.session_factory() as session:
            return await session.scalar(
                select(Category).where(Category.id == category_id)
            )

    # -------------------- Admin: products CRUD --------------------
    async def create_product(self, product: Product) -> int:
        async with self.session_factory() as session:
            session.add(product)
            await session.commit()
            await session.refresh(product)
            return product.id

    async def update_product(
        self,
        product_id: int,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[float] = None,
        stock: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> Product:
        async with self.session_factory() as session:
            p = await session.scalar(
                select(Product).where(Product.id == product_id)
            )
            if p is None:
                raise ValueError(f"product {product_id} not found")
            if title is not None:
                p.title = title
            if description is not None:
                p.description = description
            if price is not None:
                p.price = Decimal(str(price))
            if stock is not None:
                p.stock = stock
            if is_active is not None:
                p.is_active = is_active
            await session.commit()
            await session.refresh(p)
            return p

    async def deactivate_product(self, product_id: int) -> bool:
        async with self.session_factory() as session:
            p = await session.scalar(
                select(Product).where(Product.id == product_id)
            )
            if p is None:
                return False
            p.is_active = False
            await session.commit()
            return True

    async def create_category(
        self, slug: str, title: str, kind: ProductKind, description: str = "", sort: int = 0
    ) -> int:
        async with self.session_factory() as session:
            cat = Category(
                slug=slug, title=title, kind=kind, description=description, sort=sort
            )
            session.add(cat)
            await session.commit()
            await session.refresh(cat)
            return cat.id

    # -------------------- Cart --------------------
    async def add_to_cart(self, telegram_id: int, product_id: int, qty: int = 1) -> int:
        async with self.session_factory() as session:
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if user is None:
                raise UserNotFound(telegram_id)
            product = await session.scalar(
                select(Product).where(Product.id == product_id, Product.is_active.is_(True))
            )
            if product is None:
                raise ValueError(f"product {product_id} not found")

            existing = await session.scalar(
                select(CartItem).where(
                    CartItem.user_id == user.id, CartItem.product_id == product_id
                )
            )
            if existing:
                existing.quantity = max(1, existing.quantity + qty)
                q = existing.quantity
            else:
                ci = CartItem(user_id=user.id, product_id=product_id, quantity=qty)
                session.add(ci)
                q = qty
            await session.commit()
            return q

    async def set_cart_qty(self, telegram_id: int, product_id: int, qty: int) -> None:
        async with self.session_factory() as session:
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if user is None:
                raise UserNotFound(telegram_id)
            existing = await session.scalar(
                select(CartItem).where(
                    CartItem.user_id == user.id, CartItem.product_id == product_id
                )
            )
            if existing is None:
                return
            if qty <= 0:
                await session.delete(existing)
            else:
                existing.quantity = qty
            await session.commit()

    async def remove_from_cart(self, telegram_id: int, product_id: int) -> None:
        await self.set_cart_qty(telegram_id, product_id, 0)

    async def get_cart(self, telegram_id: int) -> CartSummary:
        async with self.session_factory() as session:
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if user is None:
                return CartSummary(lines=[], total=Decimal("0.00"))
            result = await session.execute(
                select(CartItem, Product)
                .join(Product, CartItem.product_id == Product.id)
                .where(CartItem.user_id == user.id, Product.is_active.is_(True))
                .order_by(CartItem.id)
            )
            lines: list[CartLine] = []
            total = Decimal("0.00")
            for ci, prod in result.all():
                lines.append(CartLine(product=prod, quantity=ci.quantity))
                total += prod.price * ci.quantity
        return CartSummary(lines=lines, total=total)

    async def clear_cart(self, telegram_id: int) -> None:
        async with self.session_factory() as session:
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if user is None:
                return
            items = await session.scalars(
                select(CartItem).where(CartItem.user_id == user.id)
            )
            for ci in items.all():
                await session.delete(ci)
            await session.commit()

    # -------------------- Orders --------------------
    async def create_order(self, telegram_id: int) -> Order:
        cart = await self.get_cart(telegram_id)
        if not cart.lines:
            raise EmptyCart()
        async with self.session_factory() as session:
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if user is None:
                raise UserNotFound(telegram_id)
            order = Order(
                user_id=user.id,
                total_amount=cart.total,
                status=OrderStatus.pending,
                external_id=secrets.token_urlsafe(8),
            )
            session.add(order)
            await session.flush()
            for line in cart.lines:
                session.add(
                    OrderItem(
                        order_id=order.id,
                        product_id=line.product.id,
                        title_snapshot=line.product.title,
                        price_snapshot=line.product.price,
                        quantity=line.quantity,
                    )
                )
            await session.commit()
            await session.refresh(order)
            return order

    async def pay_order(self, telegram_id: int, order_id: int) -> Order:
        async with self.session_factory() as session:
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if user is None:
                raise UserNotFound(telegram_id)
            order = await session.scalar(
                select(Order)
                .where(Order.id == order_id, Order.user_id == user.id)
                .options(selectinload(Order.items))
            )
            if order is None:
                raise ValueError("order not found")
            if order.status != OrderStatus.pending:
                raise ValueError(f"order already {order.status}")
            if user.balance < order.total_amount:
                raise InsufficientFunds()

            user.balance = user.balance - order.total_amount
            order.status = OrderStatus.paid
            order.paid_at = datetime.now(timezone.utc)

            if user.referrer_id:
                ref_user = await session.get(User, user.referrer_id)
                if ref_user is not None:
                    from shared.config import config

                    ref_user.balance = (
                        ref_user.balance + Decimal(config.referral_bonus)
                    )
            await session.commit()
            await session.refresh(order)
            return order

    async def cancel_order(self, telegram_id: int, order_id: int) -> Order:
        async with self.session_factory() as session:
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if user is None:
                raise UserNotFound(telegram_id)
            order = await session.scalar(
                select(Order).where(Order.id == order_id, Order.user_id == user.id)
            )
            if order is None:
                raise ValueError("order not found")
            if order.status == OrderStatus.paid:
                raise ValueError("already paid")
            order.status = OrderStatus.cancelled
            await session.commit()
            await session.refresh(order)
            return order

    async def list_orders(self, telegram_id: int, limit: int = 30) -> list[Order]:
        async with self.session_factory() as session:
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if user is None:
                return []
            result = await session.execute(
                select(Order)
                .where(Order.user_id == user.id)
                .options(selectinload(Order.items))
                .order_by(Order.id.desc())
                .limit(limit)
            )
            return list(result.scalars().all())

    async def list_order_items(self, order_id: int) -> list[OrderItem]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(OrderItem)
                .where(OrderItem.order_id == order_id)
                .order_by(OrderItem.id)
            )
            return list(result.scalars().all())

    # -------------------- Balance --------------------
    async def topup_balance(
        self,
        telegram_id: int,
        amount: Decimal | float | str,
        method: str = "manual",
    ) -> User:
        async with self.session_factory() as session:
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if user is None:
                raise UserNotFound(telegram_id)
            value = Decimal(str(amount))
            if value <= 0:
                raise ValueError("amount must be positive")
            user.balance = user.balance + value
            session.add(TopUp(user_id=user.id, amount=value, method=method))
            await session.commit()
            await session.refresh(user)
            return user

    async def list_topups(self, telegram_id: int, limit: int = 20) -> list[TopUp]:
        async with self.session_factory() as session:
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if user is None:
                return []
            result = await session.execute(
                select(TopUp)
                .where(TopUp.user_id == user.id)
                .order_by(TopUp.id.desc())
                .limit(limit)
            )
            return list(result.scalars().all())

    # -------------------- Image cache --------------------
    async def get_image_file_id(self, image_path: str) -> str | None:
        async with self.session_factory() as session:
            row = await session.scalar(
                select(ImageFile).where(ImageFile.path == image_path)
            )
            return row.file_id if row else None

    async def save_image_file_id(self, image_path: str, file_id: str) -> None:
        async with self.session_factory() as session:
            row = await session.scalar(
                select(ImageFile).where(ImageFile.path == image_path)
            )
            if row is None:
                session.add(ImageFile(path=image_path, file_id=file_id))
            else:
                row.file_id = file_id
            await session.commit()


shop_service = ShopService()
