from __future__ import annotations

# منوی اصلی — هر دکمه تمام‌عرض (یک ردیف)
BTN_PRODUCTS = "🎸 آکوردها و محصولات"
BTN_CART = "🛒 سبد خرید"
BTN_CHECKOUT = "💳 ثبت سفارش"
BTN_HELP = "🎵 راهنما"
BTN_MENU = "🎼 بازگشت به منو"
BTN_CART_CLEAR = "🗑 پاک کردن کل سبد"

MENU_BUTTONS = frozenset({BTN_PRODUCTS, BTN_CART, BTN_CHECKOUT, BTN_HELP, BTN_MENU})


def product_add_btn(index: int, title: str = "") -> str:
    """دکمه تمام‌عرض؛ عنوان کوتاه برای جا شدن روی موبایل."""
    if not title:
        return f"➕ افزودن {index}"
    short = " ".join(title.split())
    if len(short) > 28:
        short = short[:27] + "…"
    return f"➕ {index}. {short}"


def cart_dec_btn(index: int) -> str:
    return f"➖ کم کردن تعداد · {index}"


def cart_inc_btn(index: int) -> str:
    return f"➕ زیاد کردن تعداد · {index}"


def cart_rm_btn(index: int) -> str:
    return f"🗑 حذف از سبد · {index}"
