from typing import Union

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup

from misc import BotLogger
import core.di as di

class Utils:
    @staticmethod
    async def answer(
        t_object: Message | CallbackQuery,
        text: str,
        markup=None,
        edit_it: bool = False,
        file_id: str | None = None,
    ) -> None:
        logger = BotLogger.get_logger()

        if isinstance(t_object, CallbackQuery):
            message = t_object.message
        else:
            message = t_object

        bot = di.bot
        if bot is None:
            logger.error("Bot is not initialized")
            return

        if edit_it:
            try:
                if file_id is not None:
                    media = InputMediaPhoto(media=file_id, caption=text)
                    await bot.edit_message_media(
                        chat_id=message.chat.id,
                        message_id=message.message_id,
                        media=media,
                        reply_markup=markup,
                    )
                else:
                    await bot.edit_message_text(
                        text=text,
                        chat_id=message.chat.id,
                        message_id=message.message_id,
                        reply_markup=markup,
                    )
                return
            except Exception as e:
                logger.error(f"Failed to edit message: {e}")

        try:
            if file_id is not None:
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=file_id,
                    caption=text,
                    reply_markup=markup,
                )
            else:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=text,
                    reply_markup=markup,
                )
        except Exception as e:
            logger.error(f"Failed to send message: {e}")