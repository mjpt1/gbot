from __future__ import annotations



import asyncio

import logging

import sys

from pathlib import Path



ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:

    sys.path.insert(0, str(ROOT))



from aiogram import Bot, Dispatcher

from aiogram.fsm.storage.memory import MemoryStorage

from aiogram.types import ErrorEvent



from bot.config import load_config

from bot.db.database import Database

from bot.handlers import admin_notice, catalog, checkout, custom_menu, help as help_handlers, menu, start

from bot.services.telegram_bot import create_bot



logging.basicConfig(

    level=logging.INFO,

    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",

)

logger = logging.getLogger("guitarine")





async def main() -> None:

    config = load_config()

    config.branding_dir.mkdir(parents=True, exist_ok=True)

    config.products_dir.mkdir(parents=True, exist_ok=True)

    config.receipts_dir.mkdir(parents=True, exist_ok=True)

    config.protected_dir.mkdir(parents=True, exist_ok=True)



    db = Database(config.db_path)

    await db.connect()

    await db.seed_admins_from_env(config.admin_ids)

    await db.seed_settings_defaults()

    await db.seed_products_if_empty(config.products_dir)



    bot = create_bot(config)

    dp = Dispatcher(storage=MemoryStorage())

    dp["db"] = db

    dp["config"] = config



    @dp.errors()

    async def on_error(event: ErrorEvent) -> None:

        logger.exception("handler error: %s", event.exception)



    dp.include_router(admin_notice.router)

    dp.include_router(start.router)

    dp.include_router(menu.router)

    dp.include_router(catalog.router)

    dp.include_router(checkout.router)

    dp.include_router(help_handlers.router)

    dp.include_router(custom_menu.router)



    logger.info("Guitarine bot starting (user mode only)…")

    try:

        await dp.start_polling(bot, db=db, config=config)

    finally:

        await db.close()

        await bot.session.close()





if __name__ == "__main__":

    asyncio.run(main())


