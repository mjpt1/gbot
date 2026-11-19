from __future__ import annotations

from bot.config import Config
from bot.db.database import Database


async def is_admin(user_id: int, db: Database, config: Config) -> bool:
    if user_id in config.admin_ids:
        return True
    return await db.is_db_admin(user_id)


def is_super_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids
