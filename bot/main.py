import asyncio
import contextlib
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from . import crypto, db
from .config import settings
from .handlers import admin, payments, user
from .xui import xui


async def main():
    logging.basicConfig(level=logging.INFO)
    await db.init()

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_routers(admin.router, payments.router, user.router)

    poller = None
    if settings.crypto_pay_token:
        poller = asyncio.create_task(crypto.poll_loop(bot))

    try:
        await dp.start_polling(bot)
    finally:
        if poller:
            poller.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await poller
        await xui.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
