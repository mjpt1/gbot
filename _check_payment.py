import asyncio
from bot.config import load_config
from bot.db.database import Database
from bot.services.payment_store import get_payment_settings

async def main():
    config = load_config()
    db = Database(config.db_path)
    await db.connect()
    payment = await get_payment_settings(db, config)
    print("config.bank_card:", repr(config.bank_card))
    print("payment:", payment)
    rows = await db.conn.execute(
        "SELECT key, value FROM bot_settings WHERE key LIKE 'bank%'"
    )
    for row in await rows.fetchall():
        print(dict(row))
    await db.close()

asyncio.run(main())
