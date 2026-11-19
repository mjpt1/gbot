from __future__ import annotations

from pathlib import Path

from bot.config import Config
from bot.db.database import Database
from bot.texts.defaults import (
    SETTING_AWAITING_LOGO,
    SETTING_LOGO,
    SETTING_LOGO_PATH,
    SETTING_MENU,
    SETTING_WELCOME,
)


async def save_logo_file(
    config: Config, db: Database, source: Path
) -> Path:
    config.branding_dir.mkdir(parents=True, exist_ok=True)
    dest = config.branding_dir / "logo.jpg"
    for old in config.branding_dir.glob("logo.*"):
        old.unlink(missing_ok=True)
    dest.write_bytes(source.read_bytes())
    await db.set_setting(SETTING_LOGO, "")
    await db.set_setting(SETTING_LOGO_PATH, str(dest.resolve()))
    await db.set_setting(SETTING_AWAITING_LOGO, "")
    return dest


async def remove_logo(config: Config, db: Database) -> None:
    await db.set_setting(SETTING_LOGO, "")
    await db.set_setting(SETTING_LOGO_PATH, "")
    await db.set_setting(SETTING_AWAITING_LOGO, "")
    for old in config.branding_dir.glob("logo.*"):
        old.unlink(missing_ok=True)


async def save_welcome(db: Database, text: str) -> None:
    await db.set_setting(SETTING_WELCOME, text)


async def save_menu_text(db: Database, text: str) -> None:
    await db.set_setting(SETTING_MENU, text)
