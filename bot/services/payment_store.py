from __future__ import annotations

from bot.config import Config
from bot.db.database import Database
from bot.texts.defaults import SETTING_BANK_CARD, SETTING_BANK_CARD_HOLDER


def format_card_display(card: str) -> str:
    digits = card.replace("-", "").replace(" ", "")
    if len(digits) == 16 and digits.isdigit():
        return f"{digits[0:4]}-{digits[4:8]}-{digits[8:12]}-{digits[12:16]}"
    return digits or card


async def get_payment_settings(db: Database, config: Config) -> dict[str, str]:
    card = (await db.get_setting(SETTING_BANK_CARD, "")).strip()
    holder = (await db.get_setting(SETTING_BANK_CARD_HOLDER, "")).strip()
    if not card:
        card = config.bank_card.strip()
    if not holder:
        holder = config.bank_card_holder.strip()
    return {
        "bank_card": card,
        "bank_card_holder": holder,
        "bank_card_display": format_card_display(card),
    }


async def save_payment_settings(
    db: Database, *, bank_card: str, bank_card_holder: str
) -> None:
    await db.set_setting(SETTING_BANK_CARD, bank_card.strip())
    await db.set_setting(SETTING_BANK_CARD_HOLDER, bank_card_holder.strip())
