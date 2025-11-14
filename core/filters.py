from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

import core.di as di
from core.database import User


class CallbackScopeFilter(BaseFilter):

    def __init__(self, scope: str) -> None:
        self.scope = scope

    async def __call__(self, callback: CallbackQuery) -> bool:
        if not callback.data:
            return False
        parts = callback.data.split("-", 2)
        return len(parts) == 3 and parts[0] == self.scope


class AdminFilter(BaseFilter):

    async def __call__(self, obj: Message | CallbackQuery) -> bool:
        if obj.from_user is None:
            return False
        if di.repo is None:
            return False
        user = await di.repo.get_user_by_telegram_id(obj.from_user.id)
        return bool(user and user.is_admin)
