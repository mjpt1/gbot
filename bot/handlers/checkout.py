from __future__ import annotations

import re

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.db.database import Database
from bot.db.models import (
    ORDER_STATUS_AWAITING_RECEIPT,
    ORDER_STATUS_PENDING_REVIEW,
)
from bot.handlers.common import HTML, reply_with_menu
from bot.keyboards.labels import BTN_CHECKOUT
from bot.keyboards.user import share_contact_kb, stored_main_menu_reply_kb
from bot.services.branding import send_screen
from bot.services.orders import generate_tracking_code
from bot.services.payment_store import get_payment_settings
from bot.states import CheckoutStates
from bot.texts import fa

router = Router(name="checkout")

_BTN_SPACE_RE = re.compile(r"\s+")


def _normalize_btn(text: str | None) -> str:
    return _BTN_SPACE_RE.sub(" ", (text or "").strip())


def _is_checkout_btn(text: str | None) -> bool:
    return _normalize_btn(text) == _normalize_btn(BTN_CHECKOUT)


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


async def _send_checkout_text(
    target: Message | CallbackQuery,
    db: Database,
    text: str,
    *,
    reply_markup=None,
) -> None:
    if reply_markup is None:
        reply_markup = await stored_main_menu_reply_kb(db)
    await send_screen(
        target,
        db,
        text=text,
        reply_markup=reply_markup,
        logo=False,
    )


async def _send_payment_invoice(
    target: Message | CallbackQuery,
    db: Database,
    config: Config,
    *,
    tracking: str,
    total: int,
) -> bool:
    payment = await get_payment_settings(db, config)
    card = payment["bank_card_display"]
    if not card:
        await _send_checkout_text(target, db, fa.PAYMENT_NOT_CONFIGURED)
        return False

    holder = ""
    if payment["bank_card_holder"]:
        holder = f"👤 به نام: <b>{payment['bank_card_holder']}</b>\n"

    invoice = fa.CHECKOUT_INVOICE.format(
        tracking=tracking,
        amount=fa.format_toman(total),
        card=card,
        holder=holder,
    )
    await _send_checkout_text(
        target,
        db,
        invoice,
        reply_markup=await stored_main_menu_reply_kb(db),
    )
    return True


async def _run_checkout(
    target: Message | CallbackQuery,
    user_id: int,
    db: Database,
    config: Config,
    state: FSMContext,
) -> None:
    open_order = await db.get_user_open_order(user_id)
    if open_order:
        if open_order["status"] == ORDER_STATUS_AWAITING_RECEIPT:
            tracking = open_order["tracking_code"]
            sent = await _send_payment_invoice(
                target,
                db,
                config,
                tracking=tracking,
                total=int(open_order["total"]),
            )
            if sent:
                await state.set_state(CheckoutStates.waiting_receipt)
                await state.update_data(tracking=tracking)
            return

        status_label = fa.ORDER_STATUS_LABELS.get(
            open_order["status"], open_order["status"]
        )
        await _send_checkout_text(
            target,
            db,
            fa.OPEN_ORDER_EXISTS.format(
                tracking=open_order["tracking_code"],
                status=status_label,
            ),
        )
        return

    items = await db.get_cart(user_id)
    if not items:
        await _send_checkout_text(target, db, fa.CART_EMPTY)
        return

    total = await db.cart_total(user_id)
    tracking = generate_tracking_code()
    order_items = []
    for item in items:
        qty = int(item["qty"])
        for _ in range(qty):
            order_items.append(
                {
                    "product_id": int(item["product_id"]),
                    "title": item["title"],
                    "price": int(item["price"]),
                    "file_path": item["file_path"],
                }
            )

    await db.create_order(
        user_id=user_id,
        tracking_code=tracking,
        total=total,
        status=ORDER_STATUS_AWAITING_RECEIPT,
        items=order_items,
    )
    await db.clear_cart(user_id)

    sent = await _send_payment_invoice(
        target,
        db,
        config,
        tracking=tracking,
        total=total,
    )
    if sent:
        await state.set_state(CheckoutStates.waiting_receipt)
        await state.update_data(tracking=tracking)


@router.message(F.text.func(_is_checkout_btn))
async def txt_checkout(
    message: Message,
    db: Database,
    config: Config,
    state: FSMContext,
) -> None:
    if not await _require_user(message, db):
        return
    assert message.from_user
    await _run_checkout(message, message.from_user.id, db, config, state)


@router.callback_query(F.data == "menu:checkout")
async def cb_checkout(
    callback: CallbackQuery,
    db: Database,
    config: Config,
    state: FSMContext,
) -> None:
    if not await _require_user_callback(callback, db):
        return
    assert callback.from_user

    await callback.answer("💳 ثبت سفارش")
    await _run_checkout(callback, callback.from_user.id, db, config, state)


@router.message(CheckoutStates.waiting_receipt, F.photo)
async def receive_receipt_photo(
    message: Message,
    db: Database,
    config: Config,
    bot: Bot,
    state: FSMContext,
) -> None:
    user_row = await _require_user(message, db)
    if not user_row:
        return
    assert message.from_user and message.photo

    data = await state.get_data()
    tracking = data.get("tracking")
    order = None
    if tracking:
        order = await db.get_order_by_tracking(tracking)
    if not order:
        order = await db.get_user_open_order(message.from_user.id)
    if not order or order["status"] != ORDER_STATUS_AWAITING_RECEIPT:
        await reply_with_menu(message, db, fa.ORDER_NOT_FOUND)
        await state.clear()
        return

    photo = message.photo[-1]
    file_id = photo.file_id
    config.receipts_dir.mkdir(parents=True, exist_ok=True)
    local_path = config.receipts_dir / f"order_{order['id']}_{photo.file_unique_id}.jpg"
    await bot.download(photo, destination=local_path)

    await db.save_receipt(int(order["id"]), file_id, str(local_path))
    await db.update_order_status(int(order["id"]), ORDER_STATUS_PENDING_REVIEW)
    await state.clear()

    await reply_with_menu(message, db, fa.RECEIPT_RECEIVED)


@router.message(CheckoutStates.waiting_receipt)
async def waiting_receipt_fallback(message: Message, db: Database) -> None:
    await send_screen(
        message,
        db,
        text=fa.WAITING_RECEIPT,
        reply_markup=await stored_main_menu_reply_kb(db),
        logo=False,
    )
