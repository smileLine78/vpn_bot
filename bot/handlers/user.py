import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from .. import db, keyboards as kb, services
from ..config import settings
from ..xui import XUIError, xui

router = Router()
log = logging.getLogger(__name__)

WELCOME = "👋 Привет! Это VPN-сервис.\n\nВыберите действие:"
HELP = (
    "📲 <b>Как подключиться</b>\n\n"
    "1. Откройте «Моя подписка» и скопируйте ссылку.\n"
    "2. Установите приложение:\n"
    "   • iOS / macOS — Streisand, V2Box или Happ\n"
    "   • Android — v2rayNG или Happ\n"
    "   • Windows — Hiddify или v2rayN\n"
    "3. В приложении добавьте подписку по ссылке (Import from clipboard / Add subscription).\n"
    "4. Выберите сервер и включите VPN."
)


def fmt_date(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000).strftime("%d.%m.%Y %H:%M")


@router.message(CommandStart())
async def start(message: Message):
    await db.upsert_user(message.from_user.id, message.from_user.username)
    await message.answer(WELCOME, reply_markup=kb.main_menu())


@router.callback_query(F.data == "menu")
async def menu(call: CallbackQuery):
    await call.message.edit_text(WELCOME, reply_markup=kb.main_menu())
    await call.answer()


@router.callback_query(F.data == "help")
async def help_(call: CallbackQuery):
    await call.message.edit_text(HELP, reply_markup=kb.back())
    await call.answer()


@router.callback_query(F.data == "trial")
async def trial(call: CallbackQuery):
    tg_id = call.from_user.id
    await db.upsert_user(tg_id, call.from_user.username)
    user = await db.get_user(tg_id)
    if user["trial_used"]:
        await call.answer("Пробный период уже использован", show_alert=True)
        return
    await call.answer()
    try:
        user = await services.grant(tg_id, settings.trial_days, settings.trial_gb)
    except XUIError:
        log.exception("trial grant failed")
        await call.message.answer("⚠️ Сервер временно недоступен, попробуйте позже.")
        return
    await db.mark_trial_used(tg_id)
    await call.message.edit_text(
        f"🎁 Пробный период активирован: {settings.trial_days} дн., {settings.trial_gb} ГБ.\n\n"
        f"Ваша ссылка-подписка:\n<code>{services.sub_url(user['sub_id'])}</code>\n\n"
        "Инструкция — в разделе «Как подключиться».",
        reply_markup=kb.main_menu(),
    )


@router.callback_query(F.data == "buy")
async def buy(call: CallbackQuery):
    await call.message.edit_text("Выберите тариф (безлимитный трафик):", reply_markup=kb.tariffs())
    await call.answer()


@router.callback_query(F.data == "profile")
async def profile(call: CallbackQuery):
    user = await db.get_user(call.from_user.id)
    if not user or not user.get("uuid"):
        await call.message.edit_text(
            "У вас пока нет подписки. Попробуйте пробный период или купите тариф.",
            reply_markup=kb.main_menu(),
        )
        await call.answer()
        return

    import time

    active = user["expiry_ms"] > time.time() * 1000
    text = (
        f"👤 <b>Моя подписка</b>\n\n"
        f"Статус: {'✅ активна' if active else '❌ истекла'}\n"
        f"Действует до: {fmt_date(user['expiry_ms'])}\n"
    )
    try:
        tr = await xui.get_traffic(call.from_user.id)
        if tr:
            used = (tr.get("up", 0) + tr.get("down", 0)) / 1024**3
            total = tr.get("total", 0) / 1024**3
            text += f"Трафик: {used:.2f} ГБ из {'∞' if total == 0 else f'{total:.0f} ГБ'}\n"
    except XUIError:
        log.warning("traffic fetch failed", exc_info=True)

    text += f"\nСсылка-подписка:\n<code>{services.sub_url(user['sub_id'])}</code>"
    await call.message.edit_text(text, reply_markup=kb.main_menu())
    await call.answer()
