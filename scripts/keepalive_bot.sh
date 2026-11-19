#!/bin/bash
# نگه‌داری دائمی ربات تلگرام Guitarineh روی هاست cPanel
# با Cron Job هر ۵ دقیقه اجرا شود:
#   */5 * * * * /bin/bash /home/guitarin/guitarine-bot/scripts/keepalive_bot.sh
#
# اگر ربات از قبل روشن باشد، کاری انجام نمی‌دهد.
# اگر خاموش باشد (کرش کرده یا سرور ری‌استارت شده)، دوباره روشنش می‌کند.
#
# فقط خودِ ربات را اجرا می‌کند؛ پنل وب را Passenger روی دامنه بالا می‌آورد
# (passenger_wsgi.py)، پس اینجا نباید uvicorn دوم روشن شود.

set -u

# مسیر پروژه از محل همین اسکریپت حساب می‌شود — نیازی به ویرایش دستی نیست.
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PID_FILE="$APP_DIR/bot.pid"
LOG_FILE="$APP_DIR/run.log"

cd "$APP_DIR" || exit 1

if [ -f "$PID_FILE" ]; then
    OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        # ربات از قبل روشن است — کاری لازم نیست
        exit 0
    fi
fi

# virtualenv را پیدا کن: اول .venv خود پروژه، بعد virtualenv‌ای که cPanel
# برای همین اپ ساخته (~/virtualenv/<app-dir>/<py-version>/bin/python).
VENV_PY=""
for candidate in \
    "$APP_DIR/.venv/bin/python3" \
    "$APP_DIR/.venv/bin/python" \
    "$HOME/virtualenv/$(basename "$APP_DIR")"/*/bin/python3 \
    "$HOME/virtualenv/$(basename "$APP_DIR")"/*/bin/python
do
    if [ -x "$candidate" ]; then
        VENV_PY="$candidate"
        break
    fi
done

if [ -z "$VENV_PY" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') خطا: virtualenv پیدا نشد (نه .venv نه ~/virtualenv)" >> "$LOG_FILE"
    exit 1
fi

nohup "$VENV_PY" -m bot.main >> "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') ربات با PID $NEW_PID روشن شد ($VENV_PY)" >> "$LOG_FILE"
