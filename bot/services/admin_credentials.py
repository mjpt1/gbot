"""Admin panel password.

The password used to live only in `.env`, which meant changing it required
editing a file on the server. It is now stored **hashed** in `bot_settings`
and seeded from `WEB_ADMIN_PASSWORD` the first time the panel runs, so the
admin can change it from the panel itself. `.env` stays as the bootstrap
value and as the recovery path (delete the setting row and it reseeds).
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

from bot.config import Config
from bot.db.database import Database

SETTING_PASSWORD_HASH = "web_admin_password_hash"

_ALGO = "sha256"
_ITERATIONS = 240_000
_PREFIX = f"pbkdf2_{_ALGO}"

MIN_PASSWORD_LENGTH = 8


def _derive(password: str, salt: bytes, iterations: int) -> str:
    digest = hashlib.pbkdf2_hmac(_ALGO, password.encode("utf-8"), salt, iterations)
    return f"{_PREFIX}${iterations}${salt.hex()}${digest.hex()}"


def make_hash(password: str) -> str:
    return _derive(password, secrets.token_bytes(16), _ITERATIONS)


def check_hash(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if len(parts) != 4 or parts[0] != _PREFIX:
        return False
    try:
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
    except ValueError:
        return False
    return hmac.compare_digest(_derive(password, salt, iterations), stored)


async def get_password_hash(db: Database, config: Config) -> str:
    """Current hash, seeded from `.env` on first use."""
    stored = await db.get_setting(SETTING_PASSWORD_HASH)
    if stored:
        return stored
    stored = make_hash(config.web_admin_password)
    await db.set_setting(SETTING_PASSWORD_HASH, stored)
    return stored


async def verify_password(db: Database, config: Config, password: str) -> bool:
    return check_hash(password, await get_password_hash(db, config))


async def set_password(db: Database, password: str) -> str:
    stored = make_hash(password)
    await db.set_setting(SETTING_PASSWORD_HASH, stored)
    return stored


def session_fingerprint(password_hash: str) -> str:
    """Tag kept in the session cookie.

    It changes with the password, so changing the password signs every other
    device out without needing server-side session storage.
    """
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:16]


def describe_password_problem(new: str, confirm: str) -> str | None:
    """Validation shared by the route and its tests; None means OK."""
    if len(new) < MIN_PASSWORD_LENGTH:
        return f"رمز جدید باید حداقل {MIN_PASSWORD_LENGTH} کاراکتر باشد."
    if new != confirm:
        return "رمز جدید و تکرار آن یکسان نیستند."
    if new.strip() != new:
        return "رمز نباید با فاصله شروع یا تمام شود."
    return None
