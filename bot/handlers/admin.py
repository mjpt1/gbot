from __future__ import annotations

import re
import secrets
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot.config import Config
from bot.db.database import Database
from bot.db.models import (
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_DELIVERING,
    ORDER_STATUS_PENDING_REVIEW,
    ORDER_STATUS_REJECTED,
)
from bot.handlers.admin_helpers import send_dashboard, send_pending_receipts
from bot.handlers.common import HTML
from bot.keyboards.admin import receipt_actions_kb
from bot.keyboards.admin_panel import (
    admin_after_product_kb,
    admin_back_kb,
    admin_batch_collect_kb,
    admin_list_kb,
)
from bot.services.admin_access import is_admin, is_super_admin
from bot.services.pdf_protect import protect_pdf
from bot.states import AdminStates
from bot.texts import fa
from bot.texts.defaults import SETTING_AWAITING_LOGO

router = Router(name="admin")


def _name(user) -> str:
    if not user:
        return "ادمین"
    parts = [user.first_name or "", user.last_name or ""]
    return " ".join(p for p in parts if p).strip() or "ادمین"


async def _msg_admin(message: Message, db: Database, config: Config) -> bool:
    user = message.from_user
    if not user or not await is_admin(user.id, db, config):
        await message.answer(fa.ADMIN_ONLY, parse_mode=HTML)
        return False
    return True


async def _cb_admin(callback: CallbackQuery, db: Database, config: Config) -> bool:
    user = callback.from_user
    if not user or not await is_admin(user.id, db, config):
        await callback.answer(fa.ADMIN_ONLY, show_alert=True)
        return False
    return True


# —— پنل ——


@router.message(Command("admin"))
async def cmd_admin_panel(message: Message, db: Database, config: Config) -> None:
    if not await _msg_admin(message, db, config):
        return
    await send_dashboard(message, db, _name(message.from_user))


@router.callback_query(F.data == "adm:home")
async def cb_admin_home(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await _cb_admin(callback, db, config):
        return
    await send_dashboard(callback, db, _name(callback.from_user))


@router.callback_query(F.data == "adm:pending")
async def cb_admin_pending(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await _cb_admin(callback, db, config):
        return
    await send_pending_receipts(callback, db)


# —— یک محصول ——


@router.message(Command("add_product"))
@router.callback_query(F.data == "adm:add_one")
async def start_add_product(
    event: Message | CallbackQuery, config: Config, state: FSMContext, db: Database
) -> None:
    if isinstance(event, CallbackQuery):
        if not await _cb_admin(event, db, config):
            return
        await event.answer()
        await state.set_state(AdminStates.product_title)
        await event.message.answer(fa.ADMIN_ADD_TITLE, parse_mode=HTML)  # type: ignore[union-attr]
    else:
        if not await _msg_admin(event, db, config):
            return
        await state.set_state(AdminStates.product_title)
        await event.answer(fa.ADMIN_ADD_TITLE, parse_mode=HTML)


@router.message(AdminStates.product_title, F.text)
async def admin_product_title(
    message: Message, config: Config, state: FSMContext, db: Database
) -> None:
    if not await _msg_admin(message, db, config):
        return
    title = (message.text or "").strip()
    if len(title) < 2:
        await message.answer("⚠️ عنوان خیلی کوتاه است.", parse_mode=HTML)
        return
    await state.update_data(title=title)
    await state.set_state(AdminStates.product_price)
    await message.answer(fa.ADMIN_ADD_PRICE, parse_mode=HTML)


@router.message(AdminStates.product_price, F.text)
async def admin_product_price(
    message: Message, config: Config, state: FSMContext, db: Database
) -> None:
    if not await _msg_admin(message, db, config):
        return
    raw = (message.text or "").strip().replace(",", "").replace("،", "")
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(fa.ADMIN_PRICE_INVALID, parse_mode=HTML)
        return
    await state.update_data(price=int(raw))
    await state.set_state(AdminStates.product_pdf)
    await message.answer(fa.ADMIN_ADD_PDF, parse_mode=HTML)


async def _save_pdf_product(
    bot: Bot,
    db: Database,
    config: Config,
    *,
    title: str,
    price: int,
    file_id: str,
    file_name: str,
) -> int:
    safe_name = re.sub(r"[^\w\-]", "_", file_name.rsplit(".", 1)[0])[:40]
    filename = f"{safe_name}_{secrets.token_hex(4)}.pdf"
    dest = config.products_dir / filename
    config.products_dir.mkdir(parents=True, exist_ok=True)
    await bot.download(file_id, destination=dest)
    return await db.create_product(title, price, str(dest))


@router.message(AdminStates.product_pdf, F.document)
async def admin_product_pdf(
    message: Message,
    db: Database,
    config: Config,
    bot: Bot,
    state: FSMContext,
) -> None:
    if not await _msg_admin(message, db, config):
        return
    doc = message.document
    if not doc or not doc.file_name or not doc.file_name.lower().endswith(".pdf"):
        await message.answer(fa.ADMIN_PDF_INVALID, parse_mode=HTML)
        return

    data = await state.get_data()
    title = data.get("title", "product")
    price = int(data.get("price", 0))
    product_id = await _save_pdf_product(
        bot,
        db,
        config,
        title=title,
        price=price,
        file_id=doc.file_id,
        file_name=doc.file_name,
    )
    await state.clear()

    await message.answer(
        fa.ADMIN_ADD_DONE.format(
            title=title,
            price=fa.format_toman(price),
            id=product_id,
        ),
        parse_mode=HTML,
        reply_markup=admin_after_product_kb(),
    )


@router.message(AdminStates.product_pdf)
async def admin_product_pdf_invalid(
    message: Message, config: Config, db: Database
) -> None:
    if not await _msg_admin(message, db, config):
        return
    await message.answer(fa.ADMIN_PDF_INVALID, parse_mode=HTML)


# —— چند محصول ——


@router.callback_query(F.data == "adm:add_batch")
async def start_batch(
    callback: CallbackQuery, config: Config, state: FSMContext, db: Database
) -> None:
    if not await _cb_admin(callback, db, config):
        return
    await state.set_state(AdminStates.batch_collect)
    await state.update_data(batch_files=[], batch_index=0, batch_saved=0)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            fa.ADMIN_BATCH_START,
            parse_mode=HTML,
            reply_markup=admin_batch_collect_kb(0),
        )


@router.message(AdminStates.batch_collect, F.document)
async def batch_collect_pdf(
    message: Message, config: Config, state: FSMContext, db: Database
) -> None:
    if not await _msg_admin(message, db, config):
        return
    doc = message.document
    if not doc or not doc.file_name or not doc.file_name.lower().endswith(".pdf"):
        await message.answer(fa.ADMIN_PDF_INVALID, parse_mode=HTML)
        return

    data = await state.get_data()
    files: list = list(data.get("batch_files", []))
    files.append({"file_id": doc.file_id, "file_name": doc.file_name})
    await state.update_data(batch_files=files)
    await message.answer(
        fa.ADMIN_BATCH_COLLECTED.format(count=len(files)),
        parse_mode=HTML,
        reply_markup=admin_batch_collect_kb(len(files)),
    )


@router.callback_query(F.data == "adm:batch_cancel")
async def batch_cancel(
    callback: CallbackQuery, state: FSMContext, db: Database, config: Config
) -> None:
    if not await _cb_admin(callback, db, config):
        return
    await state.clear()
    await callback.answer("لغو شد")
    if callback.message:
        await callback.message.answer(fa.ADMIN_ADD_CANCEL, parse_mode=HTML)


@router.callback_query(F.data == "adm:batch_done")
async def batch_done(
    callback: CallbackQuery, state: FSMContext, db: Database, config: Config
) -> None:
    if not await _cb_admin(callback, db, config):
        return
    data = await state.get_data()
    files: list = data.get("batch_files", [])
    if not files:
        await callback.answer("هنوز فایلی نیست", show_alert=True)
        return
    await state.update_data(batch_index=0, batch_saved=0)
    await state.set_state(AdminStates.batch_title)
    await callback.answer()
    await _ask_batch_title(callback.message, state)


async def _ask_batch_title(message: Message | None, state: FSMContext) -> None:
    if not message:
        return
    data = await state.get_data()
    files: list = data.get("batch_files", [])
    idx = int(data.get("batch_index", 0))
    current = files[idx]
    await message.answer(
        fa.ADMIN_BATCH_ITEM_TITLE.format(
            current=idx + 1,
            total=len(files),
            file=current["file_name"],
        ),
        parse_mode=HTML,
    )


@router.message(AdminStates.batch_title, F.text)
async def batch_title(
    message: Message, config: Config, state: FSMContext, db: Database
) -> None:
    if not await _msg_admin(message, db, config):
        return
    title = (message.text or "").strip()
    if len(title) < 2:
        await message.answer("⚠️ عنوان کوتاه است.", parse_mode=HTML)
        return
    await state.update_data(batch_current_title=title)
    await state.set_state(AdminStates.batch_price)
    await message.answer(
        fa.ADMIN_BATCH_ITEM_PRICE.format(title=title),
        parse_mode=HTML,
    )


@router.message(AdminStates.batch_price, F.text)
async def batch_price(
    message: Message,
    db: Database,
    config: Config,
    bot: Bot,
    state: FSMContext,
) -> None:
    if not await _msg_admin(message, db, config):
        return
    raw = (message.text or "").strip().replace(",", "").replace("،", "")
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(fa.ADMIN_PRICE_INVALID, parse_mode=HTML)
        return

    price = int(raw)
    data = await state.get_data()
    files: list = data.get("batch_files", [])
    idx = int(data.get("batch_index", 0))
    title = data.get("batch_current_title", "product")
    file_info = files[idx]

    await _save_pdf_product(
        bot,
        db,
        config,
        title=title,
        price=price,
        file_id=file_info["file_id"],
        file_name=file_info["file_name"],
    )

    saved = int(data.get("batch_saved", 0)) + 1
    idx += 1
    await state.update_data(batch_index=idx, batch_saved=saved)

    if idx >= len(files):
        await state.clear()
        await message.answer(
            fa.ADMIN_BATCH_DONE.format(count=saved),
            parse_mode=HTML,
            reply_markup=admin_back_kb(),
        )
        return

    await state.set_state(AdminStates.batch_title)
    await _ask_batch_title(message, state)


# —— لیست محصولات ——


@router.message(Command("my_products"))
@router.callback_query(F.data == "adm:products")
async def show_products(
    event: Message | CallbackQuery, db: Database, config: Config
) -> None:
    if isinstance(event, CallbackQuery):
        if not await _cb_admin(event, db, config):
            return
        await event.answer()
        answer = event.message.answer  # type: ignore[union-attr]
    else:
        if not await _msg_admin(event, db, config):
            return
        answer = event.answer

    products = await db.list_all_products()
    if not products:
        await answer(
            fa.ADMIN_PRODUCTS_LIST + "محصولی ثبت نشده.",
            parse_mode=HTML,
            reply_markup=admin_back_kb(),
        )
        return

    lines = [fa.ADMIN_PRODUCTS_LIST]
    for p in products:
        status = "✅" if p["active"] else "❌"
        lines.append(
            fa.ADMIN_PRODUCT_LINE.format(
                status=status,
                id=p["id"],
                title=p["title"],
                price=fa.format_toman(int(p["price"])),
                file=Path(p["file_path"]).name,
            )
        )
    lines.append("\n🗑 حذف: <code>/del_product ID</code>")
    await answer("\n".join(lines), parse_mode=HTML, reply_markup=admin_back_kb())


@router.message(Command("del_product"))
async def cmd_del_product(message: Message, db: Database, config: Config) -> None:
    if not await _msg_admin(message, db, config):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer("⚠️ <code>/del_product 2</code>", parse_mode=HTML)
        return
    product_id = int(parts[1].strip())
    ok = await db.deactivate_product(product_id)
    text = fa.ADMIN_DEL_OK.format(id=product_id) if ok else fa.ADMIN_DEL_FAIL
    await message.answer(text, parse_mode=HTML, reply_markup=admin_back_kb())


# —— ادمین‌ها ——


async def _render_admins_list(
    target: Message | CallbackQuery, db: Database, config: Config
) -> None:
    user = target.from_user
    if not user:
        return
    super_ = is_super_admin(user.id, config)
    admins = await db.list_admins()
    lines = [fa.ADMIN_LIST_HEADER]
    for row in admins:
        star = "⭐" if row["telegram_id"] in config.admin_ids else "👤"
        name = row["full_name"] or row["username"] or "—"
        lines.append(
            fa.ADMIN_LINE.format(star=star, id=row["telegram_id"], name=name)
        )
    if super_:
        lines.append("\n⭐ = ادمین اصلی — قابل حذف از ربات نیست")
        removable = [
            a for a in admins if int(a["telegram_id"]) not in config.admin_ids
        ]
        if removable:
            lines.append("🗑 روی دکمه زیر هر ادمین برای حذف بزن.")
    text = "\n".join(lines)
    kb = admin_list_kb(admins, config.admin_ids, super_)

    if isinstance(target, CallbackQuery):
        if target.message:
            try:
                await target.message.edit_text(text, parse_mode=HTML, reply_markup=kb)
            except Exception:
                await target.message.answer(text, parse_mode=HTML, reply_markup=kb)
    else:
        await target.answer(text, parse_mode=HTML, reply_markup=kb)


@router.callback_query(F.data == "adm:admins")
async def cb_admins(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not await _cb_admin(callback, db, config):
        return
    await _render_admins_list(callback, db, config)
    await callback.answer()


@router.callback_query(F.data.startswith("adm:rm:"))
async def cb_remove_admin(
    callback: CallbackQuery, db: Database, config: Config
) -> None:
    user = callback.from_user
    if not user or not is_super_admin(user.id, config):
        await callback.answer(fa.ADMIN_SUPER_ONLY, show_alert=True)
        return
    if not callback.data:
        await callback.answer()
        return

    try:
        target_id = int(callback.data.split(":", 2)[2])
    except (IndexError, ValueError):
        await callback.answer()
        return

    if target_id in config.admin_ids:
        await callback.answer("ادمین اصلی قابل حذف نیست", show_alert=True)
        return

    ok = await db.remove_admin(target_id, config.admin_ids)
    if ok:
        await callback.answer(f"ادمین {target_id} حذف شد")
    else:
        await callback.answer("ادمین یافت نشد", show_alert=True)
        return

    await _render_admins_list(callback, db, config)


@router.callback_query(F.data == "adm:add_admin")
async def cb_add_admin(
    callback: CallbackQuery, config: Config, state: FSMContext, db: Database
) -> None:
    user = callback.from_user
    if not user or not is_super_admin(user.id, config):
        await callback.answer(fa.ADMIN_SUPER_ONLY, show_alert=True)
        return
    await state.set_state(AdminStates.add_admin_id)
    await callback.answer()
    if callback.message:
        await callback.message.answer(fa.ADMIN_ADD_ADMIN_PROMPT, parse_mode=HTML)


@router.message(AdminStates.add_admin_id, F.text)
async def admin_add_id(
    message: Message, db: Database, config: Config, state: FSMContext
) -> None:
    user = message.from_user
    if not user or not is_super_admin(user.id, config):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("⚠️ فقط آیدی عددی.", parse_mode=HTML)
        return
    new_id = int(raw)
    ok = await db.add_admin(new_id, user.id)
    await state.clear()
    if ok:
        await message.answer(
            fa.ADMIN_ADDED.format(id=new_id),
            parse_mode=HTML,
            reply_markup=admin_back_kb(),
        )
        await _render_admins_list(message, db, config)
    else:
        await message.answer(fa.ADMIN_ALREADY, parse_mode=HTML)


@router.message(Command("add_admin"))
async def cmd_add_admin(message: Message, db: Database, config: Config) -> None:
    user = message.from_user
    if not user or not is_super_admin(user.id, config):
        await message.answer(fa.ADMIN_SUPER_ONLY, parse_mode=HTML)
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer(
            "⚠️ <code>/add_admin 123456789</code>",
            parse_mode=HTML,
        )
        return
    new_id = int(parts[1].strip())
    ok = await db.add_admin(new_id, user.id)
    text = fa.ADMIN_ADDED.format(id=new_id) if ok else fa.ADMIN_ALREADY
    await message.answer(text, parse_mode=HTML, reply_markup=admin_back_kb())


@router.message(Command("del_admin"))
async def cmd_del_admin(message: Message, db: Database, config: Config) -> None:
    user = message.from_user
    if not user or not is_super_admin(user.id, config):
        await message.answer(fa.ADMIN_SUPER_ONLY, parse_mode=HTML)
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer("⚠️ <code>/del_admin 123</code>", parse_mode=HTML)
        return
    target = int(parts[1].strip())
    if target in config.admin_ids:
        await message.answer(fa.ADMIN_CANNOT_REMOVE, parse_mode=HTML)
        return
    ok = await db.remove_admin(target, config.admin_ids)
    text = fa.ADMIN_REMOVED.format(id=target) if ok else fa.ADMIN_ALREADY
    await message.answer(text, parse_mode=HTML, reply_markup=admin_back_kb())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, config: Config, state: FSMContext, db: Database) -> None:
    if not await _msg_admin(message, db, config):
        return
    if await state.get_state():
        await state.clear()
        await db.set_setting(SETTING_AWAITING_LOGO, "")
        await message.answer(fa.ADMIN_ADD_CANCEL, parse_mode=HTML, reply_markup=admin_back_kb())


# —— فیش ——


@router.callback_query(F.data.startswith("admin:approve:"))
async def approve_order(
    callback: CallbackQuery, db: Database, config: Config, bot: Bot
) -> None:
    if not await _cb_admin(callback, db, config):
        return
    if not callback.data:
        await callback.answer()
        return

    order_id = int(callback.data.rsplit(":", 1)[-1])
    detail = await db.get_order_detail(order_id)
    if not detail:
        await callback.answer("سفارش یافت نشد", show_alert=True)
        return
    # Claim first, so a double tap or the bot and panel together cannot deliver twice.
    if not await db.claim_order_status(order_id, ORDER_STATUS_PENDING_REVIEW, ORDER_STATUS_DELIVERING):
        await callback.answer("این سفارش دیگر در صف نیست", show_alert=True)
        return

    await callback.answer("در حال رمزگذاری…")
    try:
        text = await _deliver_order(db, config, bot, order_id, detail)
    except Exception:
        await db.update_order_status(order_id, ORDER_STATUS_PENDING_REVIEW)
        raise

    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.message.answer(text, parse_mode=HTML)


async def _deliver_order(db: Database, config: Config, bot: Bot, order_id: int, detail) -> str:
    items = await db.get_order_items(order_id)
    phone = detail["phone"]
    telegram_id = int(detail["user_id"])
    watermark = f"{phone} | TG:{telegram_id}"
    config.protected_dir.mkdir(parents=True, exist_ok=True)

    sent_any = False
    for idx, item in enumerate(items, start=1):
        source = Path(item["file_path"])
        if not source.exists():
            await bot.send_message(telegram_id, fa.PDF_MISSING.format(path=source.name))
            continue
        dest = config.protected_dir / f"order_{order_id}_{idx}_{source.stem}.pdf"
        try:
            protect_pdf(
                source,
                dest,
                user_password=phone,
                owner_password=config.owner_pdf_password,
                watermark_text=watermark,
            )
            await bot.send_document(
                chat_id=telegram_id,
                document=FSInputFile(dest, filename=f"{item['title']}.pdf"),
                caption=f"🎸 <b>{item['title']}</b>\n🔐 رمز: شماره موبایل شما",
                parse_mode="HTML",
            )
            sent_any = True
        finally:
            if dest.exists():
                dest.unlink(missing_ok=True)

    if sent_any:
        await bot.send_message(
            telegram_id,
            fa.USER_DELIVERED.format(
                tracking=detail["tracking_code"],
                help=fa.HELP_OPEN_PDF,
            ),
            parse_mode=HTML,
        )
        await db.update_order_status(order_id, ORDER_STATUS_DELIVERED)
        return fa.ADMIN_APPROVED.format(tracking=detail["tracking_code"])
    await db.update_order_status(order_id, ORDER_STATUS_PENDING_REVIEW)
    return "ارسال ناموفق — فایل محصول نیست."


@router.callback_query(F.data.startswith("admin:reject:"))
async def reject_order(
    callback: CallbackQuery, db: Database, config: Config, bot: Bot
) -> None:
    if not await _cb_admin(callback, db, config):
        return
    if not callback.data:
        await callback.answer()
        return

    order_id = int(callback.data.rsplit(":", 1)[-1])
    detail = await db.get_order_detail(order_id)
    if not detail:
        await callback.answer("سفارش یافت نشد", show_alert=True)
        return
    if not await db.claim_order_status(order_id, ORDER_STATUS_PENDING_REVIEW, ORDER_STATUS_REJECTED):
        await callback.answer("این سفارش دیگر در صف نیست", show_alert=True)
        return

    try:
        await bot.send_message(
            int(detail["user_id"]),
            fa.USER_REJECTED.format(tracking=detail["tracking_code"]),
            parse_mode=HTML,
        )
    except Exception:
        pass

    await callback.answer("رد شد")
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.message.answer(
            fa.ADMIN_REJECTED.format(tracking=detail["tracking_code"]),
            parse_mode=HTML,
        )
