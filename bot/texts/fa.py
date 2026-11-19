from __future__ import annotations

from bot.texts.formatting import GLASS_LINE, brand_banner, glass_card

WELCOME = (
    f"{brand_banner('خوش آمدید به دنیای آکورد و موسیقی')}\n\n"
    "🎼 برای شروع، شماره موبایل را با "
    "<b>دکمه پایین صفحه</b> ارسال کنید.\n\n"
    "🎵 <i>تایپ دستی شماره پذیرفته نمی‌شود.</i>"
)

PHONE_REQUIRED = (
    f"{brand_banner()}\n\n"
    "🎵 لطفاً از دکمه "
    "<b>🎵 📱 ارسال شماره موبایل</b> "
    "استفاده کنید."
)

PHONE_TYPED = (
    f"{brand_banner()}\n\n"
    "🎸 شماره را تایپ نکنید.\n"
    "فقط از دکمه "
    "<b>🎵 📱 ارسال شماره موبایل</b> "
    "پایین صفحه استفاده کنید."
)

PHONE_INVALID = (
    f"{brand_banner()}\n\n"
    "⚠️ فقط شماره موبایل <b>خودتان</b> قابل قبول است.\n"
    "لطفاً دوباره از دکمه پایین صفحه ارسال کنید."
)

PHONE_SAVED = (
    f"{brand_banner('عضویت شما تأیید شد')}\n\n"
    "✅ شماره ثبت شد: <code>{phone}</code>\n\n"
    "🎼 حالا از منوی پایین صفحه آکورد یا پکیج انتخاب کنید."
)

MAIN_MENU = (
    f"{brand_banner('منوی اصلی')}\n\n"
    + glass_card(
        "چطور سفارش بدهم؟",
        "۱. 🎸 آکورد یا پکیج را انتخاب کن\n"
        "۲. 🛒 به سبد اضافه کن\n"
        "۳. 💳 سفارش را نهایی کن\n"
        "۴. 📸 عکس فیش واریزی را بفرست",
        "🎵",
    )
)

CATALOG_HEADER = (
    f"{brand_banner('آکوردها و محصولات')}\n\n"
    "👇 از دکمه‌های پایین صفحه انتخاب کنید:"
)

CATALOG_EMPTY = "🎵 محصولی نیست."

HELP_SHORT = (
    "رمز PDF = شماره موبایل شما\n"
    "Acrobat یا Books"
)

ADMIN_SETTINGS_PANEL = (
    f"{brand_banner('تنظیمات ظاهر ربات')}\n\n"
    "🖼 لوگو · 📝 خوش‌آمد · 🎼 منو"
)

ADMIN_SET_WELCOME = (
    "📝 پیام خوش‌آمد جدید را بفرست.\n"
    "HTML مجاز است: <b>bold</b> · <i>italic</i>\n"
    "<i>/cancel لغو</i>"
)

ADMIN_SET_MENU = (
    "🎼 پیام منوی اصلی را بفرست.\n"
    "کنار دکمه‌های پایین صفحه نمایش داده می‌شود.\n"
    "<i>/cancel لغو</i>"
)

ADMIN_SET_LOGO = (
    "🖼 لوگو را به‌صورت <b>عکس</b> بفرست (نه فایل PDF).\n"
    "از گالری تلگرام بفرست، نه به‌صورت Document.\n"
    "<i>/cancel لغو</i>"
)

ADMIN_WELCOME_SAVED = "✅ پیام خوش‌آمد ذخیره شد."
ADMIN_MENU_SAVED = "✅ پیام منو ذخیره شد."
ADMIN_LOGO_SAVED = "✅ لوگو ذخیره شد."
ADMIN_LOGO_REMOVED = "✅ لوگو حذف شد."
ADMIN_LOGO_INVALID = "⚠️ فقط فایل عکس بفرست."

PRODUCT_ADDED = "🎵 «{title}» به سبد اضافه شد."

CART_EMPTY = "🛒 سبد خالی است."

CART_HEADER = "🛒 <b>گیتارینه</b> — سبد خرید"

CHECKOUT_INVOICE = (
    f"{brand_banner('فیش پرداخت')}\n\n"
    + glass_card(
        "جزئیات واریز",
        "🎼 کد پیگیری:\n<code>{tracking}</code>\n\n"
        "💰 مبلغ کل:\n<b>{amount}</b> تومان\n\n"
        "💳 شماره کارت:\n<code>{card}</code>\n"
        "{holder}\n"
        "⚠️ مبلغ را <b>دقیقاً</b> به همین عدد واریز کن.",
        "✦",
    )
    + "\n\n📸 پس از واریز، <b>عکس فیش</b> را همین‌جا ارسال کن.\n"
    "🎼 فقط تصویر — نه متن."
)

PAYMENT_NOT_CONFIGURED = (
    f"{brand_banner()}\n\n"
    "⚠️ شماره کارت پرداخت تنظیم نشده.\n"
    "لطفاً با پشتیبانی تماس بگیرید."
)

WAITING_RECEIPT = (
    f"{brand_banner()}\n\n"
    "📸 لطفاً <b>عکس فیش واریزی</b> را ارسال کنید.\n"
    "🎼 فقط تصویر — نه متن."
)

RECEIPT_RECEIVED = (
    f"{brand_banner('فیش دریافت شد')}\n\n"
    "🎵 فیش شما ثبت شد.\n"
    "✨ فایل ظرف <b>۳۰ دقیقه</b> پس از تأیید ادمین ارسال می‌شود."
)

NEED_AUTH = (
    f"{brand_banner()}\n\n"
    "🔐 ابتدا با /start شماره موبایل خود را ثبت کنید."
)

OPEN_ORDER_EXISTS = (
    f"{brand_banner('سفارش باز')}\n\n"
    "🎼 کد: <code>{tracking}</code>\n"
    "📌 وضعیت: <b>{status}</b>\n\n"
    "تا تعیین تکلیف این سفارش، سفارش جدید ثبت نمی‌شود."
)

HELP_OPEN_PDF = (
    f"{brand_banner('راهنمای باز کردن PDF')}\n\n"
    + glass_card(
        "مراحل",
        "۱. 🎵 فایل را با Adobe Acrobat یا Books باز کن\n"
        "۲. 🔐 رمز = همان شماره موبایل ثبت‌شده\n"
        "   <code>مثال: 09123456789</code>\n"
        "۳. 🎸 کپی و ویرایش فایل محدود است",
        "🎼",
    )
    + "\n\n<i>اگر باز نشد، شماره را بدون فاصله و با صفر اول وارد کن.</i>"
)

ADMIN_ONLY = "🔒 این بخش فقط برای ادمین است."

ADMIN_SUPER_ONLY = "🔒 فقط ادمین اصلی (.env) می‌تواند ادمین جدید اضافه/حذف کند."


def admin_dashboard(
    pending: int, products: int, admins: int, admin_name: str
) -> str:
    return (
        f"{brand_banner('پنل ادمین گیتارینه')}\n\n"
        f"👤 <b>{admin_name}</b>\n"
        f"{GLASS_LINE}\n\n"
        + glass_card(
            "آمار",
            f"🧾 فیش معلق: <b>{pending}</b>\n"
            f"📦 محصول فعال: <b>{products}</b>\n"
            f"👥 ادمین: <b>{admins}</b>",
            "✦",
        )
        + "\n\n🎼 از دکمه‌های پایین صفحه استفاده کن."
    )

ADMIN_ADD_TITLE = (
    f"{brand_banner('افزودن محصول')}\n\n"
    "🎸 <b>مرحله ۱ از ۳</b>\n"
    "عنوان محصول را بفرست (مثلاً: آکوردهای پاپ ایرانی)"
)

ADMIN_ADD_PRICE = (
    "💰 <b>مرحله ۲ از ۳</b>\n"
    "قیمت به <b>تومان</b> را بفرست (فقط عدد):\n"
    "<code>250000</code>"
)

ADMIN_ADD_PDF = (
    "📄 <b>مرحله ۳ از ۳</b>\n"
    "فایل PDF محصول را به‌صورت <b>Document</b> (فایل) بفرست.\n"
    "🎵 نه عکس — خود فایل PDF."
)

ADMIN_ADD_DONE = (
    f"{brand_banner('محصول ثبت شد')}\n\n"
    "✅ <b>{title}</b>\n"
    "💰 {price} تومان\n"
    "🆔 کد محصول: <code>{id}</code>"
)

ADMIN_ADD_CANCEL = "❌ عملیات لغو شد."

ADMIN_BATCH_START = (
    f"{brand_banner('افزودن چند محصول')}\n\n"
    "📦 چند فایل PDF را یکی‌یکی بفرست.\n"
    "🎵 وقتی تمام شد، «ثبت همه» را بزن.\n\n"
    "<i>/cancel برای لغو</i>"
)

ADMIN_BATCH_COLLECTED = (
    "📦 <b>{count}</b> فایل جمع شد.\n"
    "فایل دیگر بفرست یا «ثبت همه» را بزن."
)

ADMIN_BATCH_ITEM_TITLE = (
    "🎸 محصول <b>{current}/{total}</b>\n"
    "📄 فایل: <code>{file}</code>\n\n"
    "عنوان این محصول را بفرست:"
)

ADMIN_BATCH_ITEM_PRICE = (
    "💰 قیمت «<b>{title}</b>» به تومان (فقط عدد):"
)

ADMIN_BATCH_DONE = (
    f"{brand_banner('ثبت گروهی تمام شد')}\n\n"
    "✅ <b>{count}</b> محصول با موفقیت ثبت شد."
)

ADMIN_ADD_ADMIN_PROMPT = (
    f"{brand_banner('افزودن ادمین')}\n\n"
    "🆔 آیدی <b>عددی</b> تلگرام ادمین جدید را بفرست:\n"
    "<code>123456789</code>\n\n"
    "<i>با @userinfobot می‌گیری</i>"
)

ADMIN_ADDED = "✅ ادمین <code>{id}</code> اضافه شد."

ADMIN_ALREADY = "⚠️ این آیدی قبلاً ادمین است."

ADMIN_REMOVED = "✅ ادمین <code>{id}</code> حذف شد."

ADMIN_CANNOT_REMOVE = "⚠️ ادمین اصلی (.env) قابل حذف نیست."

ADMIN_LIST_HEADER = f"{brand_banner('لیست ادمین‌ها')}\n\n"

ADMIN_LINE = "{star} <code>{id}</code> — {name}"

ADMIN_PRICE_INVALID = "⚠️ قیمت نامعتبر است. فقط عدد بفرست، مثلاً: 250000"

ADMIN_PDF_INVALID = "⚠️ لطفاً فایل PDF را به‌صورت Document بفرست."

ADMIN_PRODUCTS_LIST = f"{brand_banner('لیست محصولات')}\n\n"

ADMIN_PRODUCT_LINE = (
    "{status} <code>#{id}</code> — {title}\n"
    "   💰 {price} ت · 📄 {file}"
)

ADMIN_DEL_OK = "✅ محصول <code>#{id}</code> حذف (غیرفعال) شد."

ADMIN_DEL_FAIL = "⚠️ محصول یافت نشد یا قبلاً حذف شده."

ADMIN_NO_PENDING = "🎵 فیش معلقی برای بررسی وجود ندارد."

ADMIN_RECEIPT_CAPTION = (
    f"🎸 <b>فیش جدید — گیتارینه</b>\n"
    f"{GLASS_LINE}\n\n"
    "🎼 کد: <code>{tracking}</code>\n"
    "👤 کاربر: {name}\n"
    "🆔 تلگرام: <code>{telegram_id}</code>\n"
    "📱 موبایل: <code>{phone}</code>\n"
    "💰 مبلغ: <b>{amount}</b> تومان\n\n"
    "🎵 محصولات:\n{products}"
)

ADMIN_APPROVED = "✅ سفارش <code>{tracking}</code> تأیید و ارسال شد."

ADMIN_REJECTED = "❌ سفارش <code>{tracking}</code> رد شد."

USER_REJECTED = (
    f"{brand_banner()}\n\n"
    "متأسفانه فیش <code>{tracking}</code> تأیید نشد.\n"
    "🎵 با پشتیبانی هماهنگ کن یا /start بزن."
)

USER_DELIVERED = (
    f"{brand_banner('سفارش تأیید شد')}\n\n"
    "✅ کد: <code>{tracking}</code>\n"
    "🎵 فایل‌های رمزگذاری‌شده در راه است.\n\n"
    "{help}"
)

PDF_MISSING = "⚠️ فایل محصول یافت نشد: {path}"

ORDER_NOT_FOUND = (
    f"{brand_banner()}\n\n"
    "سفارش منتظر فیش یافت نشد.\n"
    "🎼 از منو دوباره سفارش بده."
)

ORDER_STATUS_LABELS = {
    "awaiting_receipt": "در انتظار فیش",
    "pending_review": "در صف بررسی",
    "delivered": "ارسال شده",
    "rejected": "رد شده",
}


def format_toman(amount: int) -> str:
    return f"{amount:,}"


def format_products_catalog(products: list) -> str:
    from bot.texts.formatting import music_icon

    lines = [
        "🎸 <b>گیتارینه</b> · Guitarineh",
        "🎵 آکوردها و محصولات",
        "",
    ]
    for idx, p in enumerate(products, start=1):
        icon = music_icon(idx - 1)
        lines.append(f"{idx}. {icon} <b>{p['title']}</b>")
        lines.append(f"   💰 {format_toman(int(p['price']))} تومان")
    lines.append("")
    lines.append("👇 از دکمه‌های پایین صفحه محصول را انتخاب کنید.")
    return "\n".join(lines)


def format_cart(items: list, total: int) -> str:
    lines = [CART_HEADER, ""]
    for idx, item in enumerate(items, start=1):
        line_total = int(item["qty"]) * int(item["price"])
        lines.append(
            f"🎵 <b>{idx}. {item['title']}</b>\n"
            f"   × {item['qty']}  →  <b>{format_toman(line_total)}</b> ت"
        )
    lines.append("")
    lines.append(f"💰 جمع: <b>{format_toman(total)}</b> تومان")
    lines.append("👇 با دکمه‌های پایین تعداد را کم/زیاد کن.")
    return "\n".join(lines)
