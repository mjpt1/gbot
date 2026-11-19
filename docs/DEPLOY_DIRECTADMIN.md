# راه‌اندازی پنل ادمین روی DirectAdmin

این راهنما **فقط پنل وب** را روی هاست DirectAdmin (با Python App) نصب می‌کند.  
**ربات تلگرام** باید جداگانه اجرا شود (VPS، سرور دیگر، یا همان سرور با SSH).

---

## قبل از شروع — محدودیت مهم

### دیتابیس SQLite روی یک سرور است

پروژه از فایل `data/guitarine.db` استفاده می‌کند. این فایل **فقط روی یک ماشین** قابل اشتراک واقعی نیست.

| سناریو | نتیجه |
|--------|--------|
| پنل روی DirectAdmin + ربات روی VPS **بدون همگام‌سازی** | ❌ سفارش‌ها و محصولات جدا می‌شوند |
| پنل و ربات روی **یک VPS** | ✅ بهترین حالت |
| پنل روی DA + ربات روی DA (SSH) + **یک پوشه `data/` مشترک** | ✅ ممکن |
| پنل روی DA + ربات لوکال + **کپی دستی `data/`** | ⚠️ فقط برای تست؛ عملی نیست |

**جمع‌بندی:** برای production، یا **هر دو روی یک VPS** باشند، یا پنل و ربات هر دو روی همان سرور DirectAdmin (با SSH) با یک پوشه `data/`.

تأیید/رد سفارش در پنل، PDF را از طریق **API تلگرام** برای کاربر می‌فرستد؛ پس `BOT_TOKEN` روی سرور پنل الزامی است.

---

## پیش‌نیازها

- DirectAdmin با **Setup Python App** (Passenger / LiteSpeed Python)
- Python **3.10+** (ترجیحاً 3.11)
- دسترسی **SSH** یا File Manager + Terminal
- زیردامنه، مثلاً `admin.example.com`
- SSL (Let's Encrypt از داخل DirectAdmin)

---

## مرحله ۱ — زیردامنه

1. DirectAdmin → **Account Manager** → **Subdomain Management**
2. زیردامنه بسازید: `admin`
3. Document Root معمولاً:  
   `/home/USER/domains/admin.example.com/public_html`

---

## مرحله ۲ — آپلود فایل‌ها

کل پروژه را (بدون `.venv`) آپلود کنید:

```
public_html/
├── bot/
├── web/
├── data/              ← خالی یا با guitarine.db
├── passenger_wsgi.py  ← نقطه ورود Passenger
├── run_web.py
├── requirements-web.txt
└── .env               ← خودتان می‌سازید
```

**آپلود نکنید:** `.venv/`، `__pycache__/`

---

## مرحله ۳ — Setup Python App

1. DirectAdmin → **Advanced Features** → **Setup Python App**
2. تنظیمات پیشنهادی:

| فیلد | مقدار |
|------|--------|
| Python version | 3.11 (یا بالاترین موجود) |
| App directory | `domains/admin.example.com/public_html` |
| Application URL | `/` |
| Startup file | `passenger_wsgi.py` |
| Entry point | `application` |

3. **Create** بزنید و virtualenv ساخته می‌شود.

---

## مرحله ۴ — نصب وابستگی‌ها

از SSH (مسیر virtualenv را از DirectAdmin کپی کنید):

```bash
cd ~/domains/admin.example.com/public_html
source ~/virtualenv/admin.example.com/3.11/bin/activate   # مسیر دقیق را از DA بگیرید
pip install --upgrade pip
pip install -r requirements-web.txt
```

### اگر `pikepdf` نصب نشد

روی بعضی هاست‌های اشتراکی کتابخانه‌های C++ نیست. در این حالت:

- با پشتیبانی هاست هماهنگ کنید، **یا**
- پنل را روی VPS نصب کنید (پیشنهاد می‌شود)

بدون `pikepdf`، دکمه **تأیید سفارش** خطا می‌دهد.

---

## مرحله ۵ — فایل `.env`

در ریشه پروژه (کنار `passenger_wsgi.py`):

```env
BOT_TOKEN=your-telegram-bot-token
ADMIN_IDS=23994187
BANK_CARD=6219861836023118
BANK_CARD_HOLDER=
OWNER_PDF_PASSWORD=change-me-owner-secret

WEB_ADMIN_USER=admin
WEB_ADMIN_PASSWORD=یک-رمز-قوی-و-طولانی
WEB_SECRET_KEY=یک-رشته-تصادفی-۳۲-کاراکتری-یا-بیشتر
WEB_HOST=127.0.0.1
WEB_PORT=8080
WEB_BASE_URL=https://admin.example.com
```

| متغیر | توضیح |
|--------|--------|
| `WEB_BASE_URL` | آدرس **HTTPS** عمومی پنل (بدون `/` آخر) |
| `WEB_SECRET_KEY` | برای session؛ حتماً تصادفی و محرمانه |
| `BOT_TOKEN` | برای ارسال PDF بعد از تأیید سفارش |

---

## مرحله ۶ — دسترسی پوشه `data/`

```bash
cd ~/domains/admin.example.com/public_html
mkdir -p data/products data/receipts data/branding data/protected
chmod 750 data
chmod 640 data/guitarine.db 2>/dev/null || true
```

کاربر وب‌سرور باید بتواند در `data/` بنویسد (آپلود محصول، فیش، لوگو).

---

## مرحله ۷ — SSL

1. DirectAdmin → **SSL Certificates**
2. **Let's Encrypt** برای `admin.example.com`
3. Force HTTPS را فعال کنید
4. `WEB_BASE_URL` را در `.env` به `https://...` به‌روز کنید

---

## مرحله ۸ — راه‌اندازی مجدد Python App

در **Setup Python App** → **Restart**  
یا از SSH:

```bash
mkdir -p ~/domains/admin.example.com/tmp
touch ~/domains/admin.example.com/tmp/restart.txt
```

---

## مرحله ۹ — ربات تلگرام (جداگانه)

پنل روی DirectAdmin **ربات را اجرا نمی‌کند**. ربات را یکی از این روش‌ها اجرا کنید:

### الف) همان سرور (SSH)

```bash
cd /path/to/gbot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m bot.main
```

`data/` باید **همان پوشه‌ای** باشد که پنل استفاده می‌کند.

### ب) VPS جدا

```bash
python -m bot.main
```

⚠️ فقط اگر `data/guitarine.db` را با پنل **همگام** نگه دارید (rsync هر دقیقه — توصیه نمی‌شود).

### ج) کامپیوتر خودت (تست)

```bash
python run.py
```

---

## تست

1. مرورگر: `https://admin.example.com/login`
2. ورود با `WEB_ADMIN_USER` / `WEB_ADMIN_PASSWORD`
3. بخش **سفارش‌ها** — فیش در صف را ببینید
4. **تأیید** — PDF باید در تلگرام کاربر برسد

---

## عیب‌یابی

| مشکل | راه‌حل |
|------|--------|
| 500 Internal Server Error | لاگ Passenger/Apache در DirectAdmin؛ معمولاً `.env` یا import |
| صفحه سفید | `pip install -r requirements-web.txt` را دوباره بزنید |
| ModuleNotFoundError | virtualenv درست فعال نشده یا `sys.path` |
| session کار نمی‌کند | `WEB_SECRET_KEY` ثابت بماند؛ HTTPS فعال باشد |
| تأیید سفارش خطا | `pikepdf` / `BOT_TOKEN` / فایل PDF در `data/products/` |
| سفارش در پنل نیست | ربات و پنل **دیتابیس متفاوت** دارند — یک `data/` مشترک |

### لاگ‌ها

```bash
tail -f ~/domains/admin.example.com/logs/error.log
# یا Error Log در DirectAdmin
```

### تست محلی قبل از آپلود

```bash
python run_web.py
# http://127.0.0.1:8080
```

---

## امنیت

- رمز قوی برای `WEB_ADMIN_PASSWORD`
- حتماً **HTTPS**
- `.env` را public نکنید (خارج از public_html اگر امکان دارد)
- IP محدود در `.htaccess` (اختیاری):

```apache
<RequireAll>
  Require ip YOUR.HOME.IP
  Require valid-user
</RequireAll>
```

---

## جمع‌بندی معماری پیشنهادی

```
┌─────────────────────────────┐
│  DirectAdmin (admin.domain) │
│  passenger_wsgi.py → پنل وب  │
│  data/guitarine.db          │
└──────────────┬──────────────┘
               │ همان data/
┌──────────────▼──────────────┐
│  SSH همان سرور (یا VPS)    │
│  python -m bot.main         │
│  ربات تلگرام (polling)      │
└─────────────────────────────┘
         │
         ▼
   مشتری در تلگرام
```

**ساده‌ترین راه production:** یک VPS کوچک — پنل + ربات + `python run.py` — بدون دردسر DirectAdmin.

---

## فایل‌های مرتبط

| فایل | کاربرد |
|------|--------|
| `passenger_wsgi.py` | ورود Passenger روی DirectAdmin |
| `run_web.py` | اجرای فقط پنل (تست / VPS) |
| `requirements-web.txt` | وابستگی‌های پنل |
| `web/main.py` | اپ FastAPI |
