from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from bot.keyboards.callbacks import (
    MENU_CART,
    MENU_CHECKOUT,
    MENU_HELP,
    MENU_HOME,
    MENU_PRODUCTS,
)
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
from bot.services.menu_store import MenuItem, get_menu_items


def share_contact_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🎵 📱 ارسال شماره موبایل",
                    request_contact=True,
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="🎼 گیتارینه — شماره را با دکمه ارسال کنید",
    )


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def main_menu_reply_kb(items: list[MenuItem] | None = None) -> ReplyKeyboardMarkup:
    """منوی اصلی پایین صفحه — هر دکمه تمام‌عرض."""
    labels = [item["label"] for item in items] if items is not None else [
        BTN_PRODUCTS,
        BTN_CART,
        BTN_CHECKOUT,
        BTN_HELP,
    ]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=label)] for label in labels],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="🎼 گیتارینه — یک گزینه را انتخاب کنید",
    )


async def stored_main_menu_reply_kb(db) -> ReplyKeyboardMarkup:
    return main_menu_reply_kb(await get_menu_items(db))


def products_reply_kb(products: list) -> ReplyKeyboardMarkup:
    """دکمه‌های تمام‌عرض؛ جزئیات کامل در متن پیام است."""
    rows = [
        [KeyboardButton(text=product_add_btn(idx, str(p["title"])))]
        for idx, p in enumerate(products, start=1)
    ]
    rows.append([KeyboardButton(text=BTN_MENU)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="🎼 گیتارینه — یک محصول را انتخاب کنید",
    )


def cart_reply_kb(items: list) -> ReplyKeyboardMarkup:
    """همه دکمه‌ها تمام‌عرض (هر کدام یک ردیف)."""
    rows: list[list[KeyboardButton]] = []
    for idx, _ in enumerate(items, start=1):
        rows.append([KeyboardButton(text=cart_dec_btn(idx))])
        rows.append([KeyboardButton(text=cart_inc_btn(idx))])
        rows.append([KeyboardButton(text=cart_rm_btn(idx))])
    rows.append([KeyboardButton(text=BTN_CART_CLEAR)])
    rows.append([KeyboardButton(text=BTN_CHECKOUT)])
    rows.append([KeyboardButton(text=BTN_MENU)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="🎼 گیتارینه — سبد خرید",
    )


# —— inline فقط برای سازگاری با callbackهای قدیمی ——


def main_menu_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_PRODUCTS, callback_data=MENU_PRODUCTS)],
            [InlineKeyboardButton(text=BTN_CART, callback_data=MENU_CART)],
            [InlineKeyboardButton(text=BTN_CHECKOUT, callback_data=MENU_CHECKOUT)],
            [InlineKeyboardButton(text=BTN_HELP, callback_data=MENU_HELP)],
            [InlineKeyboardButton(text=BTN_MENU, callback_data=MENU_HOME)],
        ]
    )


def products_kb(products: list) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=product_add_btn(idx, str(p["title"])),
                callback_data=f"add:{p['id']}",
            )
        ]
        for idx, p in enumerate(products, start=1)
    ]
    rows.append([InlineKeyboardButton(text=BTN_MENU, callback_data=MENU_HOME)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cart_kb(items: list) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for idx, item in enumerate(items, start=1):
        pid = int(item["product_id"])
        rows.append(
            [
                InlineKeyboardButton(
                    text=cart_dec_btn(idx), callback_data=f"cart:dec:{pid}"
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=cart_inc_btn(idx), callback_data=f"cart:inc:{pid}"
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=cart_rm_btn(idx), callback_data=f"cart:rm:{pid}"
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text=BTN_CART_CLEAR, callback_data="cart:clear")]
    )
    rows.append(
        [InlineKeyboardButton(text=BTN_CHECKOUT, callback_data=MENU_CHECKOUT)]
    )
    rows.append([InlineKeyboardButton(text=BTN_MENU, callback_data=MENU_HOME)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_MENU, callback_data=MENU_HOME)],
        ]
    )
