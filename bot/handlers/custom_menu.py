from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import Config
from bot.db.database import Database
from bot.handlers.catalog import _require_user, _show_cart, _show_products
from bot.handlers.checkout import _run_checkout
from bot.handlers.common import SCREEN_HELP
from bot.keyboards.user import stored_main_menu_reply_kb
from bot.services.branding import send_screen
from bot.services.menu_store import (
    ACTION_CART,
    ACTION_CHECKOUT,
    ACTION_HELP,
    ACTION_MESSAGE,
    ACTION_PRODUCTS,
    get_menu_items,
)
from bot.texts import fa

router = Router(name="custom_menu")


@router.message(F.text)
async def custom_menu_action(
    message: Message,
    db: Database,
    config: Config,
    state: FSMContext,
) -> None:
    text = (message.text or "").strip()
    item = next(
        (candidate for candidate in await get_menu_items(db) if candidate["label"] == text),
        None,
    )
    if not item or not await _require_user(message, db):
        return

    action = item["action"]
    if action == ACTION_PRODUCTS:
        await _show_products(message, db)
    elif action == ACTION_CART:
        await _show_cart(message, db)
    elif action == ACTION_CHECKOUT:
        assert message.from_user
        await _run_checkout(message, message.from_user.id, db, config, state)
    elif action == ACTION_HELP:
        await send_screen(
            message,
            db,
            text=f"{SCREEN_HELP}\n\n{fa.HELP_SHORT}",
            reply_markup=await stored_main_menu_reply_kb(db),
            logo=False,
        )
    elif action == ACTION_MESSAGE:
        await send_screen(
            message,
            db,
            text=item["response_text"],
            reply_markup=await stored_main_menu_reply_kb(db),
            logo=False,
        )