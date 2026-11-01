import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from . import db
from .config import settings
from .handlers import admin, payments, user
from .xui import xui


async def main():
    logging.basicConfig(level=logging.INFO)
    await db.init()

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_routers(admin.router, payments.router, user.router)

    try:
        await dp.start_polling(bot)
    finally:
        await xui.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
