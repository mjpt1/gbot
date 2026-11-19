from __future__ import annotations

import csv
import io
import logging
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from bot.config import Config, load_config
from bot.db.database import Database
from bot.services.admin_credentials import (
    MIN_PASSWORD_LENGTH,
    describe_password_problem,
    session_fingerprint,
    set_password,
    verify_password,
)
from bot.services.branding_store import remove_logo, save_logo_file, save_menu_text, save_welcome
from bot.services.payment_store import get_payment_settings, save_payment_settings
from bot.services.menu_store import (
    ACTION_LABELS,
    ACTION_MESSAGE,
    MenuItem,
    get_menu_items,
    save_menu_items,
)
from bot.services.product_service import save_product_pdf
from bot.texts import fa
from web.auth import (
    SESSION_FINGERPRINT,
    SESSION_KEY,
    current_fingerprint,
    is_logged_in,
    redirect,
    require_login,
    url_prefix,
)

logger = logging.getLogger("guitarine.web")

WEB_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(WEB_DIR / "templates"))

STATUS_FA = {
    "awaiting_receipt": "در انتظار فیش",
    "pending_review": "در صف بررسی",
    "delivered": "ارسال شده",
    "rejected": "رد شده",
}

STATUS_CLASS = {
    "awaiting_receipt": "",
    "pending_review": "badge-warn",
    "delivered": "badge-ok",
    "rejected": "badge-danger",
}

# The panel sits on a public domain, so a wrong password must cost something.
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 15 * 60
SESSION_MAX_AGE = 8 * 60 * 60

_login_failures: dict[str, tuple[int, float]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_config()
    config.branding_dir.mkdir(parents=True, exist_ok=True)
    config.products_dir.mkdir(parents=True, exist_ok=True)
    config.receipts_dir.mkdir(parents=True, exist_ok=True)
    config.protected_dir.mkdir(parents=True, exist_ok=True)

    db = Database(config.db_path)
    await db.connect()
    await db.seed_admins_from_env(config.admin_ids)
    await db.seed_settings_defaults()
    await db.seed_products_if_empty(config.products_dir)

    app.state.config = config
    app.state.db = db
    logger.info("Web admin ready at %s", config.web_base_url)
    try:
        yield
    finally:
        await db.close()


HTTPS_ONLY = load_config().web_base_url.startswith("https://")


def create_app() -> FastAPI:
    config = load_config()
    app = FastAPI(title="Guitarineh Admin", lifespan=lifespan)
    app.add_middleware(
        SessionMiddleware,
        secret_key=config.web_secret_key,
        session_cookie="guitarine_admin",
        max_age=SESSION_MAX_AGE,
        same_site="lax",
        # On a real domain the panel is served over TLS; keep the cookie off http.
        https_only=config.web_base_url.startswith("https://"),
    )
    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
    return app


app = create_app()


@app.exception_handler(Exception)
async def on_unhandled_error(request: Request, exc: Exception):
    """Log unhandled errors where we can actually read them.

    Starlette answers a failed request with a 21-byte "Internal Server Error"
    and then re-raises so the server can log the trace — but a2wsgi stops
    iterating once the body is sent and drops that exception on the floor, and
    LiteSpeed swallows stderr too. So nothing was ever recorded. Logging here,
    inside the app, is the only place the traceback survives.
    """
    logger.exception(
        "unhandled error: %s %s (content-type=%s)",
        request.method,
        request.url.path,
        request.headers.get("content-type"),
    )
    return PlainTextResponse("Internal Server Error", status_code=500)


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    """Log the traceback and show a readable page.

    Starlette's default handler sends a bare "Internal Server Error" and then
    re-raises — but a2wsgi finishes its loop normally once the body is sent, so
    the exception is stranded in a Future and never lands anywhere we can read.
    Handling it here is the only way the trace reaches the log file.
    """
    logger.exception(
        "unhandled error: %s %s (content-type=%s, length=%s)",
        request.method,
        request.url.path,
        request.headers.get("content-type"),
        request.headers.get("content-length"),
    )
    return PlainTextResponse(
        "خطای داخلی سرور — جزئیات در data/panel-error.log ثبت شد.",
        status_code=500,
    )


def request_scheme(request: Request) -> str:
    """Scheme as seen by the *client*.

    LiteSpeed terminates TLS and hands the app a plain request, so trust the
    proxy header when it is present before falling back to the ASGI scope.
    """
    forwarded = request.headers.get("x-forwarded-proto", "")
    if forwarded:
        return forwarded.split(",")[0].strip().lower()
    return request.url.scheme


@app.middleware("http")
async def force_https(request: Request, call_next):
    """Send http:// visitors to https://.

    Both addresses work, but only one of them is used: the session cookie is
    `Secure`, so a panel served over plain http would loop back to the login
    page forever. cPanel's own "Force HTTPS Redirect" does not fire for a
    Passenger app, so the redirect lives here.
    """
    if HTTPS_ONLY and request_scheme(request) == "http":
        return RedirectResponse(
            str(request.url.replace(scheme="https")), status_code=307
        )
    return await call_next(request)


def _ctx(request: Request, **extra):
    """Template context.

    `base` is the mount prefix ("" at the domain root, "/panel" under Passenger's
    PassengerBaseURI) and every link in the templates is built as `{{ base }}/…`.
    `path` is the request path with that prefix removed, so nav highlighting
    works the same either way.
    """
    base = url_prefix(request)
    path = request.url.path
    if base and path.startswith(base):
        path = path[len(base):] or "/"
    return {"request": request, "base": base, "path": path, **extra}


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _lockout_remaining(ip: str) -> int:
    count, until = _login_failures.get(ip, (0, 0.0))
    if count < LOGIN_MAX_ATTEMPTS:
        return 0
    remaining = int(until - time.monotonic())
    if remaining <= 0:
        _login_failures.pop(ip, None)
        return 0
    return remaining


def _record_login_failure(ip: str) -> None:
    count, _ = _login_failures.get(ip, (0, 0.0))
    _login_failures[ip] = (count + 1, time.monotonic() + LOGIN_LOCKOUT_SECONDS)


@app.get("/healthz")
async def healthz(request: Request):
    """Cheap check that the app came up (used to debug the Passenger deploy)."""
    return {
        "ok": True,
        "db": hasattr(request.app.state, "db"),
        "scheme": request_scheme(request),
    }


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_logged_in(request):
        return redirect(request, "/")
    return TEMPLATES.TemplateResponse(request, "login.html", _ctx(request, error=None))


@app.post("/login")
async def login_submit(request: Request, username: str = Form(), password: str = Form()):
    config: Config = request.app.state.config
    ip = _client_ip(request)

    if remaining := _lockout_remaining(ip):
        logger.warning("login locked out ip=%s", ip)
        return TEMPLATES.TemplateResponse(
            request,
            "login.html",
            _ctx(
                request,
                error=f"تلاش‌های ناموفق زیاد بود. {remaining // 60 + 1} دقیقه دیگر امتحان کنید.",
            ),
            status_code=429,
        )

    db: Database = request.app.state.db
    user_ok = secrets.compare_digest(username, config.web_admin_user)
    pass_ok = await verify_password(db, config, password)
    if user_ok and pass_ok:
        _login_failures.pop(ip, None)
        request.session[SESSION_KEY] = True
        request.session[SESSION_FINGERPRINT] = await current_fingerprint(request)
        return redirect(request, "/")

    _record_login_failure(ip)
    logger.warning("failed login ip=%s user=%r", ip, username)
    return TEMPLATES.TemplateResponse(
        request,
        "login.html",
        _ctx(request, error="نام کاربری یا رمز عبور اشتباه است."),
        status_code=401,
    )


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return redirect(request, "/login")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    metrics = await db.get_admin_metrics()
    products = await db.count_active_products()
    users_cur = await db.conn.execute("SELECT COUNT(*) AS c FROM users")
    users_row = await users_cur.fetchone()
    orders = await db.list_all_orders(limit=8)
    activity = await db.get_order_activity(7)
    return TEMPLATES.TemplateResponse(
        request,
        "dashboard.html",
        _ctx(
            request,
            pending=metrics["pending"],
            products=products,
            users=users_row["c"] if users_row else 0,
            orders=orders,
            metrics=metrics,
            activity=activity,
            status_fa=STATUS_FA,
            status_class=STATUS_CLASS,
        ),
    )


@app.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    pending = await db.list_pending_orders()
    all_orders = await db.list_all_orders(limit=50)
    enriched = []
    for row in pending:
        order = dict(row)
        order["order_items"] = await db.get_order_items(int(row["id"]))
        receipt = await db.get_receipt(int(row["id"]))
        order["receipt"] = dict(receipt) if receipt else None
        enriched.append(order)
    return TEMPLATES.TemplateResponse(
        request,
        "orders.html",
        _ctx(
            request,
            pending_orders=enriched,
            all_orders=all_orders,
            status_fa=STATUS_FA,
            status_class=STATUS_CLASS,
            format_toman=fa.format_toman,
        ),
    )


@app.post("/orders/{order_id}/approve")
async def order_approve(request: Request, order_id: int):
    if redir := await require_login(request):
        return redir
    from bot.services.order_fulfillment import FulfillmentResult, approve_order

    db: Database = request.app.state.db
    config: Config = request.app.state.config
    try:
        result = await approve_order(db, config, order_id)
    except Exception:
        logger.exception("web approve failed order=%s", order_id)
        result = FulfillmentResult(False, "خطای داخلی — سرور فعال است.")
    return redirect(
        request, f"/orders?msg={'ok' if result.ok else 'err'}&t={result.message}"
    )


@app.post("/orders/{order_id}/reject")
async def order_reject(request: Request, order_id: int):
    if redir := await require_login(request):
        return redir
    from bot.services.order_fulfillment import FulfillmentResult, reject_order

    db: Database = request.app.state.db
    config: Config = request.app.state.config
    try:
        result = await reject_order(db, config, order_id)
    except Exception:
        logger.exception("web reject failed order=%s", order_id)
        result = FulfillmentResult(False, "خطای داخلی — سرور فعال است.")
    return redirect(
        request, f"/orders?msg={'ok' if result.ok else 'err'}&t={result.message}"
    )


@app.get("/receipts/{order_id}")
async def receipt_image(request: Request, order_id: int):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    receipt = await db.get_receipt(order_id)
    if not receipt or not receipt["local_path"]:
        raise HTTPException(404)
    path = Path(receipt["local_path"])
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path)


@app.get("/customers", response_class=HTMLResponse)
async def customers_page(request: Request):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    customers = await db.list_customers()
    return TEMPLATES.TemplateResponse(
        request,
        "customers.html",
        _ctx(
            request,
            customers=customers,
            total_spent=sum(int(c["spent"] or 0) for c in customers),
            format_toman=fa.format_toman,
        ),
    )


@app.get("/customers/export.csv")
async def customers_export(request: Request):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    customers = await db.list_customers()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "شناسه تلگرام",
            "نام",
            "نام کاربری",
            "شماره موبایل",
            "تعداد سفارش",
            "سفارش تحویل‌شده",
            "مجموع خرید (تومان)",
            "تاریخ عضویت",
            "آخرین سفارش",
        ]
    )
    for c in customers:
        writer.writerow(
            [
                c["telegram_id"],
                c["full_name"] or "",
                f"@{c['username']}" if c["username"] else "",
                # Leading "=" keeps Excel from eating the leading zero of 09…
                f'="{c["phone"]}"' if c["phone"] else "",
                c["orders_count"],
                c["delivered_count"],
                c["spent"],
                c["created_at"] or "",
                c["last_order_at"] or "",
            ]
        )

    # UTF-8 BOM so Excel opens Persian text correctly instead of mojibake.
    payload = "﻿" + buffer.getvalue()
    stamp = datetime.now().strftime("%Y-%m-%d")
    return Response(
        content=payload.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="guitarineh-customers-{stamp}.csv"'
        },
    )


@app.get("/products", response_class=HTMLResponse)
async def products_page(request: Request):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    products = await db.list_all_products()
    return TEMPLATES.TemplateResponse(
        request,
        "products.html",
        _ctx(request, products=products, format_toman=fa.format_toman),
    )


@app.post("/products")
async def product_create(
    request: Request,
    title: str = Form(),
    price: str = Form(),
    pdf: UploadFile = File(),
):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    config: Config = request.app.state.config
    title = title.strip()
    raw = price.strip().replace(",", "").replace("،", "")
    if len(title) < 2 or not raw.isdigit() or int(raw) <= 0:
        return redirect(request, "/products?err=1")
    if not pdf.filename or not pdf.filename.lower().endswith(".pdf"):
        return redirect(request, "/products?err=pdf")

    # Never build a path out of the uploaded filename: LiteSpeed starts the
    # worker without a UTF-8 locale, so `sys.getfilesystemencoding()` is ascii
    # and a Persian filename raised UnicodeEncodeError here. (Writing a
    # user-supplied name to disk is worth avoiding on its own, too.)
    tmp = config.products_dir / f"_upload_{secrets.token_hex(8)}.pdf"
    tmp.write_bytes(await pdf.read())
    try:
        # Catch a password-protected PDF here rather than when an order is
        # approved — at that point the customer has already paid.
        from bot.services.pdf_protect import check_pdf

        if problem := check_pdf(tmp):
            return redirect(request, f"/products?err={problem}")
        await save_product_pdf(db, config, title=title, price=int(raw), source=tmp)
    finally:
        tmp.unlink(missing_ok=True)
    return redirect(request, "/products?ok=1")


@app.post("/products/{product_id}/deactivate")
async def product_deactivate(request: Request, product_id: int):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    await db.deactivate_product(product_id)
    return redirect(request, "/products?deactivated=1")


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    config: Config = request.app.state.config
    brand = await db.get_branding()
    payment = await get_payment_settings(db, config)
    menu_items = await get_menu_items(db)
    logo_path = brand.get("logo_path") or ""
    has_logo = bool(logo_path and Path(logo_path).exists())
    return TEMPLATES.TemplateResponse(
        request,
        "settings.html",
        _ctx(
            request,
            brand=brand,
            payment=payment,
            has_logo=has_logo,
            admin_user=config.web_admin_user,
            min_password_length=MIN_PASSWORD_LENGTH,
            menu_items=menu_items,
            menu_actions=ACTION_LABELS,
            message_action=ACTION_MESSAGE,
        ),
    )


def _clean_menu_form(label: str, action: str, response_text: str) -> MenuItem | None:
    label = label.strip()
    action = action.strip()
    response_text = response_text.strip()
    if len(label) < 2 or action not in ACTION_LABELS:
        return None
    if action == ACTION_MESSAGE and len(response_text) < 2:
        return None
    return {
        "id": "",
        "label": label[:64],
        "action": action,
        "response_text": response_text[:4000] if action == ACTION_MESSAGE else "",
    }


@app.post("/settings/menu-items")
async def settings_menu_item_create(
    request: Request,
    label: str = Form(),
    action: str = Form(),
    response_text: str = Form(default=""),
):
    if redir := await require_login(request):
        return redir
    item = _clean_menu_form(label, action, response_text)
    if not item:
        return redirect(request, "/settings?err=menu_item")
    db: Database = request.app.state.db
    items = await get_menu_items(db)
    if len(items) >= 10 or any(existing["label"] == item["label"] for existing in items):
        return redirect(request, "/settings?err=menu_duplicate")
    item["id"] = secrets.token_hex(8)
    items.append(item)
    await save_menu_items(db, items)
    return redirect(request, "/settings?ok=menu_item")


@app.post("/settings/menu-items/{item_id}/edit")
async def settings_menu_item_edit(
    request: Request,
    item_id: str,
    label: str = Form(),
    action: str = Form(),
    response_text: str = Form(default=""),
):
    if redir := await require_login(request):
        return redir
    replacement = _clean_menu_form(label, action, response_text)
    if not replacement:
        return redirect(request, "/settings?err=menu_item")
    db: Database = request.app.state.db
    items = await get_menu_items(db)
    if any(
        item["id"] != item_id and item["label"] == replacement["label"]
        for item in items
    ):
        return redirect(request, "/settings?err=menu_duplicate")
    for index, item in enumerate(items):
        if item["id"] == item_id:
            replacement["id"] = item_id
            items[index] = replacement
            await save_menu_items(db, items)
            return redirect(request, "/settings?ok=menu_item")
    return redirect(request, "/settings?err=menu_missing")


@app.post("/settings/menu-items/{item_id}/delete")
async def settings_menu_item_delete(request: Request, item_id: str):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    items = await get_menu_items(db)
    if len(items) <= 1:
        return redirect(request, "/settings?err=menu_last")
    remaining = [item for item in items if item["id"] != item_id]
    if len(remaining) == len(items):
        return redirect(request, "/settings?err=menu_missing")
    await save_menu_items(db, remaining)
    return redirect(request, "/settings?ok=menu_deleted")


@app.post("/settings/menu-items/{item_id}/move")
async def settings_menu_item_move(
    request: Request,
    item_id: str,
    direction: str = Form(),
):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    items = await get_menu_items(db)
    index = next((i for i, item in enumerate(items) if item["id"] == item_id), -1)
    target = index - 1 if direction == "up" else index + 1
    if index >= 0 and 0 <= target < len(items):
        items[index], items[target] = items[target], items[index]
        await save_menu_items(db, items)
    return redirect(request, "/settings?ok=menu_order")


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    return TEMPLATES.TemplateResponse(
        request,
        "analytics.html",
        _ctx(
            request,
            metrics=await db.get_admin_metrics(),
            activity=await db.get_order_activity(14),
        ),
    )


@app.post("/settings/welcome")
async def settings_welcome(request: Request, welcome_text: str = Form()):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    text = welcome_text.strip()
    if len(text) >= 3:
        await save_welcome(db, text)
    return redirect(request, "/settings?ok=welcome")


@app.post("/settings/menu")
async def settings_menu(request: Request, menu_text: str = Form()):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    text = menu_text.strip()
    if len(text) >= 2:
        await save_menu_text(db, text)
    return redirect(request, "/settings?ok=menu")


@app.post("/settings/logo")
async def settings_logo(request: Request, logo: UploadFile = File()):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    config: Config = request.app.state.config
    if not logo.content_type or not logo.content_type.startswith("image/"):
        return redirect(request, "/settings?err=logo")
    tmp = config.branding_dir / "_upload_logo"
    tmp.write_bytes(await logo.read())
    try:
        await save_logo_file(config, db, tmp)
    finally:
        tmp.unlink(missing_ok=True)
    return redirect(request, "/settings?ok=logo")


@app.post("/settings/payment")
async def settings_payment(
    request: Request,
    bank_card: str = Form(),
    bank_card_holder: str = Form(default=""),
):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    card = bank_card.strip().replace("-", "").replace(" ", "")
    if len(card) < 16 or not card.isdigit():
        return redirect(request, "/settings?err=payment")
    await save_payment_settings(
        db, bank_card=card, bank_card_holder=bank_card_holder.strip()
    )
    return redirect(request, "/settings?ok=payment")


@app.post("/settings/logo/remove")
async def settings_logo_remove(request: Request):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    config: Config = request.app.state.config
    await remove_logo(config, db)
    return redirect(request, "/settings?ok=logo_removed")


@app.post("/settings/password")
async def settings_password(
    request: Request,
    current_password: str = Form(),
    new_password: str = Form(),
    confirm_password: str = Form(),
):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    config: Config = request.app.state.config

    if not await verify_password(db, config, current_password):
        logger.warning("password change rejected ip=%s", _client_ip(request))
        return redirect(request, "/settings?err=pw_current")

    if problem := describe_password_problem(new_password, confirm_password):
        key = "pw_short" if "کاراکتر" in problem else "pw_mismatch"
        return redirect(request, f"/settings?err={key}")

    new_hash = await set_password(db, new_password)
    # Keep this device signed in; the new fingerprint drops every other session.
    request.session[SESSION_FINGERPRINT] = session_fingerprint(new_hash)
    logger.info("admin password changed ip=%s", _client_ip(request))
    return redirect(request, "/settings?ok=password")


@app.get("/settings/logo/preview")
async def settings_logo_preview(request: Request):
    if redir := await require_login(request):
        return redir
    db: Database = request.app.state.db
    brand = await db.get_branding()
    path = brand.get("logo_path") or ""
    if not path or not Path(path).exists():
        raise HTTPException(404)
    return FileResponse(path)
