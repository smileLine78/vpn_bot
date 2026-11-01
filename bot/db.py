import os
import time

import aiosqlite

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    tg_id INTEGER PRIMARY KEY,
    username TEXT,
    created_at INTEGER,
    trial_used INTEGER DEFAULT 0,
    uuid TEXT,
    sub_id TEXT,
    expiry_ms INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER,
    tariff TEXT,
    amount INTEGER,
    charge_id TEXT UNIQUE,
    created_at INTEGER
);
"""


def _connect():
    return aiosqlite.connect(settings.db_path)


async def init():
    os.makedirs(os.path.dirname(settings.db_path) or ".", exist_ok=True)
    async with _connect() as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def upsert_user(tg_id: int, username: str | None):
    async with _connect() as db:
        await db.execute(
            "INSERT INTO users (tg_id, username, created_at) VALUES (?, ?, ?) "
            "ON CONFLICT(tg_id) DO UPDATE SET username = excluded.username",
            (tg_id, username, int(time.time())),
        )
        await db.commit()


async def get_user(tg_id: int) -> dict | None:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def save_subscription(tg_id: int, uuid: str, sub_id: str, expiry_ms: int):
    async with _connect() as db:
        await db.execute(
            "UPDATE users SET uuid = ?, sub_id = ?, expiry_ms = ? WHERE tg_id = ?",
            (uuid, sub_id, expiry_ms, tg_id),
        )
        await db.commit()


async def mark_trial_used(tg_id: int):
    async with _connect() as db:
        await db.execute("UPDATE users SET trial_used = 1 WHERE tg_id = ?", (tg_id,))
        await db.commit()


async def add_payment(tg_id: int, tariff: str, amount: int, charge_id: str) -> bool:
    """False, если платёж с таким charge_id уже обработан."""
    async with _connect() as db:
        cur = await db.execute(
            "INSERT OR IGNORE INTO payments (tg_id, tariff, amount, charge_id, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (tg_id, tariff, amount, charge_id, int(time.time())),
        )
        await db.commit()
        return cur.rowcount > 0


async def stats() -> dict:
    now_ms = int(time.time() * 1000)
    async with _connect() as db:
        async def one(sql, *args):
            async with db.execute(sql, args) as cur:
                return (await cur.fetchone())[0] or 0

        return {
            "users": await one("SELECT COUNT(*) FROM users"),
            "active": await one("SELECT COUNT(*) FROM users WHERE expiry_ms > ?", now_ms),
            "payments": await one("SELECT COUNT(*) FROM payments"),
            "stars": await one("SELECT SUM(amount) FROM payments"),
        }
