from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot.db.database import Database


class IsNotRegistered(BaseFilter):
    async def __call__(self, message: Message, db: Database) -> bool:
        user = message.from_user
        if not user:
            return False
        row = await db.get_user(user.id)
        return row is None or not row["phone"]
