from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_main_kb(pending_count: int = 0) -> InlineKeyboardMarkup:
    badge = f" ({pending_count})" if pending_count else ""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🧾  فیش‌های معلق{badge}",
                    callback_data="adm:pending",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="➕  افزودن محصول",
                    callback_data="adm:add_one",
                ),
                InlineKeyboardButton(
                    text="📦  افزودن چندتایی",
                    callback_data="adm:add_batch",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📋  لیست محصولات",
                    callback_data="adm:products",
                ),
                InlineKeyboardButton(
                    text="👥  ادمین‌ها",
                    callback_data="adm:admins",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚙️  تنظیمات",
                    callback_data="adm:settings",
                ),
                InlineKeyboardButton(
                    text="🔄  بروزرسانی",
                    callback_data="adm:home",
                ),
            ],
        ]
    )


def admin_after_product_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕  محصول بعدی",
                    callback_data="adm:add_one",
                ),
                InlineKeyboardButton(
                    text="🎼  پنل ادمین",
                    callback_data="adm:home",
                ),
            ],
        ]
    )


def admin_batch_collect_kb(count: int) -> InlineKeyboardMarkup:
    label = f"✅  ثبت {count} فایل" if count else "✅  (هنوز فایلی نیست)"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data="adm:batch_done",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌  لغو",
                    callback_data="adm:batch_cancel",
                ),
            ],
        ]
    )


def admin_list_kb(
    admins: list, env_admin_ids: frozenset[int], is_super: bool
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if is_super:
        for row in admins:
            tid = int(row["telegram_id"])
            if tid in env_admin_ids:
                continue
            label = row["full_name"] or row["username"] or str(tid)
            if len(label) > 16:
                label = label[:14] + "…"
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"🗑  حذف {label}",
                        callback_data=f"adm:rm:{tid}",
                    )
                ]
            )
        rows.append(
            [
                InlineKeyboardButton(
                    text="➕  افزودن ادمین",
                    callback_data="adm:add_admin",
                ),
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="🎼  بازگشت", callback_data="adm:home")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝  پیام خوش‌آمد",
                    callback_data="adm:set_welcome",
                ),
                InlineKeyboardButton(
                    text="🎼  پیام منو",
                    callback_data="adm:set_menu",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🖼  تغییر لوگو",
                    callback_data="adm:set_logo",
                ),
                InlineKeyboardButton(
                    text="🗑  حذف لوگو",
                    callback_data="adm:rm_logo",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👁  پیش‌نمایش",
                    callback_data="adm:preview_brand",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎼  بازگشت",
                    callback_data="adm:home",
                ),
            ],
        ]
    )


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎼  پنل ادمین", callback_data="adm:home")],
        ]
    )
