from __future__ import annotations

import logging
import re

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.db.database import Database
from bot.filters.auth import IsNotRegistered
from bot.handlers.common import HTML, send_main_menu
from bot.keyboards.user import remove_kb, share_contact_kb
from bot.services.branding import send_welcome_guest
from bot.services.orders import normalize_phone
from bot.texts import fa

router = Router(name="start")
logger = logging.getLogger("guitarine.auth")

_PHONE_LIKE = re.compile(r"^[\d+\s\-()۰-۹٠-٩]+$")


def _display_name(message: Message) -> str | None:
    user = message.from_user
    if not user:
        return None
    parts = [user.first_name or "", user.last_name or ""]
    return " ".join(p for p in parts if p).strip() or None


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database) -> None:
    user = message.from_user
    if not user:
        return

    existing = await db.get_user(user.id)
    if existing and existing["phone"]:
        await send_main_menu(message, db)
        return

    await send_welcome_guest(message, db, share_contact_kb())


@router.message(F.contact)
async def on_contact(message: Message, db: Database) -> None:
    user = message.from_user
    contact = message.contact
    if not user or not contact:
        return

    if contact.user_id is not None and contact.user_id != user.id:
        await send_welcome_guest(message, db, share_contact_kb())
        await message.answer(fa.PHONE_INVALID, parse_mode=HTML)
        return

    phone = normalize_phone(contact.phone_number or "")
    if len(phone) < 10:
        await send_welcome_guest(message, db, share_contact_kb())
        await message.answer(fa.PHONE_INVALID, parse_mode=HTML)
        return

    await db.upsert_user(
        telegram_id=user.id,
        phone=phone,
        full_name=_display_name(message),
        username=user.username,
    )
    await message.answer("✅", reply_markup=remove_kb())
    await send_main_menu(message, db)


@router.message(IsNotRegistered(), F.text, ~F.text.startswith("/"))
async def unregistered_text(message: Message, db: Database) -> None:
    text = (message.text or "").strip()
    if _PHONE_LIKE.match(text):
        await message.answer(fa.PHONE_TYPED, parse_mode=HTML, reply_markup=share_contact_kb())
        return
    await send_welcome_guest(message, db, share_contact_kb())


@router.message(IsNotRegistered())
async def unregistered_other(message: Message, db: Database) -> None:
    await send_welcome_guest(message, db, share_contact_kb())


@router.message(Command("menu"))
async def cmd_menu(message: Message, db: Database) -> None:
    user = message.from_user
    if not user:
        return
    existing = await db.get_user(user.id)
    if not existing or not existing["phone"]:
        await send_welcome_guest(message, db, share_contact_kb())
        return
    await send_main_menu(message, db)
