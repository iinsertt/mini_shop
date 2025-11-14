from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject
from aiogram.fsm.context import FSMContext
from typing import Any, Awaitable, Callable
from core.metrics import metric_errors_total


class ErrorsMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception:
            metric_errors_total.inc()
            raise


class CallbackStateMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject | CallbackQuery,
        data: dict[str, Any]
    ) -> Any:
        state: FSMContext | None = data.get("state")

        if state and isinstance(event, CallbackQuery) and event.message:
            await state.update_data(
                last_callback_data=event.data,
                last_message_id=event.message.message_id
            )

        return await handler(event, data)
