from __future__ import annotations

import logging
from pathlib import Path

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
)

from bot.db.database import Database

logger = logging.getLogger("guitarine.branding")

HTML = "HTML"


def _split_markup(reply_markup):
    inline_kb = (
        reply_markup if isinstance(reply_markup, InlineKeyboardMarkup) else None
    )
    reply_kb = (
        reply_markup if isinstance(reply_markup, ReplyKeyboardMarkup) else None
    )
    return inline_kb, reply_kb


async def _get_brand_safe(db: Database) -> dict[str, str]:
    try:
        return await db.get_branding()
    except Exception as exc:
        logger.warning("get_branding failed: %s", exc)
        from bot.texts.defaults import DEFAULT_MENU, DEFAULT_WELCOME

        return {
            "welcome_text": DEFAULT_WELCOME,
            "menu_text": DEFAULT_MENU,
            "logo_file_id": "",
            "logo_path": "",
        }


async def _send_photo_with_caption(
    bot,
    chat_id: int,
    *,
    photo,
    caption: str,
    inline_kb: InlineKeyboardMarkup | None,
) -> None:
    await bot.send_photo(
        chat_id,
        photo=photo,
        caption=caption,
        parse_mode=HTML,
        reply_markup=inline_kb,
    )


async def _send_logo_message(
    bot,
    chat_id: int,
    *,
    brand: dict[str, str],
    caption: str,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | None,
) -> None:
    inline_kb, reply_kb = _split_markup(reply_markup)
    logo_path = brand.get("logo_path") or ""
    file_id = brand.get("logo_file_id") or ""
    path = Path(logo_path) if logo_path else None
    safe_caption = caption.strip() or "🎼"

    async def _finish() -> None:
        if reply_kb:
            await bot.send_message(
                chat_id, "👇 منوی پایین صفحه", reply_markup=reply_kb
            )

    if path and path.exists():
        try:
            await _send_photo_with_caption(
                bot,
                chat_id,
                photo=FSInputFile(path),
                caption=safe_caption,
                inline_kb=inline_kb,
            )
            await _finish()
            return
        except TelegramBadRequest as exc:
            logger.warning("logo photo from path failed: %s", exc)

    if file_id:
        try:
            await _send_photo_with_caption(
                bot,
                chat_id,
                photo=file_id,
                caption=safe_caption,
                inline_kb=inline_kb,
            )
            await _finish()
            return
        except TelegramBadRequest:
            try:
                await bot.send_document(
                    chat_id,
                    document=file_id,
                    caption=safe_caption,
                    parse_mode=HTML,
                    reply_markup=inline_kb,
                )
                await _finish()
                return
            except TelegramBadRequest as exc:
                logger.warning("logo send failed: %s", exc)

    await bot.send_message(
        chat_id,
        safe_caption,
        parse_mode=HTML,
        reply_markup=reply_markup,
    )


async def _deliver_screen(
    bot,
    chat_id: int,
    *,
    brand: dict[str, str],
    caption: str,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | None,
    has_logo: bool,
) -> None:
    if has_logo:
        await _send_logo_message(
            bot, chat_id, brand=brand, caption=caption, reply_markup=reply_markup
        )
        return
    await bot.send_message(
        chat_id, caption, parse_mode=HTML, reply_markup=reply_markup
    )


async def _send_with_fallback(
    bot,
    chat_id: int,
    *,
    brand: dict[str, str],
    caption: str,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | None,
    has_logo: bool,
) -> None:
    safe_caption = caption.strip() or "🎼"
    try:
        await _deliver_screen(
            bot,
            chat_id,
            brand=brand,
            caption=safe_caption,
            reply_markup=reply_markup,
            has_logo=has_logo,
        )
    except Exception as exc:
        logger.warning("send_screen primary failed: %s", exc)
        try:
            await bot.send_message(
                chat_id,
                safe_caption,
                parse_mode=HTML,
                reply_markup=reply_markup,
            )
        except Exception as exc2:
            logger.warning("send_screen text fallback failed: %s", exc2)
            await bot.send_message(chat_id, safe_caption)


async def send_screen(
    target: Message | CallbackQuery,
    db: Database,
    *,
    text: str,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | None = None,
    logo: bool = False,
    notify: str | None = None,
) -> None:
    brand = await _get_brand_safe(db)
    caption = text.strip() or "🎼"
    has_logo = logo and (brand.get("logo_path") or brand.get("logo_file_id"))

    if isinstance(target, CallbackQuery):
        msg = target.message
        if not msg:
            await target.answer()
            return
        chat_id = msg.chat.id
        bot = msg.bot
        assert bot

        try:
            await _send_with_fallback(
                bot,
                chat_id,
                brand=brand,
                caption=caption,
                reply_markup=reply_markup,
                has_logo=has_logo,
            )
            try:
                await msg.delete()
            except Exception:
                pass
        finally:
            try:
                await target.answer(notify or "")
            except Exception:
                pass
        return

    bot = target.bot
    assert bot
    await _send_with_fallback(
        bot,
        target.chat.id,
        brand=brand,
        caption=caption,
        reply_markup=reply_markup,
        has_logo=has_logo,
    )


async def send_welcome_guest(message: Message, db: Database, reply_markup) -> None:
    brand = await _get_brand_safe(db)
    caption = brand["welcome_text"].strip() or "🎼"
    has_logo = brand.get("logo_path") or brand.get("logo_file_id")

    bot = message.bot
    assert bot
    await _send_with_fallback(
        bot,
        message.chat.id,
        brand=brand,
        caption=caption,
        reply_markup=reply_markup,
        has_logo=bool(has_logo),
    )


async def send_main_menu_screen(
    target: Message | CallbackQuery, db: Database, reply_markup
) -> None:
    brand = await _get_brand_safe(db)
    await send_screen(
        target,
        db,
        text=brand["menu_text"],
        reply_markup=reply_markup,
        logo=True,
    )
