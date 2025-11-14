from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from misc import BotLogger

logger = BotLogger.get_logger("Notifier")


async def safe_notify(bot, user_id: int, text: str, **kwargs) -> None:
    try:
        await bot.send_message(chat_id=user_id, text=text, **kwargs)
    except TelegramForbiddenError:
        logger.warning(f"User {user_id} blocked the bot — notification skipped.")
    except TelegramBadRequest as e:
        logger.error(f"BadRequest while sending notification to {user_id}: {e}")
    except Exception as e:
        logger.exception(f"Unexpected notification error for user {user_id}: {e}")
