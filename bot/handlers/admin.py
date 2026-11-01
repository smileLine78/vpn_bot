from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from .. import db, services
from ..config import settings
from ..xui import XUIError

router = Router()


def is_admin(message: Message) -> bool:
    return message.from_user.id in settings.admins


@router.message(Command("stats"))
async def stats(message: Message):
    if not is_admin(message):
        return
    s = await db.stats()
    await message.answer(
        f"👥 Пользователей: {s['users']}\n"
        f"✅ Активных подписок: {s['active']}\n"
        f"💳 Платежей: {s['payments']} ({s['stars']} ⭐)"
    )


@router.message(Command("give"))
async def give(message: Message, command: CommandObject):
    """/give <tg_id> <дней> — выдать или продлить подписку вручную."""
    if not is_admin(message):
        return
    try:
        tg_id, days = (int(x) for x in (command.args or "").split())
    except ValueError:
        await message.answer("Использование: /give <tg_id> <дней>")
        return
    await db.upsert_user(tg_id, None)
    try:
        user = await services.grant(tg_id, days)
    except XUIError as e:
        await message.answer(f"Ошибка: {e}")
        return
    await message.answer(f"Готово. Ссылка: {services.sub_url(user['sub_id'])}")
