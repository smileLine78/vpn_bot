"""Оплата через CryptoBot (Crypto Pay API). Работает без домена и webhook'ов: счета опрашиваются."""
import asyncio
import logging

import aiohttp

from . import db, services
from .config import TARIFFS, Tariff, settings

log = logging.getLogger(__name__)
POLL_INTERVAL = 15


class CryptoPayError(Exception):
    pass


async def _call(method: str, params: dict | None = None):
    headers = {"Crypto-Pay-API-Token": settings.crypto_pay_token}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as s:
            async with s.post(
                f"{settings.crypto_pay_api.rstrip('/')}/{method}", json=params or {}, headers=headers
            ) as r:
                body = await r.json(content_type=None)
    except aiohttp.ClientError as e:
        raise CryptoPayError(f"Нет связи с Crypto Pay: {e}") from e
    if not body.get("ok"):
        raise CryptoPayError(f"Crypto Pay: {body.get('error')}")
    return body["result"]


async def create_invoice(tg_id: int, tariff: Tariff) -> tuple[int, str]:
    res = await _call(
        "createInvoice",
        {
            "asset": "USDT",
            "amount": f"{tariff.usdt:g}",
            "description": f"VPN — {tariff.title}",
            "payload": f"{tg_id}:{tariff.key}",
            "expires_in": 3600,
        },
    )
    url = res.get("bot_invoice_url") or res.get("pay_url")
    return res["invoice_id"], url


async def _get_invoices(ids: list[int]) -> list[dict]:
    res = await _call("getInvoices", {"invoice_ids": ",".join(map(str, ids))})
    # в разных версиях API результат — либо список, либо {"items": [...]}
    return res["items"] if isinstance(res, dict) else res


async def check_pending(bot):
    pending = {p["invoice_id"]: p for p in await db.pending_crypto_invoices()}
    if not pending:
        return
    for inv in await _get_invoices(list(pending)):
        p = pending.get(inv["invoice_id"])
        if not p:
            continue
        if inv["status"] == "paid":
            t = TARIFFS[p["tariff"]]
            await services.process_payment(
                bot, p["tg_id"], t, round(t.usdt * 100), "USDT", f"crypto:{inv['invoice_id']}"
            )
            await db.set_crypto_status(p["invoice_id"], "paid")
        elif inv["status"] == "expired":
            await db.set_crypto_status(p["invoice_id"], "expired")


async def poll_loop(bot):
    while True:
        try:
            await check_pending(bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("crypto polling failed")
        await asyncio.sleep(POLL_INTERVAL)
