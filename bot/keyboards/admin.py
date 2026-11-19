from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def receipt_actions_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✦  ✅  تایید و ارسال فایل",
                    callback_data=f"admin:approve:{order_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="◇  ❌  رد فیش",
                    callback_data=f"admin:reject:{order_id}",
                )
            ],
        ]
    )
