import logging
import secrets
import time
import uuid as uuidlib

from aiogram import Bot

from . import db, keyboards as kb
from .config import Tariff, settings
from .xui import XUIError, xui

log = logging.getLogger(__name__)
DAY_MS = 86_400_000


def sub_url(sub_id: str) -> str:
    return f"{settings.sub_base_url.rstrip('/')}/{sub_id}"


async def grant(tg_id: int, days: int, total_gb: int = 0) -> dict:
    """Создаёт клиента в 3x-ui или продлевает существующего. Возвращает запись пользователя."""
    user = await db.get_user(tg_id)
    now_ms = int(time.time() * 1000)
    base = max(now_ms, (user or {}).get("expiry_ms") or 0)
    new_expiry = base + days * DAY_MS

    if user and user.get("uuid"):
        await xui.update_client(tg_id, user["uuid"], user["sub_id"], new_expiry, total_gb)
        client_uuid, sub_id = user["uuid"], user["sub_id"]
    else:
        client_uuid = str(uuidlib.uuid4())
        sub_id = secrets.token_hex(8)
        await xui.add_client(tg_id, client_uuid, sub_id, new_expiry, total_gb)

    await db.save_subscription(tg_id, client_uuid, sub_id, new_expiry)
    return await db.get_user(tg_id)


async def process_payment(
    bot: Bot, tg_id: int, tariff: Tariff, amount: int, currency: str, charge_id: str
):
    """Общая обработка оплаты для любого способа: записать платёж, выдать доступ, уведомить."""
    # защита от повторной обработки одного и того же платежа
    if not await db.add_payment(tg_id, tariff.key, amount, currency, charge_id):
        return

    try:
        user = await grant(tg_id, tariff.days)
    except XUIError:
        log.exception("grant after payment failed")
        await bot.send_message(
            tg_id,
            "✅ Оплата получена, но выдать доступ сразу не удалось. "
            "Администратор уже уведомлён и активирует подписку вручную.",
        )
        for admin in settings.admins:
            await bot.send_message(
                admin,
                f"⚠️ Оплата без выдачи доступа!\nuser: {tg_id}\ntariff: {tariff.key}\n"
                f"payment: {charge_id} ({amount} {currency})\n"
                f"Выдать вручную: /give {tg_id} {tariff.days}",
            )
        return

    await bot.send_message(
        tg_id,
        f"✅ Оплата прошла! Тариф «{tariff.title}» активирован.\n\n"
        f"Ссылка-подписка:\n<code>{sub_url(user['sub_id'])}</code>",
        reply_markup=kb.main_menu(),
    )
