"""Админские хэндлеры: добавить товар, пополнить баланс."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.handlers.shop import shop_category
from bot.keyboards.keyboards import categories_inline
from bot.utils.visual import send_visual
from shared.config import config
from shared.models import ProductKind
from shared.services import UserNotFound, shop_service


router = Router(name="admin")


class AddProductFSM(StatesGroup):
    choosing_category = State()
    entering_title = State()
    entering_description = State()
    entering_price = State()
    entering_kind = State()
    entering_rental_days = State()
    entering_stock = State()
    confirm = State()


class UserTopUpFSM(StatesGroup):
    waiting_tg_id = State()
    waiting_amount = State()
    confirm = State()


def _is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids or bool(config.admin_token) and False  # last False is unreachable


# ====== Главный вход в админку ======

@router.message(F.text == "🛠 Админка")
async def admin_entry(message: Message) -> None:
    if message.from_user.id not in config.admin_ids:
        await message.answer("⛔️ Недостаточно прав")
        return
    cats = await shop_service.list_categories()
    products = await shop_service.list_products(include_inactive=True, limit=30)
    text = (
        "🛠 <b>Админка</b>\n\n"
        f"Категорий: <b>{len(cats)}</b>\n"
        f"Товаров (вкл. скрытые): <b>{len(products)}</b>\n"
        "Выберите действие:"
    )
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    rows = [
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin:add")],
        [InlineKeyboardButton(text="💰 Пополнить баланс пользователю", callback_data="admin:topup_user")],
        [InlineKeyboardButton(text="📋 Список товаров", callback_data="admin:list")],
    ]
    await send_visual(
        message,
        caption=text,
        keyboard=InlineKeyboardMarkup(inline_keyboard=rows),
        image="menu_main.png",
    )


@router.callback_query(F.data == "admin:list")
async def admin_list(call: CallbackQuery) -> None:
    if call.from_user.id not in config.admin_ids:
        await call.answer("⛔️ Нет прав", show_alert=True)
        return
    await call.answer()
    products = await shop_service.list_products(include_inactive=True, limit=50)
    if not products:
        await send_visual(
            call,
            caption="Товаров нет",
            keyboard=None,
            image="menu_main.png",
            edit=True,
        )
        return
    from bot.keyboards.keyboards import products_inline

    await send_visual(
        call,
        caption=f"📋 Товары ({len(products)}):",
        keyboard=products_inline(products, config.twa_url),
        image="menu_main.png",
        edit=True,
    )


# ====== Добавление товара ======

@router.callback_query(F.data == "admin:add")
async def admin_add(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user.id not in config.admin_ids:
        await call.answer("⛔️ Нет прав", show_alert=True)
        return
    await call.answer()
    cats = await shop_service.list_categories()
    await send_visual(
        call,
        caption="➕ <b>Новый товар — шаг 1/7</b>\nВыберите категорию:",
        keyboard=categories_inline(cats, config.twa_url),
        image="menu_main.png",
        edit=True,
    )
    await state.set_state(AddProductFSM.choosing_category)


@router.callback_query(F.data.startswith("shop:cat:"), AddProductFSM.choosing_category)
async def admin_add_category(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user.id not in config.admin_ids:
        return
    try:
        cat_id = int(call.data.split(":")[2])
    except (ValueError, IndexError):
        return
    await state.update_data(category_id=cat_id)
    await state.set_state(AddProductFSM.entering_title)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    await send_visual(
        call,
        caption=(
            "➕ <b>Шаг 2/7</b>\n"
            "Введите <b>название</b> товара.\n\n"
            "Например: <code>Steam Wallet 2000 ₽</code>"
        ),
        keyboard=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:back")]
            ]
        ),
        image="menu_main.png",
        edit=True,
    )


@router.message(AddProductFSM.entering_title)
async def admin_add_title(message: Message, state: FSMContext) -> None:
    if message.from_user.id not in config.admin_ids:
        return
    title = (message.text or "").strip()
    if len(title) < 2 or len(title) > 200:
        await message.answer("Название должно быть от 2 до 200 символов. Попробуйте ещё раз:")
        return
    await state.update_data(title=title)
    await state.set_state(AddProductFSM.entering_description)
    await message.answer(
        "➕ <b>Шаг 3/7</b>\n"
        "Введите <b>описание</b> товара (или <code>-</code> чтобы пропустить)."
    )


@router.message(AddProductFSM.entering_description)
async def admin_add_desc(message: Message, state: FSMContext) -> None:
    if message.from_user.id not in config.admin_ids:
        return
    text = (message.text or "").strip()
    if text == "-":
        text = ""
    await state.update_data(description=text)
    await state.set_state(AddProductFSM.entering_price)
    await message.answer("➕ <b>Шаг 4/7</b>\nВведите <b>цену</b> в рублях (например, <code>999</code> или <code>1499.50</code>).")


@router.message(AddProductFSM.entering_price)
async def admin_add_price(message: Message, state: FSMContext) -> None:
    if message.from_user.id not in config.admin_ids:
        return
    raw = (message.text or "").strip().replace(",", ".")
    try:
        price = Decimal(raw)
    except InvalidOperation:
        await message.answer("Не похоже на число. Попробуйте ещё раз (например, <code>999.99</code>):")
        return
    if price <= 0:
        await message.answer("Цена должна быть больше 0:")
        return
    await state.update_data(price=float(price))
    await state.set_state(AddProductFSM.entering_kind)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    rows = [
        [InlineKeyboardButton(text="🎮 Подписка", callback_data="kind:subscription")],
        [InlineKeyboardButton(text="👤 Аккаунт", callback_data="kind:account")],
        [InlineKeyboardButton(text="🔑 Ключ", callback_data="kind:key")],
        [InlineKeyboardButton(text="🕒 Прокат", callback_data="kind:rental")],
    ]
    await message.answer(
        "➕ <b>Шаг 5/7</b>\nВыберите <b>тип</b> товара:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("kind:"), AddProductFSM.entering_kind)
async def admin_add_kind(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user.id not in config.admin_ids:
        return
    kind_value = call.data.split(":", 1)[1]
    try:
        kind = ProductKind(kind_value)
    except ValueError:
        await call.answer("Неизвестный тип", show_alert=True)
        return
    await state.update_data(kind=kind.value)
    await call.answer()
    if kind is ProductKind.rental:
        await state.set_state(AddProductFSM.entering_rental_days)
        await call.message.answer(
            "➕ <b>Шаг 6/7</b>\nВведите <b>срок проката</b> в днях (целое число, например <code>7</code>)."
        )
    else:
        await state.update_data(rental_days=None)
        await state.set_state(AddProductFSM.entering_stock)
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        rows = [
            [InlineKeyboardButton(text="♾️ Без лимита", callback_data="stock:-1")],
            [InlineKeyboardButton(text="10", callback_data="stock:10"),
             InlineKeyboardButton(text="50", callback_data="stock:50")],
            [InlineKeyboardButton(text="100", callback_data="stock:100"),
             InlineKeyboardButton(text="500", callback_data="stock:500")],
        ]
        await call.message.answer(
            "➕ <b>Шаг 6/7</b>\nЗапас на складе:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        )


@router.callback_query(F.data.startswith("stock:"), AddProductFSM.entering_stock)
async def admin_add_stock(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user.id not in config.admin_ids:
        return
    try:
        stock = int(call.data.split(":")[1])
    except (ValueError, IndexError):
        return
    await state.update_data(stock=stock)
    await state.set_state(AddProductFSM.confirm)
    await _show_confirm(call.message, await state.get_data())


@router.message(AddProductFSM.entering_rental_days)
async def admin_add_rental_days(message: Message, state: FSMContext) -> None:
    if message.from_user.id not in config.admin_ids:
        return
    raw = (message.text or "").strip()
    try:
        days = int(raw)
    except ValueError:
        await message.answer("Нужно целое число. Попробуйте ещё:")
        return
    if days <= 0 or days > 365:
        await message.answer("Срок должен быть от 1 до 365 дней:")
        return
    await state.update_data(rental_days=days)
    await state.set_state(AddProductFSM.entering_stock)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    rows = [
        [InlineKeyboardButton(text="♾️ Без лимита", callback_data="stock:-1")],
        [InlineKeyboardButton(text="100", callback_data="stock:100")],
    ]
    await message.answer(
        "➕ <b>Шаг 6/7</b>\nЗапас на складе:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


async def _show_confirm(target_msg: Message, data: dict) -> None:
    """Показывает карточку с введёнными данными и просит подтвердить."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    kind_label = {
        "subscription": "🎮 Подписка",
        "account": "👤 Аккаунт",
        "key": "🔑 Ключ",
        "rental": "🕒 Прокат",
    }.get(data["kind"], data["kind"])
    text = (
        "➕ <b>Шаг 7/7 — подтверждение</b>\n\n"
        f"📂 Категория ID: <code>{data['category_id']}</code>\n"
        f"📛 Название: <b>{data['title']}</b>\n"
        f"📝 Описание: {data.get('description') or '—'}\n"
        f"💵 Цена: <b>{data['price']} ₽</b>\n"
        f"🏷 Тип: {kind_label}\n"
        f"📆 Срок проката: {data.get('rental_days') or '—'} дн.\n"
        f"📦 На складе: {'♾️' if data['stock'] == -1 else data['stock']}\n\n"
        "Сохранить?"
    )
    rows = [
        [InlineKeyboardButton(text="✅ Сохранить", callback_data="admin:save")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="admin:cancel")],
    ]
    await target_msg.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data == "admin:save", AddProductFSM.confirm)
async def admin_save(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user.id not in config.admin_ids:
        return
    data = await state.get_data()
    await state.clear()
    await call.answer("Сохраняю…")
    from shared.models import Product

    p = Product(
        category_id=data["category_id"],
        title=data["title"],
        description=data.get("description", ""),
        price=Decimal(str(data["price"])),
        kind=ProductKind(data["kind"]),
        rental_days=data.get("rental_days"),
        stock=int(data["stock"]),
        is_active=True,
    )
    pid = await shop_service.create_product(p)
    text = (
        f"✅ <b>Товар сохранён</b>\n\n"
        f"ID: <code>{pid}</code>\n"
        f"{p.title} · {p.price} ₽"
    )
    await send_visual(
        call,
        caption=text,
        keyboard=None,
        image="menu_main.png",
        edit=True,
    )


@router.callback_query(F.data == "admin:cancel", AddProductFSM.confirm)
async def admin_cancel(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.answer("Отменено")
    await call.message.answer("Добавление отменено.")


# ====== Пополнение баланса ======

@router.callback_query(F.data == "admin:topup_user")
async def admin_topup_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user.id not in config.admin_ids:
        await call.answer("⛔️ Нет прав", show_alert=True)
        return
    await call.answer()
    await state.set_state(UserTopUpFSM.waiting_tg_id)
    await call.message.answer(
        "💰 <b>Пополнение баланса</b>\n\n"
        "Введите <b>Telegram ID</b> пользователя (целое число)."
    )


@router.message(UserTopUpFSM.waiting_tg_id)
async def admin_topup_tgid(message: Message, state: FSMContext) -> None:
    if message.from_user.id not in config.admin_ids:
        return
    raw = (message.text or "").strip()
    try:
        tg_id = int(raw)
    except ValueError:
        await message.answer("Telegram ID должен быть числом. Попробуйте:")
        return
    user = await shop_service.get_user_by_telegram(tg_id)
    if user is None:
        await message.answer(
            f"⚠️ Пользователь с ID {tg_id} не запускал бота. "
            "Попросите его нажать /start и попробуйте снова."
        )
        return
    await state.update_data(telegram_id=tg_id, full_name=user.full_name)
    await state.set_state(UserTopUpFSM.waiting_amount)
    await message.answer(
        f"✅ Пользователь: <b>{user.full_name}</b> (@{user.username or '—'})\n"
        f"💵 Текущий баланс: <b>{user.balance} ₽</b>\n\n"
        "Введите <b>сумму</b> пополнения в рублях."
    )


@router.message(UserTopUpFSM.waiting_amount)
async def admin_topup_amount(message: Message, state: FSMContext) -> None:
    if message.from_user.id not in config.admin_ids:
        return
    raw = (message.text or "").strip().replace(",", ".")
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        await message.answer("Сумма должна быть числом:")
        return
    if amount <= 0:
        await message.answer("Сумма должна быть > 0:")
        return
    data = await state.get_data()
    data["amount"] = float(amount)
    await state.update_data(amount=float(amount))
    await state.set_state(UserTopUpFSM.confirm)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    text = (
        f"💰 Подтвердите пополнение:\n\n"
        f"👤 {data['full_name']} (ID <code>{data['telegram_id']}</code>)\n"
        f"💵 Сумма: <b>{amount} ₽</b>"
    )
    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Подтвердить", callback_data="admin:topup_ok")],
                [InlineKeyboardButton(text="❌ Отменить", callback_data="admin:topup_no")],
            ]
        ),
    )


@router.callback_query(F.data == "admin:topup_ok", UserTopUpFSM.confirm)
async def admin_topup_apply(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user.id not in config.admin_ids:
        return
    data = await state.get_data()
    await state.clear()
    await call.answer("Зачисляю…")
    try:
        user = await shop_service.topup_balance(
            data["telegram_id"], data["amount"], method="admin"
        )
    except UserNotFound:
        await call.message.answer("Пользователь не найден.")
        return
    await call.message.answer(
        f"✅ Баланс {data['full_name']} пополнен на <b>{data['amount']} ₽</b>\n"
        f"💰 Новый баланс: <b>{user.balance} ₽</b>"
    )


@router.callback_query(F.data == "admin:topup_no", UserTopUpFSM.confirm)
async def admin_topup_cancel(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.answer("Отменено")
    await call.message.answer("Пополнение отменено.")
