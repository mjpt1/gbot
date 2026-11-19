from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession

from bot.config import Config

logger = logging.getLogger("guitarine")


def resolve_telegram_proxy(explicit: str = "") -> str:
    """Return proxy URL only when TELEGRAM_PROXY is set in .env (no auto-detect)."""
    if explicit.strip():
        return _normalize_proxy(explicit.strip())
    return ""


def _normalize_proxy(raw: str) -> str:
    if "://" not in raw:
        return f"http://{raw}"
    return raw


def create_bot(config: Config) -> Bot:
    proxy = resolve_telegram_proxy(config.telegram_proxy)
    if proxy:
        logger.info("Telegram API via proxy %s", proxy)
        session = AiohttpSession(proxy=proxy)
        return Bot(token=config.bot_token, session=session)
    logger.info("Telegram API direct (no proxy)")
    return Bot(token=config.bot_token)
