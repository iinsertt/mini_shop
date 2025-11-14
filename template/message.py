from aiogram.utils.formatting import Text


class Messages:
    @staticmethod
    def start(name: str) -> str:
        return Text(
            f"Приветствуем тебя, {name}!\n",
            "Тут ты можешь купить и продать товары.\n\n",
            "⚡ Выбери желаемое действие:",
        ).as_html()

    @staticmethod
    def ask_card_title() -> str:
        return "📝 Введите название товара:"

    @staticmethod
    def ask_card_description() -> str:
        return "✏️ Введите описание товара:"

    @staticmethod
    def ask_card_price() -> str:
        return "💰 Введите цену товара (число):"

    @staticmethod
    def invalid_price() -> str:
        return "❗ Цена должна быть числом. Попробуйте ещё раз."

    @staticmethod
    def ask_card_photo() -> str:
        return "📷 Отправьте фото товара или напишите `-`, чтобы пропустить."

    @staticmethod
    def card_sent_to_moderation() -> str:
        return "✅ Карточка отправлена на модерацию."

    @staticmethod
    def no_cards_available() -> str:
        return "Пока нет доступных карточек."

    @staticmethod
    def format_card(card_title: str, card_description: str, price: float, owner_username: str | None, show_owner: bool = False) -> str:
        owner = owner_username or "неизвестен"
        return (
            f"📦 <b>{card_title}</b>\n"
            f"{card_description}\n\n"
            f"💰 Цена: <b>{price:.2f}</b>\n"
            f"👤 Продавец: {'@'+owner if show_owner else 'Скрыто'}\n"
        )

    @staticmethod
    def balance(balance: float) -> str:
        return f"💰 Ваш баланс: <b>{balance:.2f}</b>"

    @staticmethod
    def ask_withdraw_requisites(amount: float) -> str:
        return (
            f"Вы хотите вывести <b>{amount:.2f}</b>.\n"
            "Введите реквизиты для выплаты:"
        )

    @staticmethod
    def withdraw_created() -> str:
        return "✅ Заявка на вывод отправлена. Ожидайте обработки."

    @staticmethod
    def admin_menu() -> str:
        return "🍷 Админ меню. Выберите действие:"

    @staticmethod
    def moderation_empty() -> str:
        return "На модерации пока нет карточек."

    @staticmethod
    def withdraws_empty() -> str:
        return "Нет заявок на вывод."

    @staticmethod
    def moderation_card_header() -> str:
        return "Карточка на модерации:"

    @staticmethod
    def card_updated() -> str:
        return "✅ Карточка обновлена."

    @staticmethod
    def stats_header() -> str:
        return "📊 Статистика по пользователям:"

    @staticmethod
    def stats_line(username: str | None, total: int, approved: int, rejected: int) -> str:
        uname = username or "без username"
        return (
            f"• @{uname}: всего {total}, "
            f"одобрено {approved}, отклонено {rejected}"
        )

    @staticmethod
    def withdraw_request_text(username: str | None, amount: float, requisites: str) -> str:
        uname = username or "без username"
        return (
            f"👤 Пользователь: @{uname}\n"
            f"💰 Сумма: <b>{amount:.2f}</b>\n"
            f"📄 Реквизиты: {requisites}"
        )
