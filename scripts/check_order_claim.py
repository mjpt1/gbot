"""Self-check: two approvals of one order at the same time must deliver only once.

Run: python scripts/check_order_claim.py
"""
import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.db.database import Database
from bot.db.models import ORDER_STATUS_DELIVERING, ORDER_STATUS_PENDING_REVIEW


async def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "t.db")
        await db.connect()
        await db.upsert_user(1, "09120000000")
        order_id = await db.create_order(1, "T1", 1000, ORDER_STATUS_PENDING_REVIEW, [])

        wins = await asyncio.gather(
            *[db.claim_order_status(order_id, ORDER_STATUS_PENDING_REVIEW, ORDER_STATUS_DELIVERING) for _ in range(5)]
        )
        assert wins.count(True) == 1, wins
        assert (await db.get_order_detail(order_id))["status"] == ORDER_STATUS_DELIVERING
        await db.close()
    print("ok: only one approval claimed the order")


asyncio.run(main())
