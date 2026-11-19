from __future__ import annotations

import logging
from pathlib import Path

import aiohttp

from bot.config import Config
from bot.services.telegram_bot import resolve_telegram_proxy

logger = logging.getLogger("guitarine.telegram")

_API_TIMEOUT = aiohttp.ClientTimeout(total=180)


def _api_url(config: Config, method: str) -> str:
    return f"https://api.telegram.org/bot{config.bot_token}/{method}"


def _proxy(config: Config) -> str | None:
    value = resolve_telegram_proxy(config.telegram_proxy)
    return value or None


async def send_message(
    config: Config,
    chat_id: int,
    text: str,
    *,
    parse_mode: str = "HTML",
) -> None:
    url = _api_url(config, "sendMessage")
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    async with aiohttp.ClientSession(timeout=_API_TIMEOUT) as session:
        async with session.post(url, json=payload, proxy=_proxy(config)) as resp:
            body = await resp.json()
    if not body.get("ok"):
        raise RuntimeError(body.get("description") or "sendMessage failed")
    logger.debug("sendMessage ok chat=%s", chat_id)


async def send_document(
    config: Config,
    chat_id: int,
    path: Path,
    *,
    filename: str,
    caption: str,
    parse_mode: str = "HTML",
) -> None:
    url = _api_url(config, "sendDocument")
    file_bytes = path.read_bytes()
    form = aiohttp.FormData()
    form.add_field("chat_id", str(chat_id))
    form.add_field("caption", caption)
    form.add_field("parse_mode", parse_mode)
    form.add_field(
        "document",
        file_bytes,
        filename=filename,
        content_type="application/pdf",
    )
    async with aiohttp.ClientSession(timeout=_API_TIMEOUT) as session:
        async with session.post(url, data=form, proxy=_proxy(config)) as resp:
            body = await resp.json()
    if not body.get("ok"):
        raise RuntimeError(body.get("description") or "sendDocument failed")
    logger.info("sendDocument ok chat=%s file=%s", chat_id, filename)
