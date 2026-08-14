"""FSM-состояния бота."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class CartFSM(StatesGroup):
    viewing_product = State()     # открыта карточка в корзине
    confirming_pay = State()      # показали подтверждение оплаты


class TopUpFSM(StatesGroup):
    choosing_amount = State()
