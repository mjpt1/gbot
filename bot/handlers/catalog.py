from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.db.database import Database
from bot.handlers.common import HTML, send_main_menu
from bot.services.branding import send_screen
from bot.keyboards.labels import (
    BTN_CART,
    BTN_CART_CLEAR,
    BTN_CHECKOUT,
    BTN_HELP,
    BTN_MENU,
    BTN_PRODUCTS,
    cart_dec_btn,
    cart_inc_btn,
    cart_rm_btn,
    product_add_btn,
)
from bot.keyboards.user import (
    cart_reply_kb,
    products_reply_kb,
    share_contact_kb,
    stored_main_menu_reply_kb,
)
from bot.texts import fa

router = Router(name="catalog")

_ADD_RE = re.compile(r"^➕\s*(\d+)\.\s+")
_CART_DEC_RE = re.compile(r"^➖\s*کم کردن تعداد\s*[·.]\s*(\d+)\s*$")
_CART_INC_RE = re.compile(r"^➕\s*زیاد کردن تعداد\s*[·.]\s*(\d+)\s*$")
_CART_RM_RE = re.compile(r"^🗑\s*حذف از سبد\s*[·.]\s*(\d+)\s*$")


async def _require_user(message: Message, db: Database):
    user = message.from_user
    if not user:
        return None
    row = await db.get_user(user.id)
    if not row or not row["phone"]:
        await message.answer(
            fa.NEED_AUTH,
            parse_mode=HTML,
            reply_markup=share_contact_kb(),
        )
        return None
    return row


async def _require_user_callback(callback: CallbackQuery, db: Database) -> bool:
    user = callback.from_user
    if not user:
        return False
    row = await db.get_user(user.id)
    if not row or not row["phone"]:
        await callback.answer(fa.NEED_AUTH, show_alert=True)
        return False
    return True


async def _show_products(target: Message | CallbackQuery, db: Database) -> None:
    products = await db.list_active_products()
    if not products:
        await send_screen(
            target,
            db,
            text=fa.CATALOG_EMPTY,
            reply_markup=await stored_main_menu_reply_kb(db),
            logo=False,
        )
        return

    await send_screen(
        target,
        db,
        text=fa.format_products_catalog(products),
        reply_markup=products_reply_kb(products),
        notify="🎸",
        logo=False,
    )


async def _show_cart(
    target: Message | CallbackQuery, db: Database, *, silent: bool = False
) -> None:
    user_id = (
        target.from_user.id
        if isinstance(target, CallbackQuery)
        else target.from_user.id  # type: ignore[union-attr]
    )
    items = await db.get_cart(user_id)
    if not items:
        text = fa.CART_EMPTY
        kb = await stored_main_menu_reply_kb(db)
    else:
        total = sum(int(i["qty"]) * int(i["price"]) for i in items)
        text = fa.format_cart(items, total)
        kb = cart_reply_kb(items)

    await send_screen(
        target, db, text=text, reply_markup=kb, notify=None if silent else "🛒", logo=False
    )


async def _add_by_index(message: Message, db: Database, index: int) -> None:
    products = await db.list_active_products()
    if index < 1 or index > len(products):
        await message.answer(
            "⚠️ محصول یافت نشد.", reply_markup=await stored_main_menu_reply_kb(db)
        )
        return
    product = products[index - 1]
    await db.add_to_cart(message.from_user.id, int(product["id"]))
    await message.answer(
        fa.PRODUCT_ADDED.format(title=product["title"]),
        parse_mode=HTML,
        reply_markup=products_reply_kb(products),
    )


async def _cart_action(message: Message, db: Database, index: int, action: str) -> None:
    items = await db.get_cart(message.from_user.id)
    if index < 1 or index > len(items):
        await message.answer(
            "⚠️ آیتم یافت نشد.", reply_markup=await stored_main_menu_reply_kb(db)
        )
        return
    product_id = int(items[index - 1]["product_id"])
    if action == "dec":
        await db.decrease_cart_item(message.from_user.id, product_id)
    elif action == "inc":
        await db.add_to_cart(message.from_user.id, product_id)
    elif action == "rm":
        await db.remove_cart_item(message.from_user.id, product_id)
    await _show_cart(message, db, silent=True)


# —— Reply keyboard ——

@router.message(F.text == BTN_PRODUCTS)
async def txt_products(message: Message, db: Database) -> None:
    if not await _require_user(message, db):
        return
    await _show_products(message, db)


@router.message(F.text == BTN_CART)
async def txt_cart(message: Message, db: Database) -> None:
    if not await _require_user(message, db):
        return
    await _show_cart(message, db)


@router.message(F.text == BTN_MENU)
async def txt_menu(message: Message, db: Database) -> None:
    if not await _require_user(message, db):
        return
    await send_main_menu(message, db)


@router.message(F.text.regexp(_ADD_RE))
async def txt_add_product(message: Message, db: Database) -> None:
    if not await _require_user(message, db):
        return
    m = _ADD_RE.match((message.text or "").strip())
    if not m:
        return
    await _add_by_index(message, db, int(m.group(1)))


@router.message(F.text.regexp(_CART_DEC_RE))
async def txt_cart_dec(message: Message, db: Database) -> None:
    if not await _require_user(message, db):
        return
    m = _CART_DEC_RE.match((message.text or "").strip())
    if m:
        await _cart_action(message, db, int(m.group(1)), "dec")


@router.message(F.text.regexp(_CART_INC_RE))
async def txt_cart_inc(message: Message, db: Database) -> None:
    if not await _require_user(message, db):
        return
    m = _CART_INC_RE.match((message.text or "").strip())
    if m:
        await _cart_action(message, db, int(m.group(1)), "inc")


@router.message(F.text.regexp(_CART_RM_RE))
async def txt_cart_rm(message: Message, db: Database) -> None:
    if not await _require_user(message, db):
        return
    m = _CART_RM_RE.match((message.text or "").strip())
    if m:
        await _cart_action(message, db, int(m.group(1)), "rm")


@router.message(F.text == BTN_CART_CLEAR)
async def txt_cart_clear(message: Message, db: Database) -> None:
    if not await _require_user(message, db):
        return
    await db.clear_cart(message.from_user.id)
    await message.answer(
        "🗑 سبد پاک شد.", reply_markup=await stored_main_menu_reply_kb(db)
    )


# —— Inline callback (سازگاری) ——

@router.callback_query(F.data == "menu:products")
async def cb_products(callback: CallbackQuery, db: Database) -> None:
    if not await _require_user_callback(callback, db):
        return
    await _show_products(callback, db)


@router.callback_query(F.data == "menu:cart")
async def cb_cart(callback: CallbackQuery, db: Database) -> None:
    if not await _require_user_callback(callback, db):
        return
    await _show_cart(callback, db)


@router.message(Command("products"))
async def cmd_products(message: Message, db: Database) -> None:
    if not await _require_user(message, db):
        return
    await _show_products(message, db)


@router.message(Command("cart"))
async def cmd_cart(message: Message, db: Database) -> None:
    if not await _require_user(message, db):
        return
    await _show_cart(message, db)


@router.callback_query(F.data.startswith("add:"))
async def add_product(callback: CallbackQuery, db: Database) -> None:
    user = callback.from_user
    if not user or not callback.data:
        await callback.answer()
        return
    if not await _require_user_callback(callback, db):
        return
    try:
        product_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer()
        return
    product = await db.get_product(product_id)
    if not product:
        await callback.answer("محصول یافت نشد", show_alert=True)
        return
    await db.add_to_cart(user.id, product_id)
    await callback.answer(f"🎵 {product['title']} ✓", show_alert=False)


@router.callback_query(F.data.startswith("cart:"))
async def edit_cart(callback: CallbackQuery, db: Database) -> None:
    if not await _require_user_callback(callback, db):
        return
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    parts = callback.data.split(":")
    if len(parts) < 2:
        await callback.answer()
        return
    cmd = parts[1]
    if cmd == "noop":
        await callback.answer()
        return
    user_id = callback.from_user.id
    if cmd == "clear":
        await db.clear_cart(user_id)
        await callback.answer("🗑 سبد پاک شد")
        await _show_cart(callback, db, silent=True)
        return
    if len(parts) < 3:
        await callback.answer()
        return
    try:
        product_id = int(parts[2])
    except ValueError:
        await callback.answer()
        return
    if cmd == "inc":
        await db.add_to_cart(user_id, product_id)
        await callback.answer("➕ اضافه شد")
    elif cmd == "dec":
        await db.decrease_cart_item(user_id, product_id)
        await callback.answer("➖ کم شد")
    elif cmd == "rm":
        await db.remove_cart_item(user_id, product_id)
        await callback.answer("🗑 حذف شد")
    else:
        await callback.answer()
        return
    await _show_cart(callback, db, silent=True)
