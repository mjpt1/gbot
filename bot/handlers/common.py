from __future__ import annotations

from aiogram.types import CallbackQuery, Message

from bot.db.database import Database
from bot.keyboards.user import stored_main_menu_reply_kb
from bot.services.branding import send_main_menu_screen, send_screen

HTML = "HTML"

SCREEN_PRODUCTS = "🎸 گیتارینه — آکوردها و محصولات"
SCREEN_CART = "🛒 سبد خرید"
SCREEN_HELP = "🎵 راهنمای گیتارینه"


async def send_main_menu(target: Message | CallbackQuery, db: Database) -> None:
    await send_main_menu_screen(target, db, await stored_main_menu_reply_kb(db))


async def reply_with_menu(message: Message, db: Database, text: str) -> None:
    await send_screen(
        message,
        db,
        text=text,
        reply_markup=await stored_main_menu_reply_kb(db),
        logo=False,
    )
