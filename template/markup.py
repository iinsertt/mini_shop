from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from core.database import Card, WithdrawRequest


class Markups:
    @staticmethod
    def start_menu(is_admin: bool) -> InlineKeyboardMarkup:
        keyboard: list[list[InlineKeyboardButton]] = [
            [InlineKeyboardButton(text="Добавить карточку", callback_data="user-add_product-0")],
            [InlineKeyboardButton(text="Посмотреть карточки", callback_data="user-show_products-0")],
            [InlineKeyboardButton(text="Баланс", callback_data="user-balance-0")],
        ]
        if is_admin:
            keyboard.append(
                [InlineKeyboardButton(text="🍷 Админ меню", callback_data="admin-menu-0")]
            )
        return InlineKeyboardMarkup(inline_keyboard=keyboard)


    @staticmethod
    def admin_card_result_keyboard(approved: bool) -> InlineKeyboardMarkup:
        text = "✅ Товар принят" if approved else "❌ Товар отклонён"
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=text, callback_data="admin-result-0")]
            ]
        )

    @staticmethod
    def admin_withdraw_result_keyboard() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Выплата проведена", callback_data="admin-wdresult-0")]
            ]
        )

    @staticmethod
    def cancel_reply_kb() -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отмена")]],
            resize_keyboard=True,
            one_time_keyboard=False,
        )

    @staticmethod
    def remove_reply_kb() -> ReplyKeyboardRemove:
        return ReplyKeyboardRemove()

    @staticmethod
    def user_cards_keyboard(offset: int, has_prev: bool, has_next: bool, card,
                            total_cards: int = None) -> InlineKeyboardMarkup:
        buttons = [[
            InlineKeyboardButton(text="🛒 Купить", callback_data=f"user-buy-{card.id}")
        ]]

        current_page = offset + 1

        if total_cards:
            pages_text = f"{current_page}/{total_cards}"
        else:
            pages_text = f"{current_page}"

        page_btn = InlineKeyboardButton(text=pages_text, callback_data="noop")

        left_btn = InlineKeyboardButton(
            text="◀",
            callback_data=f"user-cards_prev-{offset}" if has_prev else "noop"
        )

        right_btn = InlineKeyboardButton(
            text="▶",
            callback_data=f"user-cards_next-{offset}" if has_next else "noop"
        )

        buttons.append([left_btn, page_btn, right_btn])

        buttons.append([
            InlineKeyboardButton(text="⬅ Назад", callback_data="user-back-0")
        ])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def balance_keyboard() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Вывести", callback_data="user-withdraw-0")],
                [InlineKeyboardButton(text="⬅ Назад", callback_data="user-back-0")],
            ]
        )

    @staticmethod
    def admin_menu() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Модерация", callback_data="admin-moderation-0")],
                [InlineKeyboardButton(text="Статистика", callback_data="admin-stats-0")],
                [InlineKeyboardButton(text="Заявки на вывод", callback_data="admin-withdraws-0")],
                [InlineKeyboardButton(text="Назад", callback_data="admin-back-0")],
            ]
        )

    @staticmethod
    def admin_moderation_keyboard(offset: int, has_prev: bool, has_next: bool, card: Card) -> InlineKeyboardMarkup:
        buttons: list[list[InlineKeyboardButton]] = []

        nav_row: list[InlineKeyboardButton] = []
        if has_prev:
            nav_row.append(
                InlineKeyboardButton(
                    text="«",
                    callback_data=f"admin-mod_prev-{offset}",
                )
            )
        if has_next:
            nav_row.append(
                InlineKeyboardButton(
                    text="»",
                    callback_data=f"admin-mod_next-{offset}",
                )
            )
        if nav_row:
            buttons.append(nav_row)

        buttons.append(
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"admin-modapprove-{card.id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin-modreject-{card.id}"),
            ]
        )
        buttons.append(
            [InlineKeyboardButton(text="✏ Изменить", callback_data=f"admin-modedit-{card.id}")]
        )

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def admin_edit_fields_keyboard() -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Название")],
                [KeyboardButton(text="Описание")],
                [KeyboardButton(text="Цена")],
                [KeyboardButton(text="Фото")],
                [KeyboardButton(text="Отмена")],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

    @staticmethod
    def user_card_purchased_keyboard() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Товар куплен", callback_data="user-purchased-0")]
            ]
        )



    @staticmethod
    def admin_withdraw_keyboard(
        offset: int, has_prev: bool, has_next: bool, request: WithdrawRequest
    ) -> InlineKeyboardMarkup:
        buttons: list[list[InlineKeyboardButton]] = []

        nav_row: list[InlineKeyboardButton] = []
        if has_prev:
            nav_row.append(
                InlineKeyboardButton(
                    text="«",
                    callback_data=f"admin-wd_prev-{offset}",
                )
            )
        if has_next:
            nav_row.append(
                InlineKeyboardButton(
                    text="»",
                    callback_data=f"admin-wd_next-{offset}",
                )
            )
        if nav_row:
            buttons.append(nav_row)

        buttons.append(
            [
                InlineKeyboardButton(
                    text="Выплата проведена",
                    callback_data=f"admin-wdpaid-{request.id}",
                )
            ]
        )

        return InlineKeyboardMarkup(inline_keyboard=buttons)
