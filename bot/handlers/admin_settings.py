from __future__ import annotations

import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.filters.logo_upload import AwaitingLogoUpload
from bot.db.database import Database
from bot.handlers.admin import _cb_admin, _msg_admin
from bot.handlers.common import HTML
from bot.keyboards.admin_panel import admin_back_kb, admin_settings_kb
from bot.keyboards.user import share_contact_kb, stored_main_menu_reply_kb
from bot.services.branding import send_main_menu_screen, send_welcome_guest
from bot.states import AdminStates
from bot.texts import fa
from bot.texts.defaults import (
    SETTING_AWAITING_LOGO,
    SETTING_LOGO,
    SETTING_LOGO_PATH,
    SETTING_MENU,
    SETTING_WELCOME,
)

router = Router(name="admin_settings")
logger = logging.getLogger("guitarine.admin_settings")


async def _clear_logo_upload(db: Database, state: FSMContext) -> None:
    await db.set_setting(SETTING_AWAITING_LOGO, "")
    await state.clear()


async def _save_logo_file(
    bot: Bot,
    config: Config,
    db: Database,
    *,
    file_id: str,
    source,
) -> Path:
    config.branding_dir.mkdir(parents=True, exist_ok=True)
    dest = config.branding_dir / "logo.jpg"
    for old in config.branding_dir.glob("logo.*"):
        old.unlink(missing_ok=True)

    await bot.download(source or file_id, destination=dest)
    if not dest.exists() or dest.stat().st_size == 0:
        raise RuntimeError("logo download failed")

    await db.set_setting(SETTING_LOGO, file_id)
    await db.set_setting(SETTING_LOGO_PATH, str(dest.resolve()))
    return dest


@router.callback_query(F.data == "adm:settings")
async def cb_settings(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await _cb_admin(callback, db, config):
        return
    if callback.message:
        await callback.message.answer(
            fa.ADMIN_SETTINGS_PANEL,
            parse_mode=HTML,
            reply_markup=admin_settings_kb(),
        )
    await callback.answer()


@router.callback_query(F.data == "adm:set_welcome")
async def cb_set_welcome(
    callback: CallbackQuery, state: FSMContext, db: Database, config: Config
) -> None:
    if not await _cb_admin(callback, db, config):
        return
    await state.set_state(AdminStates.settings_welcome)
    await callback.answer()
    if callback.message:
        await callback.message.answer(fa.ADMIN_SET_WELCOME, parse_mode=HTML)


@router.callback_query(F.data == "adm:set_menu")
async def cb_set_menu(
    callback: CallbackQuery, state: FSMContext, db: Database, config: Config
) -> None:
    if not await _cb_admin(callback, db, config):
        return
    await state.set_state(AdminStates.settings_menu)
    await callback.answer()
    if callback.message:
        await callback.message.answer(fa.ADMIN_SET_MENU, parse_mode=HTML)


@router.callback_query(F.data == "adm:set_logo")
async def cb_set_logo(
    callback: CallbackQuery, state: FSMContext, db: Database, config: Config
) -> None:
    if not await _cb_admin(callback, db, config):
        return
    await state.set_state(AdminStates.settings_logo)
    await db.set_setting(SETTING_AWAITING_LOGO, str(callback.from_user.id))
    await callback.answer()
    if callback.message:
        await callback.message.answer(fa.ADMIN_SET_LOGO, parse_mode=HTML)


@router.callback_query(F.data == "adm:rm_logo")
async def cb_rm_logo(
    callback: CallbackQuery, db: Database, config: Config
) -> None:
    if not await _cb_admin(callback, db, config):
        return
    await db.set_setting(SETTING_LOGO, "")
    await db.set_setting(SETTING_LOGO_PATH, "")
    await db.set_setting(SETTING_AWAITING_LOGO, "")
    for old in config.branding_dir.glob("logo.*"):
        old.unlink(missing_ok=True)
    await callback.answer("لوگو حذف شد")
    if callback.message:
        await callback.message.answer(fa.ADMIN_LOGO_REMOVED, parse_mode=HTML)


@router.callback_query(F.data == "adm:preview_brand")
async def cb_preview(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await _cb_admin(callback, db, config):
        return
    await callback.answer("پیش‌نمایش")
    if callback.message:
        await send_welcome_guest(callback.message, db, share_contact_kb())
        await send_main_menu_screen(
            callback.message, db, await stored_main_menu_reply_kb(db)
        )


@router.message(AdminStates.settings_welcome, F.text)
async def save_welcome(
    message: Message, db: Database, config: Config, state: FSMContext
) -> None:
    if not await _msg_admin(message, db, config):
        return
    text = (message.text or "").strip()
    if len(text) < 3:
        await message.answer("⚠️ متن خیلی کوتاه است.", parse_mode=HTML)
        return
    await db.set_setting(SETTING_WELCOME, text)
    await state.clear()
    await message.answer(fa.ADMIN_WELCOME_SAVED, parse_mode=HTML, reply_markup=admin_back_kb())


@router.message(AdminStates.settings_menu, F.text)
async def save_menu_text(
    message: Message, db: Database, config: Config, state: FSMContext
) -> None:
    if not await _msg_admin(message, db, config):
        return
    text = (message.text or "").strip()
    if len(text) < 2:
        await message.answer("⚠️ متن خیلی کوتاه است.", parse_mode=HTML)
        return
    await db.set_setting(SETTING_MENU, text)
    await state.clear()
    await message.answer(fa.ADMIN_MENU_SAVED, parse_mode=HTML, reply_markup=admin_back_kb())


@router.message(AwaitingLogoUpload(), F.photo)
async def save_logo_photo(
    message: Message,
    db: Database,
    config: Config,
    state: FSMContext,
    bot: Bot,
) -> None:
    if not await _msg_admin(message, db, config):
        return
    photo = message.photo[-1]
    try:
        await _save_logo_file(
            bot, config, db, file_id=photo.file_id, source=photo
        )
    except Exception:
        logger.exception("logo save failed")
        await message.answer(
            "⚠️ ذخیره لوگو ناموفق بود. دوباره به‌صورت <b>عکس</b> بفرست.",
            parse_mode=HTML,
        )
        return
    await _clear_logo_upload(db, state)
    await message.answer(fa.ADMIN_LOGO_SAVED, parse_mode=HTML, reply_markup=admin_back_kb())
    await send_main_menu_screen(message, db, await stored_main_menu_reply_kb(db))


@router.message(AwaitingLogoUpload(), F.document)
async def save_logo_doc(
    message: Message, db: Database, config: Config, state: FSMContext, bot: Bot
) -> None:
    if not await _msg_admin(message, db, config):
        return
    doc = message.document
    if not doc or not doc.mime_type or not doc.mime_type.startswith("image/"):
        await message.answer(fa.ADMIN_LOGO_INVALID, parse_mode=HTML)
        return
    try:
        await _save_logo_file(
            bot, config, db, file_id=doc.file_id, source=doc
        )
    except Exception:
        logger.exception("logo save failed")
        await message.answer(
            "⚠️ ذخیره لوگو ناموفق بود. دوباره به‌صورت <b>عکس</b> بفرست.",
            parse_mode=HTML,
        )
        return
    await _clear_logo_upload(db, state)
    await message.answer(fa.ADMIN_LOGO_SAVED, parse_mode=HTML, reply_markup=admin_back_kb())
    await send_main_menu_screen(message, db, await stored_main_menu_reply_kb(db))


@router.message(AwaitingLogoUpload())
async def save_logo_invalid(message: Message, db: Database, config: Config) -> None:
    if not await _msg_admin(message, db, config):
        return
    await message.answer(fa.ADMIN_LOGO_INVALID, parse_mode=HTML)
