import logging

from aiogram import Bot, F, Router
from aiogram.types import Message, PreCheckoutQuery

from .. import db, keyboards as kb, services
from ..config import TARIFFS, settings
from ..xui import XUIError

router = Router()
log = logging.getLogger(__name__)


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    key = query.invoice_payload.split(":", 1)[-1]
    await query.answer(ok=key in TARIFFS, error_message="Тариф недоступен")


@router.message(F.successful_payment)
async def paid(message: Message, bot: Bot):
    pay = message.successful_payment
    tg_id = message.from_user.id
    tariff = TARIFFS[pay.invoice_payload.split(":", 1)[1]]

    # защита от повторной обработки одного и того же платежа
    if not await db.add_payment(tg_id, tariff.key, pay.total_amount, pay.telegram_payment_charge_id):
        return

    try:
        user = await services.grant(tg_id, tariff.days)
    except XUIError:
        log.exception("grant after payment failed")
        await message.answer(
            "✅ Оплата получена, но выдать доступ сразу не удалось. "
            "Администратор уже уведомлён и активирует подписку вручную."
        )
        for admin in settings.admins:
            await bot.send_message(
                admin,
                f"⚠️ Оплата без выдачи доступа!\nuser: {tg_id}\ntariff: {tariff.key}\n"
                f"charge_id: {pay.telegram_payment_charge_id}\n"
                f"Выдать вручную: /give {tg_id} {tariff.days}",
            )
        return

    await message.answer(
        f"✅ Оплата прошла! Тариф «{tariff.title}» активирован.\n\n"
        f"Ссылка-подписка:\n<code>{services.sub_url(user['sub_id'])}</code>",
        reply_markup=kb.main_menu(),
    )
