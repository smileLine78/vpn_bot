from aiogram.types import InlineKeyboardButton as Btn
from aiogram.types import InlineKeyboardMarkup as Markup

from .config import TARIFFS


def main_menu() -> Markup:
    return Markup(
        inline_keyboard=[
            [Btn(text="🎁 Пробный период", callback_data="trial")],
            [Btn(text="💳 Купить / продлить", callback_data="buy")],
            [Btn(text="👤 Моя подписка", callback_data="profile")],
            [Btn(text="📲 Как подключиться", callback_data="help")],
        ]
    )


def tariffs() -> Markup:
    rows = [
        [Btn(text=f"{t.title} — {t.stars} ⭐", callback_data=f"tariff:{t.key}")]
        for t in TARIFFS.values()
    ]
    rows.append([Btn(text="⬅️ Назад", callback_data="menu")])
    return Markup(inline_keyboard=rows)


def back() -> Markup:
    return Markup(inline_keyboard=[[Btn(text="⬅️ Назад", callback_data="menu")]])
