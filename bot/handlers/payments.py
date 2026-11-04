import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from .. import crypto, db, keyboards as kb, services
from ..config import TARIFFS, settings

router = Router()
log = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("tariff:"))
async def choose_method(call: CallbackQuery):
    t = TARIFFS.get(call.data.split(":", 1)[1])
    if not t:
        await call.answer("Тариф не найден", show_alert=True)
        return
    await call.message.edit_text(
        f"Тариф: <b>{t.title}</b> (безлимитный трафик)\n\nВыберите способ оплаты:",
        reply_markup=kb.pay_methods(t.key),
    )
    await call.answer()


@router.callback_query(F.data.startswith("pay:"))
async def pay(call: CallbackQuery):
    _, method, key = call.data.split(":", 2)
    t = TARIFFS.get(key)
    if not t:
        await call.answer("Тариф не найден", show_alert=True)
        return

    title = f"VPN — {t.title}"
    description = f"Доступ к VPN на {t.days} дн."
    payload = f"tariff:{t.key}"

    if method == "stars":
        await call.message.answer_invoice(
            title=title, description=description, payload=payload,
            currency="XTR", provider_token="",  # Telegram Stars
            prices=[LabeledPrice(label=t.title, amount=t.stars)],
        )
    elif method == "card" and settings.payment_provider_token:
        await call.message.answer_invoice(
            title=title, description=description, payload=payload,
            currency=settings.card_currency,
            provider_token=settings.payment_provider_token,
            # Telegram принимает сумму в минимальных единицах (копейки, центы)
            prices=[LabeledPrice(label=t.title, amount=t.card * 100)],
        )
    elif method == "crypto" and settings.crypto_pay_token:
        try:
            invoice_id, url = await crypto.create_invoice(call.from_user.id, t)
        except crypto.CryptoPayError:
            log.exception("crypto invoice failed")
            await call.answer("Не удалось создать счёт, попробуйте позже", show_alert=True)
            return
        await db.add_crypto_invoice(invoice_id, call.from_user.id, t.key)
        await call.message.answer(
            f"🪙 Счёт на {t.usdt:g} USDT создан (действует 1 час).\n"
            "После оплаты доступ придёт автоматически, обычно в течение минуты.",
            reply_markup=kb.url_button("Оплатить в CryptoBot", url),
        )
    else:
        await call.answer("Этот способ оплаты недоступен", show_alert=True)
        return
    await call.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    key = query.invoice_payload.split(":", 1)[-1]
    await query.answer(ok=key in TARIFFS, error_message="Тариф недоступен")


@router.message(F.successful_payment)
async def paid(message: Message, bot: Bot):
    pay_ = message.successful_payment
    tariff = TARIFFS[pay_.invoice_payload.split(":", 1)[1]]
    await services.process_payment(
        bot, message.from_user.id, tariff,
        pay_.total_amount, pay_.currency, pay_.telegram_payment_charge_id,
    )
