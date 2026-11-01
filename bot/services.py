import secrets
import time
import uuid as uuidlib

from . import db
from .config import settings
from .xui import xui

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
