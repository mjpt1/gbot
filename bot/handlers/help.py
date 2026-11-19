from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.db.database import Database
from bot.handlers.common import HTML, send_main_menu
from bot.keyboards.user import stored_main_menu_reply_kb
from bot.texts import fa

router = Router(name="help")


@router.message(Command("help"))
async def show_help(message: Message, db: Database) -> None:
    await message.answer(
        fa.HELP_OPEN_PDF,
        parse_mode=HTML,
        reply_markup=await stored_main_menu_reply_kb(db),
    )
