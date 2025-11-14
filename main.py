import asyncio
from aiogram import Dispatcher
from aiogram.types import BotCommand

from core.metrics import start_metrics_server
from core.metrics_loader import preload_metrics
from core.middleware import CallbackStateMiddleware
from misc import BotLogger
from routers import router_head as main_router
import core.di as di

logger = BotLogger.get_logger("bot")


async def bot_runner():
    await di.init()
    logger.info("Глобальные сервисы инициализированы")

    start_metrics_server()
    await preload_metrics()

    dispatcher = Dispatcher()

    main_router.callback_query.middleware(CallbackStateMiddleware())

    if not getattr(main_router, "_is_attached", False):
        dispatcher.include_router(main_router)
        main_router._is_attached = True

    if di.bot:
        await di.bot.set_my_commands(
            [BotCommand(command="start", description="Главное меню")]
        )

    await dispatcher.start_polling(di.bot)


def main():
    try:
        asyncio.run(bot_runner())
    except Exception:
        logger.exception("Ошибка при запуске бота")


if __name__ == "__main__":
    main()
