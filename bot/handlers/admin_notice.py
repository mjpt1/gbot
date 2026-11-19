from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import Config
from bot.db.database import Database
from bot.handlers.common import HTML

router = Router(name="admin_notice")


@router.message(Command("admin"))
async def cmd_admin_redirect(message: Message, config: Config) -> None:
    await message.answer(
        f"🎸 مدیریت فقط از <b>پنل وب</b> انجام می‌شود:\n"
        f"<a href=\"{config.web_base_url}\">{config.web_base_url}</a>",
        parse_mode=HTML,
        disable_web_page_preview=True,
    )
