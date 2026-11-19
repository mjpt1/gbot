from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.db.database import Database
from bot.handlers.common import HTML, SCREEN_HELP, send_main_menu
from bot.keyboards.labels import BTN_HELP
from bot.keyboards.user import share_contact_kb, stored_main_menu_reply_kb
from bot.services.branding import send_screen
from bot.texts import fa

router = Router(name="menu")


async def _require_user_callback(callback: CallbackQuery, db: Database) -> bool:
    user = callback.from_user
    if not user:
        return False
    row = await db.get_user(user.id)
    if not row or not row["phone"]:
        await callback.answer(fa.NEED_AUTH, show_alert=True)
        if callback.message:
            await callback.message.answer(
                fa.NEED_AUTH,
                parse_mode=HTML,
                reply_markup=share_contact_kb(),
            )
        return False
    return True


@router.message(F.text == BTN_HELP)
async def txt_help(message: Message, db: Database) -> None:
    user = message.from_user
    if not user:
        return
    row = await db.get_user(user.id)
    if not row or not row["phone"]:
        await message.answer(fa.NEED_AUTH, parse_mode=HTML, reply_markup=share_contact_kb())
        return
    await send_screen(
        message,
        db,
        text=f"{SCREEN_HELP}\n\n{fa.HELP_SHORT}",
        reply_markup=await stored_main_menu_reply_kb(db),
        logo=False,
    )


@router.callback_query(F.data == "menu:home")
async def menu_home(callback: CallbackQuery, db: Database) -> None:
    if not await _require_user_callback(callback, db):
        return
    await send_main_menu(callback, db)


@router.callback_query(F.data == "menu:help")
async def menu_help(callback: CallbackQuery, db: Database) -> None:
    if not await _require_user_callback(callback, db):
        return
    await send_screen(
        callback,
        db,
        text=f"{SCREEN_HELP}\n\n{fa.HELP_SHORT}",
        reply_markup=await stored_main_menu_reply_kb(db),
        notify="🎵 راهنما",
        logo=False,
    )
