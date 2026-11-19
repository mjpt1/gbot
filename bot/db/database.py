from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite

from bot.db.models import SCHEMA_SQL


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.execute("PRAGMA journal_mode = WAL")
        await self._conn.execute("PRAGMA busy_timeout = 5000")
        await self._conn.executescript(SCHEMA_SQL)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        return self._conn

    async def seed_products_if_empty(self, products_dir: Path) -> None:
        cur = await self.conn.execute("SELECT COUNT(*) AS c FROM products")
        row = await cur.fetchone()
        if row and row["c"] > 0:
            return

        samples = [
            ("آکوردهای مبتدی گیتار", 150_000, "beginner-chords.pdf"),
            ("پکیج آکوردهای پیشرفته", 280_000, "advanced-chords.pdf"),
            ("آکوردهای پاپ ایرانی", 220_000, "iranian-pop.pdf"),
        ]
        for title, price, filename in samples:
            file_path = products_dir / filename
            await self.conn.execute(
                "INSERT INTO products (title, price, file_path, active) VALUES (?, ?, ?, 1)",
                (title, price, str(file_path)),
            )
        await self.conn.commit()

    # —— users ——
    async def get_user(self, telegram_id: int) -> aiosqlite.Row | None:
        cur = await self.conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        return await cur.fetchone()

    async def upsert_user(
        self,
        telegram_id: int,
        phone: str,
        full_name: str | None = None,
        username: str | None = None,
    ) -> None:
        await self.conn.execute(
            """
            INSERT INTO users (telegram_id, phone, full_name, username)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                phone = excluded.phone,
                full_name = COALESCE(excluded.full_name, users.full_name),
                username = COALESCE(excluded.username, users.username)
            """,
            (telegram_id, phone, full_name, username),
        )
        await self.conn.commit()

    # —— products ——
    async def list_active_products(self) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT * FROM products WHERE active = 1 ORDER BY id"
        )
        return list(await cur.fetchall())

    async def get_product(self, product_id: int) -> aiosqlite.Row | None:
        cur = await self.conn.execute(
            "SELECT * FROM products WHERE id = ? AND active = 1", (product_id,)
        )
        return await cur.fetchone()

    async def list_all_products(self) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT * FROM products ORDER BY id DESC"
        )
        return list(await cur.fetchall())

    async def create_product(self, title: str, price: int, file_path: str) -> int:
        cur = await self.conn.execute(
            """
            INSERT INTO products (title, price, file_path, active)
            VALUES (?, ?, ?, 1)
            """,
            (title, price, file_path),
        )
        await self.conn.commit()
        assert cur.lastrowid is not None
        return int(cur.lastrowid)

    async def deactivate_product(self, product_id: int) -> bool:
        cur = await self.conn.execute(
            "UPDATE products SET active = 0 WHERE id = ? AND active = 1",
            (product_id,),
        )
        await self.conn.commit()
        return cur.rowcount > 0

    # —— cart ——
    async def add_to_cart(self, user_id: int, product_id: int) -> None:
        await self.conn.execute(
            """
            INSERT INTO cart_items (user_id, product_id, qty)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, product_id) DO UPDATE SET qty = qty + 1
            """,
            (user_id, product_id),
        )
        await self.conn.commit()

    async def decrease_cart_item(self, user_id: int, product_id: int) -> None:
        cur = await self.conn.execute(
            """
            SELECT qty FROM cart_items
            WHERE user_id = ? AND product_id = ?
            """,
            (user_id, product_id),
        )
        row = await cur.fetchone()
        if not row:
            return
        qty = int(row["qty"]) - 1
        if qty <= 0:
            await self.remove_cart_item(user_id, product_id)
        else:
            await self.conn.execute(
                """
                UPDATE cart_items SET qty = ?
                WHERE user_id = ? AND product_id = ?
                """,
                (qty, user_id, product_id),
            )
            await self.conn.commit()

    async def remove_cart_item(self, user_id: int, product_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM cart_items WHERE user_id = ? AND product_id = ?",
            (user_id, product_id),
        )
        await self.conn.commit()

    async def get_cart(self, user_id: int) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(
            """
            SELECT c.product_id, c.qty, p.title, p.price, p.file_path
            FROM cart_items c
            JOIN products p ON p.id = c.product_id
            WHERE c.user_id = ? AND p.active = 1
            ORDER BY c.product_id
            """,
            (user_id,),
        )
        return list(await cur.fetchall())

    async def clear_cart(self, user_id: int) -> None:
        await self.conn.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
        await self.conn.commit()

    async def cart_total(self, user_id: int) -> int:
        cur = await self.conn.execute(
            """
            SELECT COALESCE(SUM(c.qty * p.price), 0) AS total
            FROM cart_items c
            JOIN products p ON p.id = c.product_id
            WHERE c.user_id = ? AND p.active = 1
            """,
            (user_id,),
        )
        row = await cur.fetchone()
        return int(row["total"]) if row else 0

    # —— orders ——
    async def create_order(
        self,
        user_id: int,
        tracking_code: str,
        total: int,
        status: str,
        items: list[dict[str, Any]],
    ) -> int:
        cur = await self.conn.execute(
            """
            INSERT INTO orders (tracking_code, user_id, total, status)
            VALUES (?, ?, ?, ?)
            """,
            (tracking_code, user_id, total, status),
        )
        order_id = cur.lastrowid
        assert order_id is not None
        for item in items:
            await self.conn.execute(
                """
                INSERT INTO order_items (order_id, product_id, title, price, file_path)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    item["product_id"],
                    item["title"],
                    item["price"],
                    item["file_path"],
                ),
            )
        await self.conn.commit()
        return int(order_id)

    async def get_order(self, order_id: int) -> aiosqlite.Row | None:
        cur = await self.conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        return await cur.fetchone()

    async def get_order_by_tracking(self, tracking_code: str) -> aiosqlite.Row | None:
        cur = await self.conn.execute(
            "SELECT * FROM orders WHERE tracking_code = ?", (tracking_code,)
        )
        return await cur.fetchone()

    async def get_user_open_order(self, user_id: int) -> aiosqlite.Row | None:
        cur = await self.conn.execute(
            """
            SELECT * FROM orders
            WHERE user_id = ? AND status IN ('awaiting_receipt', 'pending_review')
            ORDER BY id DESC LIMIT 1
            """,
            (user_id,),
        )
        return await cur.fetchone()

    async def list_pending_orders(self) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(
            """
            SELECT o.*, u.phone, u.full_name, u.username
            FROM orders o
            JOIN users u ON u.telegram_id = o.user_id
            WHERE o.status = 'pending_review'
            ORDER BY o.id
            """
        )
        return list(await cur.fetchall())

    async def list_all_orders(self, limit: int = 100) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(
            """
            SELECT o.*, u.phone, u.full_name, u.username
            FROM orders o
            JOIN users u ON u.telegram_id = o.user_id
            ORDER BY o.id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return list(await cur.fetchall())

    async def update_order_status(self, order_id: int, status: str) -> None:
        await self.conn.execute(
            """
            UPDATE orders
            SET status = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (status, order_id),
        )
        await self.conn.commit()

    async def claim_order_status(self, order_id: int, expected: str, status: str) -> bool:
        """Move an order from `expected` to `status` in one step; False if someone else got there first."""
        cur = await self.conn.execute(
            """
            UPDATE orders
            SET status = ?, updated_at = datetime('now')
            WHERE id = ? AND status = ?
            """,
            (status, order_id, expected),
        )
        await self.conn.commit()
        return cur.rowcount == 1

    async def get_order_items(self, order_id: int) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT * FROM order_items WHERE order_id = ? ORDER BY id",
            (order_id,),
        )
        return list(await cur.fetchall())

    async def get_order_detail(self, order_id: int) -> aiosqlite.Row | None:
        cur = await self.conn.execute(
            """
            SELECT o.*, u.phone, u.full_name, u.username
            FROM orders o
            JOIN users u ON u.telegram_id = o.user_id
            WHERE o.id = ?
            """,
            (order_id,),
        )
        return await cur.fetchone()

    # —— receipts ——
    async def save_receipt(
        self, order_id: int, file_id: str, local_path: str | None
    ) -> None:
        await self.conn.execute(
            """
            INSERT INTO receipts (order_id, file_id, local_path)
            VALUES (?, ?, ?)
            ON CONFLICT(order_id) DO UPDATE SET
                file_id = excluded.file_id,
                local_path = excluded.local_path,
                created_at = datetime('now')
            """,
            (order_id, file_id, local_path),
        )
        await self.conn.commit()

    async def get_receipt(self, order_id: int) -> aiosqlite.Row | None:
        cur = await self.conn.execute(
            "SELECT * FROM receipts WHERE order_id = ?", (order_id,)
        )
        return await cur.fetchone()

    async def count_active_products(self) -> int:
        cur = await self.conn.execute(
            "SELECT COUNT(*) AS c FROM products WHERE active = 1"
        )
        row = await cur.fetchone()
        return int(row["c"]) if row else 0

    async def count_pending_orders(self) -> int:
        cur = await self.conn.execute(
            "SELECT COUNT(*) AS c FROM orders WHERE status = 'pending_review'"
        )
        row = await cur.fetchone()
        return int(row["c"]) if row else 0

    async def get_admin_metrics(self) -> dict[str, int]:
        cur = await self.conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN status = 'pending_review' THEN 1 ELSE 0 END), 0)
                    AS pending,
                COALESCE(SUM(CASE WHEN status = 'delivered'
                    AND date(updated_at) = date('now') THEN 1 ELSE 0 END), 0)
                    AS approved_today,
                COALESCE(SUM(CASE WHEN status = 'rejected'
                    AND date(updated_at) = date('now') THEN 1 ELSE 0 END), 0)
                    AS rejected_today,
                COALESCE(SUM(CASE WHEN status = 'delivered'
                    AND date(updated_at) = date('now') THEN total ELSE 0 END), 0)
                    AS revenue_today,
                COALESCE(SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END), 0)
                    AS delivered_total,
                COALESCE(SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END), 0)
                    AS rejected_total,
                COUNT(*) AS orders_total
            FROM orders
            """
        )
        row = await cur.fetchone()
        return {
            key: int(row[key] or 0) if row else 0
            for key in (
                "pending",
                "approved_today",
                "rejected_today",
                "revenue_today",
                "delivered_total",
                "rejected_total",
                "orders_total",
            )
        }

    async def get_order_activity(self, days: int = 7) -> list[dict[str, int | str]]:
        days = max(2, min(days, 31))
        cur = await self.conn.execute(
            """
            WITH RECURSIVE dates(day) AS (
                SELECT date('now', ?)
                UNION ALL
                SELECT date(day, '+1 day') FROM dates WHERE day < date('now')
            )
            SELECT
                dates.day,
                COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN 1 ELSE 0 END), 0)
                    AS delivered,
                COALESCE(SUM(CASE WHEN o.status = 'rejected' THEN 1 ELSE 0 END), 0)
                    AS rejected,
                COUNT(o.id) AS total
            FROM dates
            LEFT JOIN orders o ON date(o.created_at) = dates.day
            GROUP BY dates.day
            ORDER BY dates.day
            """,
            (f"-{days - 1} days",),
        )
        return [dict(row) for row in await cur.fetchall()]

    # —— admins ——
    async def seed_admins_from_env(self, env_admin_ids: frozenset[int]) -> None:
        for admin_id in env_admin_ids:
            await self.conn.execute(
                """
                INSERT INTO admins (telegram_id, added_by, full_name)
                VALUES (?, NULL, 'super')
                ON CONFLICT(telegram_id) DO NOTHING
                """,
                (admin_id,),
            )
        await self.conn.commit()

    async def is_db_admin(self, telegram_id: int) -> bool:
        cur = await self.conn.execute(
            "SELECT 1 FROM admins WHERE telegram_id = ?", (telegram_id,)
        )
        return await cur.fetchone() is not None

    async def list_admins(self) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT * FROM admins ORDER BY telegram_id"
        )
        return list(await cur.fetchall())

    async def add_admin(
        self,
        telegram_id: int,
        added_by: int,
        full_name: str | None = None,
        username: str | None = None,
    ) -> bool:
        cur = await self.conn.execute(
            "SELECT 1 FROM admins WHERE telegram_id = ?", (telegram_id,)
        )
        if await cur.fetchone():
            return False
        await self.conn.execute(
            """
            INSERT INTO admins (telegram_id, added_by, full_name, username)
            VALUES (?, ?, ?, ?)
            """,
            (telegram_id, added_by, full_name, username),
        )
        await self.conn.commit()
        return True

    async def remove_admin(self, telegram_id: int, env_admin_ids: frozenset[int]) -> bool:
        if telegram_id in env_admin_ids:
            return False
        cur = await self.conn.execute(
            "DELETE FROM admins WHERE telegram_id = ?", (telegram_id,)
        )
        await self.conn.commit()
        return cur.rowcount > 0

    # —— customers ——
    async def list_customers(self) -> list:
        """Every registered user with their order totals, newest first.

        Only delivered orders count towards `spent` — pending or rejected ones
        are not money in the till.
        """
        cur = await self.conn.execute(
            """
            SELECT
                u.telegram_id,
                u.full_name,
                u.username,
                u.phone,
                u.created_at,
                COUNT(o.id) AS orders_count,
                COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN 1 ELSE 0 END), 0)
                    AS delivered_count,
                COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.total ELSE 0 END), 0)
                    AS spent,
                MAX(o.created_at) AS last_order_at
            FROM users u
            LEFT JOIN orders o ON o.user_id = u.telegram_id
            GROUP BY u.telegram_id
            ORDER BY u.created_at DESC
            """
        )
        return await cur.fetchall()

    # —— bot settings ——
    async def seed_settings_defaults(self) -> None:
        from bot.texts.defaults import (
            DEFAULT_MENU,
            DEFAULT_WELCOME,
            SETTING_AWAITING_LOGO,
            SETTING_BANK_CARD,
            SETTING_BANK_CARD_HOLDER,
            SETTING_LOGO,
            SETTING_LOGO_PATH,
            SETTING_MENU,
            SETTING_WELCOME,
        )

        defaults = {
            SETTING_WELCOME: DEFAULT_WELCOME,
            SETTING_MENU: DEFAULT_MENU,
            SETTING_LOGO: "",
            SETTING_LOGO_PATH: "",
            SETTING_AWAITING_LOGO: "",
            SETTING_BANK_CARD: "",
            SETTING_BANK_CARD_HOLDER: "",
        }
        for key, value in defaults.items():
            await self.conn.execute(
                """
                INSERT INTO bot_settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO NOTHING
                """,
                (key, value),
            )
        await self.conn.commit()

    async def get_setting(self, key: str, default: str = "") -> str:
        cur = await self.conn.execute(
            "SELECT value FROM bot_settings WHERE key = ?", (key,)
        )
        row = await cur.fetchone()
        return row["value"] if row else default

    async def set_setting(self, key: str, value: str) -> None:
        await self.conn.execute(
            """
            INSERT INTO bot_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        await self.conn.commit()

    async def get_branding(self) -> dict[str, str]:
        from bot.texts.defaults import (
            DEFAULT_MENU,
            DEFAULT_WELCOME,
            SETTING_LOGO,
            SETTING_LOGO_PATH,
            SETTING_MENU,
            SETTING_WELCOME,
        )

        return {
            "welcome_text": await self.get_setting(SETTING_WELCOME, DEFAULT_WELCOME),
            "menu_text": await self.get_setting(SETTING_MENU, DEFAULT_MENU),
            "logo_file_id": await self.get_setting(SETTING_LOGO, ""),
            "logo_path": await self.get_setting(SETTING_LOGO_PATH, ""),
        }
