from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.db.database import Database
from bot.states import AdminStates
from bot.texts.defaults import SETTING_AWAITING_LOGO


class AwaitingLogoUpload(BaseFilter):
    async def __call__(
        self, message: Message, db: Database, state: FSMContext
    ) -> bool:
        user = message.from_user
        if not user:
            return False
        if await state.get_state() == AdminStates.settings_logo.state:
            return True
        awaiting = await db.get_setting(SETTING_AWAITING_LOGO, "")
        return awaiting == str(user.id)
