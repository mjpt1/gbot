# نصب ربات Guitarineh + پنل ادمین روی cPanel

هاست: `sbot14.viphostnet.net` (IP `45.89.220.5`) — کاربر cPanel: `guitarin`
دامنه پنل: **telegram-guitarineh.ir**

سه بخش مجزا:

1. **DNS دامنه** — تا این درست نشود، cPanel اجازه اضافه‌کردن دامنه را نمی‌دهد.
2. **ربات تلگرام** (پولینگ دائمی) — با Cron Job زنده نگه داشته می‌شود.
3. **پنل وب مدیریت** — با Setup Python App روی دامنه.

---

## مرحله ۰ — DNS دامنه (اول این)

خطای زیر در cPanel یعنی دامنه هنوز nameserver ثبت‌شده ندارد:

```
Error: (XID …) Could not determine the nameserver IP addresses for
"telegram-guitarineh.ir". Please make sure that the domain is registered
with a valid domain registrar.
```

cPanel قبل از افزودن دامنه، رکورد **NS** آن را از ریشه اینترنت می‌پرسد. برای
`telegram-guitarineh.ir` هیچ NS برنمی‌گردد، پس اضافه‌کردن دامنه رد می‌شود.
این ایراد سمت **ثبت‌کننده دامنه (nic.ir)** است، نه سمت هاست.

### کاری که باید انجام شود

1. **nameserverهای هاست را بگیرید.** در cPanel، سمت راست بخش
   *General Information* → **Nameservers**. اگر آنجا نبود، از پشتیبانی
   viphostnet بپرسید. (معمولاً چیزی شبیه `ns1.<host>.net` و `ns2.<host>.net`.)
2. وارد پنل **nic.ir** شوید (`https://ir.nic.ir` → «ورود به سامانه»).
3. دامنه `telegram-guitarineh.ir` را انتخاب کنید → بخش **«سرویس‌دهنده‌های DNS»**
   (DNS Servers) → هر دو nameserver هاست را وارد و ذخیره کنید.
4. مطمئن شوید وضعیت دامنه **فعال (ok)** است، نه در انتظار تأیید مدارک.
   دامنه‌ای که هنوز تأیید مالکیت نشده، delegate نمی‌شود.
5. بین ۳۰ دقیقه تا چند ساعت صبر کنید، بعد دوباره در cPanel دامنه را اضافه کنید.

> **جایگزین:** اگر می‌خواهید DNS را Cloudflare مدیریت کند، در Cloudflare دامنه را
> اضافه کنید، یک رکورد `A` برای `telegram-guitarineh.ir` به `45.89.220.5` بسازید،
> و nameserverهای Cloudflare را در nic.ir ثبت کنید. باز هم قدم ۳ لازم است —
> nic.ir رکورد A نمی‌پذیرد، فقط NS.

**تست اینکه درست شده:**

```bash
nslookup -type=NS telegram-guitarineh.ir 8.8.8.8
```

> از داخل ایران نتیجه DNS قابل اتکا نیست (ISP جواب را عوض می‌کند).
> از سایت‌هایی مثل dnschecker.org یا از خودِ Terminal هاست تست بگیرید.

وقتی NS برگشت: cPanel → **Domains** → **Create A Domain** →
`telegram-guitarineh.ir`.

⚠️ **Document Root را روی پوشه پروژه نگذارید.** مقدار پیش‌فرض
(`/home/guitarin/telegram-guitarineh.ir`) درست است. اگر document root را
`guitarine-bot` بگذارید، پوشه `data/` (دیتابیس، فیش‌ها، PDFهای خام) از روی
اینترنت قابل دانلود می‌شود.

---

## مرحله ۱ — آپلود پروژه

اگر قبلاً آپلود کرده‌اید، فقط فایل‌های تغییرکرده را جایگزین کنید
(پایین‌تر، بخش «به‌روزرسانی»).

1. cPanel → **File Manager**
2. پوشه `guitarine-bot` کنار `public_html` (نه داخلش)
3. `gbot.zip` را آپلود و Extract کنید

فایل‌های لازم:

```
guitarine-bot/
├── bot/
├── web/
├── scripts/
├── data/                (دیتابیس، PDFها، فیش‌ها)
├── run.py
├── run_web.py
├── passenger_wsgi.py
├── requirements.txt
├── requirements-web.txt
└── .env                 (خودتان می‌سازید — مرحله ۲)
```

---

## مرحله ۲ — فایل `.env`

`guitarine-bot/.env` با این محتوا:

```env
BOT_TOKEN=<توکن ربات از BotFather>
ADMIN_IDS=23994187
BANK_CARD=6219861836023118
BANK_CARD_HOLDER=
OWNER_PDF_PASSWORD=<یک رشته تصادفی — رمز مالک PDF>

WEB_ADMIN_USER=admin
WEB_ADMIN_PASSWORD=<رمز قوی خودتان>
WEB_SECRET_KEY=<۶۴ کاراکتر تصادفی>
WEB_HOST=127.0.0.1
WEB_PORT=8080
WEB_BASE_URL=https://telegram-guitarineh.ir

TELEGRAM_PROXY=
```

`WEB_BASE_URL` دو کار می‌کند: لینکی که دستور `/admin` در ربات نشان می‌دهد،
و اینکه کوکی ورود پنل با فلگ `Secure` ست شود. حتماً `https://` باشد.

ساخت رشته تصادفی در Terminal هاست:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## مرحله ۳ — Setup Python App (پنل وب)

cPanel → **Setup Python App** → **Create Application**:

| فیلد | مقدار |
|------|-------|
| Python version | 3.11 (یا بالاترین موجود) |
| Application root | `guitarine-bot` |
| Application URL | `telegram-guitarineh.ir` |
| Application startup file | `passenger_wsgi.py` |
| Application entry point | `application` |

بعد از Create:

1. در همان صفحه، دستور «Enter to the virtual environment» را کپی کنید.
2. cPanel → **Terminal** → آن دستور را اجرا کنید، سپس:

```bash
cd ~/guitarine-bot
pip install --upgrade pip
pip install -r requirements-web.txt
```

3. برگردید به Setup Python App → **Restart**.

**تست:** `https://telegram-guitarineh.ir/healthz` باید `{"ok":true,"db":true}`
برگرداند. اگر `db` برابر `false` بود یا خطای ۵۰۰ گرفتید، لاگ را ببینید:

```bash
tail -50 ~/guitarine-bot/stderr.log
```

بعد `https://telegram-guitarineh.ir/` → صفحه ورود پنل.

> **نکته فنی:** Passenger فقط WSGI می‌فهمد و FastAPI با ASGI کار می‌کند.
> `a2wsgi` این دو را وصل می‌کند ولی **رویداد lifespan را اجرا نمی‌کند** — یعنی
> دیتابیس و آبجکت ربات هیچ‌وقت ساخته نمی‌شدند و هر درخواست ۵۰۰ می‌داد.
> `passenger_wsgi.py` حالا خودش lifespan را روی همان event loop اجرا می‌کند.
> این فایل را ساده‌سازی نکنید.

---

## مرحله ۴ — SSL

cPanel → **SSL/TLS Status** → دامنه را تیک بزنید → **Run AutoSSL**.
تا وقتی گواهی صادر نشده، کوکی `Secure` روی http ارسال نمی‌شود و ورود به پنل
کار نمی‌کند. اگر لازم شد موقتاً `WEB_BASE_URL` را `http://…` بگذارید و بعد از
صدور SSL برگردانید به `https://`.

---

## مرحله ۵ — اجرای دائمی ربات (Cron Job)

هاست اشتراکی سرویس دائمی ندارد، پس یک Cron هر ۵ دقیقه چک می‌کند ربات روشن است.

cPanel → **Cron Jobs**:

- Minute: `*/5` — بقیه فیلدها: `*`
- Command:
  ```
  /bin/bash /home/guitarin/guitarine-bot/scripts/keepalive_bot.sh
  ```

اسکریپت مسیر پروژه و virtualenv را خودش پیدا می‌کند (اول `.venv` پروژه، بعد
`~/virtualenv/guitarine-bot/…` که cPanel می‌سازد) و **فقط ربات** را اجرا می‌کند
(`python -m bot.main`) — پنل وب کار Passenger است، نباید دوبار بالا بیاید.

پکیج‌های ربات باید در همان virtualenv نصب باشند:

```bash
cd ~/guitarine-bot
pip install -r requirements.txt
```

اجرای دستی برای تست فوری:

```bash
bash ~/guitarine-bot/scripts/keepalive_bot.sh
tail -f ~/guitarine-bot/run.log
```

بعد در تلگرام به [@guitarine_bot](https://t.me/guitarine_bot) دستور `/start`
بدهید. دستور `/admin` باید لینک `https://telegram-guitarineh.ir` را بدهد.

---

## به‌روزرسانی کد

```bash
cd ~/guitarine-bot
# فایل‌های جدید را با File Manager جایگزین کنید، سپس:
kill "$(cat bot.pid)" 2>/dev/null   # ربات با Cron خودش برمی‌گردد
```
و در Setup Python App دکمه **Restart** را برای پنل بزنید.

`data/` و `.env` را هیچ‌وقت overwrite نکنید.

---

## عیب‌یابی

| مشکل | راه‌حل |
|------|--------|
| cPanel دامنه را قبول نمی‌کند (XID …) | مرحله ۰ — NS در nic.ir ثبت نشده |
| پنل ۵۰۰ می‌دهد | `tail -50 ~/guitarine-bot/stderr.log`؛ آیا `requirements-web.txt` نصب شده؟ |
| `/healthz` می‌گوید `db: false` | lifespan اجرا نشده — `passenger_wsgi.py` نسخه قدیمی است |
| بعد از ورود دوباره به صفحه login برمی‌گردد | SSL فعال نیست ولی `WEB_BASE_URL` روی `https` است |
| ربات جواب نمی‌دهد | `tail -f ~/guitarine-bot/run.log`؛ Cron فعال است؟ |
| تأیید سفارش **503** می‌دهد | فایل‌های جدید (`telegram_send.py`, `order_fulfillment.py`) را آپلود کنید؛ در Terminal: `pip install aiohttp`؛ Setup Python App → **Restart**؛ لاگ: `tail -50 ~/guitarine-bot/data/panel-error.log` |
| PDF ارسال نشد / «فایل پیدا نشد» | PDF محصول را دوباره در پنل → محصولات آپلود کنید (مسیر فایل روی سرور باید درست باشد) |
| PDF «خودش رمز دارد» | نسخه **بدون رمز** PDF را آپلود کنید |
| `pikepdf` نصب نمی‌شود | با پشتیبانی هاست هماهنگ کنید (نیاز به build tools) |
| «تلاش‌های ناموفق زیاد بود» | ۱۵ دقیقه قفل بعد از ۵ ورود اشتباه — منتظر بمانید یا اپ را Restart کنید |

---

## فایل‌های مرتبط

| فایل | کاربرد |
|------|--------|
| `passenger_wsgi.py` | ورودی Passenger برای پنل + اجرای lifespan |
| `scripts/keepalive_bot.sh` | نگه‌داری دائمی ربات با Cron |
| `run_web.py` | اجرای فقط پنل (تست لوکال) |
| `run.py` | اجرای همزمان ربات + پنل (فقط لوکال) |
