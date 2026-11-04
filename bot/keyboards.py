from aiogram.types import InlineKeyboardButton as Btn
from aiogram.types import InlineKeyboardMarkup as Markup

from .config import TARIFFS, settings


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
    rows = [[Btn(text=t.title, callback_data=f"tariff:{t.key}")] for t in TARIFFS.values()]
    rows.append([Btn(text="⬅️ Назад", callback_data="menu")])
    return Markup(inline_keyboard=rows)


def pay_methods(key: str) -> Markup:
    t = TARIFFS[key]
    rows = []
    if settings.payment_provider_token:
        rows.append(
            [Btn(text=f"💳 Картой — {t.card} {settings.card_currency}", callback_data=f"pay:card:{key}")]
        )
    if settings.crypto_pay_token:
        rows.append([Btn(text=f"🪙 Криптой — {t.usdt:g} USDT", callback_data=f"pay:crypto:{key}")])
    rows.append([Btn(text=f"⭐ Telegram Stars — {t.stars} ⭐", callback_data=f"pay:stars:{key}")])
    rows.append([Btn(text="⬅️ Назад", callback_data="buy")])
    return Markup(inline_keyboard=rows)


def url_button(text: str, url: str) -> Markup:
    return Markup(inline_keyboard=[[Btn(text=text, url=url)]])


def back() -> Markup:
    return Markup(inline_keyboard=[[Btn(text="⬅️ Назад", callback_data="menu")]])
