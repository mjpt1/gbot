from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent

from bot.config import load_config
from bot.db.database import Database
from bot.handlers import catalog, checkout, custom_menu, help as help_handlers, menu, start
from bot.handlers import admin_notice
from bot.services.telegram_bot import create_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("guitarine")


def _detach_router(router) -> None:
    """Allow module-level routers to be re-attached after a supervised restart."""
    parent = router.parent_router
    if parent is None:
        return
    try:
        parent.sub_routers.remove(router)
    except ValueError:
        pass
    router._parent_router = None


async def run_bot(config, db: Database) -> None:
    bot = create_bot(config)
    dp = Dispatcher(storage=MemoryStorage())
    dp["db"] = db
    dp["config"] = config

    @dp.errors()
    async def on_error(event: ErrorEvent) -> None:
        logger.exception("handler error: %s", event.exception)

    routers = (
        admin_notice.router,
        start.router,
        menu.router,
        catalog.router,
        checkout.router,
        help_handlers.router,
        custom_menu.router,
    )
    for router in routers:
        _detach_router(router)
        dp.include_router(router)

    logger.info("Telegram bot polling…")
    try:
        await dp.start_polling(bot, db=db, config=config)
    finally:
        await bot.session.close()


async def run_web(config) -> None:
    web_config = uvicorn.Config(
        "web.main:app",
        host=config.web_host,
        port=config.web_port,
        log_level="info",
    )
    server = uvicorn.Server(web_config)
    logger.info("Web admin at %s", config.web_base_url)
    await server.serve()


async def _supervise(name: str, coro_factory) -> None:
    while True:
        try:
            await coro_factory()
        except asyncio.CancelledError:
            raise
        except SystemExit as exc:
            logger.error("%s exited (code=%s); restarting in 5s", name, exc.code)
            await asyncio.sleep(5)
        except Exception:
            logger.exception("%s task crashed; restarting in 5s", name)
            await asyncio.sleep(5)


async def main() -> None:
    config = load_config()
    for d in (
        config.branding_dir,
        config.products_dir,
        config.receipts_dir,
        config.protected_dir,
    ):
        d.mkdir(parents=True, exist_ok=True)

    db = Database(config.db_path)
    await db.connect()
    await db.seed_admins_from_env(config.admin_ids)
    await db.seed_settings_defaults()
    await db.seed_products_if_empty(config.products_dir)

    try:
        await asyncio.gather(
            _supervise("bot", lambda: run_bot(config, db)),
            _supervise("web", lambda: run_web(config)),
        )
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
