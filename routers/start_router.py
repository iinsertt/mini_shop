from datetime import datetime, timezone

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

import core.di as di
from core.database import User
from core.utils import Utils
from misc import BotLogger
from template.markup import Markups
from template.message import Messages
from core.metrics import users_total

start_router = Router(name="start_router")
logger = BotLogger.get_logger(__name__)


@start_router.message(F.chat.type == "private", F.text == "/start")
async def start_handler(message: types.Message, state: FSMContext) -> None:
    if di.repo is None:
        logger.error("Repository is not initialized")
        return

    user = await di.repo.get_user_by_telegram_id(message.from_user.id)

    if not user:
        new_user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await di.repo.upsert(new_user)
        user = new_user
        logger.info("Создан новый пользователь %s", user.telegram_id)

        async with di.db.async_sessionmaker() as session:
            result = await session.execute(User.count_query())
            total_users = result.scalar_one()
            users_total.set(total_users)

    await Utils.answer(
        t_object=message,
        text=Messages.start(message.from_user.first_name),
        markup=Markups.start_menu(is_admin=user.is_admin),
    )
