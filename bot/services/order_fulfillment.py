from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from bot.config import Config
from bot.db.database import Database
from bot.db.models import (
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_DELIVERING,
    ORDER_STATUS_PENDING_REVIEW,
    ORDER_STATUS_REJECTED,
)
from bot.services.pdf_protect import SourcePdfLocked, protect_pdf
from bot.services import telegram_send
from bot.texts import fa

logger = logging.getLogger("guitarine.fulfillment")


@dataclass(slots=True)
class FulfillmentResult:
    ok: bool
    message: str
    tracking_code: str = ""


async def approve_order(
    db: Database, config: Config, order_id: int
) -> FulfillmentResult:
    # Claim first, so a double tap or the bot and panel together cannot deliver twice.
    if not await db.claim_order_status(order_id, ORDER_STATUS_PENDING_REVIEW, ORDER_STATUS_DELIVERING):
        if not await db.get_order_detail(order_id):
            return FulfillmentResult(False, "سفارش یافت نشد.")
        return FulfillmentResult(False, "این سفارش دیگر در صف نیست.")
    result = await _deliver(db, config, order_id)
    if not result.ok:
        await db.update_order_status(order_id, ORDER_STATUS_PENDING_REVIEW)
    return result


async def _deliver(
    db: Database, config: Config, order_id: int
) -> FulfillmentResult:
    try:
        detail = await db.get_order_detail(order_id)
        if not detail:
            return FulfillmentResult(False, "سفارش یافت نشد.")

        items = await db.get_order_items(order_id)
        phone = detail["phone"]
        telegram_id = int(detail["user_id"])
        watermark = f"{phone} | TG:{telegram_id}"
        config.protected_dir.mkdir(parents=True, exist_ok=True)

        sent_any = False
        locked: list[str] = []
        missing: list[str] = []
        for idx, item in enumerate(items, start=1):
            source = Path(item["file_path"])
            if not source.exists():
                missing.append(item["title"])
                try:
                    await telegram_send.send_message(
                        config,
                        telegram_id,
                        fa.PDF_MISSING.format(path=source.name),
                    )
                except Exception:
                    logger.exception(
                        "notify missing pdf failed order=%s item=%s", order_id, item["title"]
                    )
                continue
            dest = config.protected_dir / f"order_{order_id}_{idx}_{source.stem}.pdf"
            try:
                await asyncio.to_thread(
                    protect_pdf,
                    source,
                    dest,
                    user_password=phone,
                    owner_password=config.owner_pdf_password,
                    watermark_text=watermark,
                )
                await telegram_send.send_document(
                    config,
                    telegram_id,
                    dest,
                    filename=f"{item['title']}.pdf",
                    caption=f"🎸 <b>{item['title']}</b>\n🔐 رمز: شماره موبایل شما",
                )
                sent_any = True
            except SourcePdfLocked:
                locked.append(item["title"])
                logger.error(
                    "product pdf is password-protected order=%s item=%s file=%s",
                    order_id,
                    item["title"],
                    source.name,
                )
            except Exception:
                logger.exception(
                    "deliver item failed order=%s item=%s", order_id, item["title"]
                )
            finally:
                if dest.exists():
                    dest.unlink(missing_ok=True)

        tracking = detail["tracking_code"]
        if sent_any:
            await telegram_send.send_message(
                config,
                telegram_id,
                fa.USER_DELIVERED.format(
                    tracking=tracking,
                    help=fa.HELP_OPEN_PDF,
                ),
            )
            await db.update_order_status(order_id, ORDER_STATUS_DELIVERED)
            return FulfillmentResult(True, f"سفارش {tracking} تأیید و ارسال شد.", tracking)

        if locked:
            return FulfillmentResult(
                False,
                "ارسال نشد — فایل «"
                + "، ".join(locked)
                + "» خودش رمز دارد و قابل پردازش نیست. نسخه بدون رمز را در بخش محصولات آپلود کنید.",
                tracking,
            )
        if missing:
            return FulfillmentResult(
                False,
                "ارسال نشد — فایل «" + "، ".join(missing) + "» روی سرور پیدا نشد.",
                tracking,
            )
        return FulfillmentResult(False, "ارسال ناموفق — جزئیات در لاگ ثبت شد.", tracking)
    except Exception:
        logger.exception("approve_order crashed order=%s", order_id)
        return FulfillmentResult(False, "خطای داخلی در تأیید سفارش.")


async def reject_order(
    db: Database, config: Config, order_id: int
) -> FulfillmentResult:
    detail = await db.get_order_detail(order_id)
    if not detail:
        return FulfillmentResult(False, "سفارش یافت نشد.")
    if not await db.claim_order_status(order_id, ORDER_STATUS_PENDING_REVIEW, ORDER_STATUS_REJECTED):
        return FulfillmentResult(False, "این سفارش دیگر در صف نیست.")

    tracking = detail["tracking_code"]
    try:
        await telegram_send.send_message(
            config,
            int(detail["user_id"]),
            fa.USER_REJECTED.format(tracking=tracking),
        )
    except Exception:
        logger.exception("reject notify failed order=%s", order_id)
    return FulfillmentResult(True, f"سفارش {tracking} رد شد.", tracking)
