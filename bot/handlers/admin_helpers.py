from __future__ import annotations

from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.db.database import Database
from bot.handlers.common import HTML
from bot.keyboards.admin_panel import admin_main_kb
from bot.texts import fa


async def build_dashboard(db: Database, admin_name: str) -> tuple[str, int]:
    pending = await db.count_pending_orders()
    products = await db.count_active_products()
    admins = len(await db.list_admins())
    text = fa.admin_dashboard(pending, products, admins, admin_name)
    return text, pending


async def send_dashboard(
    target: Message | CallbackQuery, db: Database, admin_name: str
) -> None:
    text, pending = await build_dashboard(db, admin_name)
    kb = admin_main_kb(pending)
    if isinstance(target, CallbackQuery):
        if target.message:
            try:
                await target.message.edit_text(text, parse_mode=HTML, reply_markup=kb)
            except Exception:
                await target.message.answer(text, parse_mode=HTML, reply_markup=kb)
        await target.answer()
    else:
        await target.answer(text, parse_mode=HTML, reply_markup=kb)


async def send_pending_receipts(
    target: Message | CallbackQuery, db: Database
) -> None:
    from bot.keyboards.admin import receipt_actions_kb

    pending = await db.list_pending_orders()
    if not pending:
        text = fa.ADMIN_NO_PENDING
        if isinstance(target, CallbackQuery):
            await target.answer("فیش معلقی نیست", show_alert=True)
            if target.message:
                await target.message.answer(text, parse_mode=HTML)
        else:
            await target.answer(text, parse_mode=HTML)
        return

    header = f"🧾 فیش‌های معلق: <b>{len(pending)}</b>"
    if isinstance(target, CallbackQuery):
        await target.answer()
        if target.message:
            await target.message.answer(header, parse_mode=HTML)
        msg = target.message
    else:
        await target.answer(header, parse_mode=HTML)
        msg = target

    for order in pending:
        items = await db.get_order_items(int(order["id"]))
        product_lines = "\n".join(f"🎵 • {it['title']}" for it in items) or "—"
        caption = fa.ADMIN_RECEIPT_CAPTION.format(
            tracking=order["tracking_code"],
            name=order["full_name"] or "—",
            telegram_id=order["user_id"],
            phone=order["phone"],
            amount=fa.format_toman(int(order["total"])),
            products=product_lines,
        )
        receipt = await db.get_receipt(int(order["id"]))
        kb = receipt_actions_kb(int(order["id"]))
        if receipt and receipt["file_id"]:
            await msg.answer_photo(
                photo=receipt["file_id"],
                caption=caption,
                parse_mode=HTML,
                reply_markup=kb,
            )
        else:
            await msg.answer(caption, parse_mode=HTML, reply_markup=kb)
