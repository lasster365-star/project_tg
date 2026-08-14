"""Общие утилиты: цена, время, реф-коды и т.п."""
from __future__ import annotations

import secrets
import string
from decimal import Decimal


def format_price(value: Decimal | float | int | str) -> str:
    amount = Decimal(str(value))
    sign = "" if amount >= 0 else "-"
    amount = abs(amount).quantize(Decimal("0.01"))
    integer, _, fraction = format(amount, "f").partition(".")
    # 1 234.56
    integer_with_spaces = ""
    for i, ch in enumerate(reversed(integer)):
        integer_with_spaces = ch + integer_with_spaces
        if (i + 1) % 3 == 0 and i + 1 != len(integer):
            integer_with_spaces = " " + integer_with_spaces
    return f"{sign}{integer_with_spaces}.{fraction} ₽"


def short_ref_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    # Без 0/O/1/I чтобы не путаться
    blacklist = set("0O1I")
    alphabet = "".join(c for c in alphabet if c not in blacklist)
    return "".join(secrets.choice(alphabet) for _ in range(length))


def build_referral_link(bot_username: str, code: str) -> str:
    return f"https://t.me/{bot_username}?start=ref_{code}"
