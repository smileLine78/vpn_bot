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
    currency TEXT DEFAULT 'XTR',
    charge_id TEXT UNIQUE,
    created_at INTEGER
);
CREATE TABLE IF NOT EXISTS crypto_invoices (
    invoice_id INTEGER PRIMARY KEY,
    tg_id INTEGER,
    tariff TEXT,
    status TEXT DEFAULT 'active',
    created_at INTEGER
);
"""


def _connect():
    return aiosqlite.connect(settings.db_path)


async def init():
    os.makedirs(os.path.dirname(settings.db_path) or ".", exist_ok=True)
    async with _connect() as db:
        await db.executescript(SCHEMA)
        # миграция для баз, созданных до появления оплаты в других валютах
        try:
            await db.execute("ALTER TABLE payments ADD COLUMN currency TEXT DEFAULT 'XTR'")
        except aiosqlite.OperationalError:
            pass  # колонка уже есть
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


async def add_payment(tg_id: int, tariff: str, amount: int, currency: str, charge_id: str) -> bool:
    """amount — в минимальных единицах (копейки, центы; для Stars — штуки).
    False, если платёж с таким charge_id уже обработан."""
    async with _connect() as db:
        cur = await db.execute(
            "INSERT OR IGNORE INTO payments (tg_id, tariff, amount, currency, charge_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (tg_id, tariff, amount, currency, charge_id, int(time.time())),
        )
        await db.commit()
        return cur.rowcount > 0


async def add_crypto_invoice(invoice_id: int, tg_id: int, tariff: str):
    async with _connect() as db:
        await db.execute(
            "INSERT OR IGNORE INTO crypto_invoices (invoice_id, tg_id, tariff, created_at) "
            "VALUES (?, ?, ?, ?)",
            (invoice_id, tg_id, tariff, int(time.time())),
        )
        await db.commit()


async def pending_crypto_invoices() -> list[dict]:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM crypto_invoices WHERE status = 'active' AND created_at > ?",
            (int(time.time()) - 86400,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def set_crypto_status(invoice_id: int, status: str):
    async with _connect() as db:
        await db.execute(
            "UPDATE crypto_invoices SET status = ? WHERE invoice_id = ?", (status, invoice_id)
        )
        await db.commit()


async def stats() -> dict:
    now_ms = int(time.time() * 1000)
    async with _connect() as db:
        async def one(sql, *args):
            async with db.execute(sql, args) as cur:
                return (await cur.fetchone())[0] or 0

        async with db.execute(
            "SELECT currency, SUM(amount) FROM payments GROUP BY currency"
        ) as cur:
            revenue = {row[0]: row[1] for row in await cur.fetchall()}

        return {
            "users": await one("SELECT COUNT(*) FROM users"),
            "active": await one("SELECT COUNT(*) FROM users WHERE expiry_ms > ?", now_ms),
            "payments": await one("SELECT COUNT(*) FROM payments"),
            "revenue": revenue,
        }
