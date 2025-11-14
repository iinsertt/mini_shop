from datetime import datetime, timezone
from typing import Optional
from core.notifier import safe_notify
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InputMediaPhoto
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from core.database import Card, CardStatus, User, Purchase, WithdrawRequest, WithdrawStatus
import core.di as di
from core.states import AddCardStates, WithdrawStates
from core.utils import Utils
from misc import BotLogger
from template.markup import Markups
from template.message import Messages
from core.metrics import purchases_total, withdraw_requests_total, cards_total

user_router = Router(name="user_router")
logger = BotLogger.get_logger(__name__)


async def _get_total_approved():
    async with di.db.async_sessionmaker() as session:
        result = await session.execute(
            select(func.count(Card.id)).where(Card.status == CardStatus.approved)
        )
        return result.scalar() or 0


async def _go_main_menu_from_callback(callback: CallbackQuery) -> None:
    if di.repo is None:
        return
    user = await di.repo.get_user_by_telegram_id(callback.from_user.id)
    is_admin = bool(user and user.is_admin)
    await Utils.answer(
        callback,
        Messages.start(callback.from_user.first_name),
        markup=Markups.start_menu(is_admin=is_admin),
        edit_it=False,
    )


async def _go_main_menu_from_message(message: Message) -> None:
    if di.repo is None:
        return
    user = await di.repo.get_user_by_telegram_id(message.from_user.id)
    is_admin = bool(user and user.is_admin)
    await Utils.answer(
        message,
        Messages.start(message.from_user.first_name),
        markup=Markups.start_menu(is_admin=is_admin),
        edit_it=False,
    )


@user_router.callback_query(F.data == "user-back-0")
async def user_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _go_main_menu_from_callback(callback)


@user_router.callback_query(F.data == "user-add_product-0")
async def add_card_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddCardStates.waiting_title)
    await Utils.answer(callback, Messages.ask_card_title(), markup=Markups.cancel_reply_kb())
    logger.info("Пользователь %s начал добавление карточки", callback.from_user.id)


@user_router.message(AddCardStates.waiting_title, F.text)
async def add_card_title(message: Message, state: FSMContext) -> None:
    if message.text == "Отмена":
        await state.clear()
        await Utils.answer(message, "Добавление карточки отменено.")
        return await _go_main_menu_from_message(message)

    await state.update_data(title=message.text.strip())
    await state.set_state(AddCardStates.waiting_description)
    await Utils.answer(message, Messages.ask_card_description(), markup=Markups.cancel_reply_kb())


@user_router.message(AddCardStates.waiting_description, F.text)
async def add_card_description(message: Message, state: FSMContext) -> None:
    if message.text == "Отмена":
        await state.clear()
        await Utils.answer(message, "Добавление карточки отменено.")
        return await _go_main_menu_from_message(message)

    await state.update_data(description=message.text.strip())
    await state.set_state(AddCardStates.waiting_price)
    await Utils.answer(message, Messages.ask_card_price(), markup=Markups.cancel_reply_kb())


@user_router.message(AddCardStates.waiting_price)
async def add_card_price(message: Message, state: FSMContext) -> None:
    if message.text == "Отмена":
        await state.clear()
        await Utils.answer(message, "Добавление карточки отменено.")
        return await _go_main_menu_from_message(message)

    try:
        price = float(message.text.replace(",", "."))
    except:
        return await Utils.answer(message, Messages.invalid_price(), markup=Markups.cancel_reply_kb())

    await state.update_data(price=price)
    await state.set_state(AddCardStates.waiting_photo)
    await Utils.answer(message, Messages.ask_card_photo(), markup=Markups.cancel_reply_kb())


@user_router.message(AddCardStates.waiting_photo)
async def add_card_photo(message: Message, state: FSMContext) -> None:
    if message.text == "Отмена":
        await state.clear()
        await Utils.answer(message, "Добавление карточки отменено.")
        return await _go_main_menu_from_message(message)

    data = await state.get_data()
    title = data["title"]
    description = data["description"]
    price = data["price"]

    photo_file_id = message.photo[-1].file_id if message.photo else None

    if di.repo is None:
        return

    user = await di.repo.get_user_by_telegram_id(message.from_user.id)
    if not user:
        user = await di.repo.upsert(
            User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )

    card = Card(
        owner_id=user.id,
        title=title,
        description=description,
        price=price,
        photo_file_id=photo_file_id,
        status=CardStatus.pending,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await di.repo.upsert(card)

    cards_total.inc()

    await state.clear()
    await Utils.answer(message, Messages.card_sent_to_moderation(), markup=Markups.remove_reply_kb())
    await _go_main_menu_from_message(message)


async def _fetch_approved_card_with_neighbors(offset: int):
    if di.db is None:
        return None, False, False
    async with di.db.async_sessionmaker() as session:
        result = await session.execute(
            select(Card)
            .options(selectinload(Card.owner))
            .where(Card.status == CardStatus.approved)
            .order_by(Card.id)
            .offset(offset)
            .limit(2)
        )
        cards = result.scalars().all()
        if not cards:
            return None, False, False
        return cards[0], offset > 0, len(cards) > 1


@user_router.callback_query(F.data == "user-show_products-0")
async def show_cards_start(callback: CallbackQuery, state: FSMContext) -> None:
    await _show_card(callback, offset=0, edit=False)


@user_router.callback_query(F.data.startswith("user-cards_prev-"))
async def show_cards_prev(callback: CallbackQuery, state: FSMContext) -> None:
    offset = int(callback.data.split("-")[2])
    await _show_card(callback, offset=max(offset - 1, 0), edit=True)


@user_router.callback_query(F.data.startswith("user-cards_next-"))
async def show_cards_next(callback: CallbackQuery, state: FSMContext) -> None:
    offset = int(callback.data.split("-")[2])
    await _show_card(callback, offset=max(offset + 1, 0), edit=True)


async def _show_card(cb_or_msg, offset: int, edit: bool):
    card, has_prev, has_next = await _fetch_approved_card_with_neighbors(offset)
    if not card:
        return await Utils.answer(cb_or_msg, Messages.no_cards_available())

    total_cards = await _get_total_approved()
    kb = Markups.user_cards_keyboard(offset, has_prev, has_next, card, total_cards)
    text = Messages.format_card(
        card_title=card.title,
        card_description=card.description,
        price=card.price,
        owner_username=card.owner.username if card.owner else None,
        show_owner=(card.owner.telegram_id == cb_or_msg.from_user.id),
    )

    if isinstance(cb_or_msg, CallbackQuery):
        if card.photo_file_id:
            if edit:
                try:
                    await cb_or_msg.message.edit_media(
                        media=InputMediaPhoto(media=card.photo_file_id, caption=text),
                        reply_markup=kb,
                    )
                except:
                    await cb_or_msg.message.answer_photo(card.photo_file_id, caption=text, reply_markup=kb)
            else:
                await cb_or_msg.message.answer_photo(card.photo_file_id, caption=text, reply_markup=kb)
        else:
            await Utils.answer(cb_or_msg, text, markup=kb, edit_it=edit)
    else:
        if card.photo_file_id:
            await cb_or_msg.answer_photo(photo=card.photo_file_id, caption=text, reply_markup=kb)
        else:
            await Utils.answer(cb_or_msg, text, markup=kb)


@user_router.callback_query(F.data.startswith("user-buy-"))
async def buy_card(callback: CallbackQuery, state: FSMContext) -> None:
    card_id = int(callback.data.split("-")[2])

    async with di.db.async_sessionmaker() as session:
        result = await session.execute(
            select(Card).options(selectinload(Card.owner)).where(Card.id == card_id)
        )
        card = result.scalars().first()

        if not card or card.status != CardStatus.approved:
            await callback.answer("Карточка недоступна.")
            return
        buyer_result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        buyer = buyer_result.scalars().first()

        if not buyer:
            return await Utils.answer(callback, "Ошибка: пользователь не найден.")

        seller = card.owner
        if not seller:
            await Utils.answer(callback, "Ошибка: у карточки нет владельца.")
            return
        if seller.id == buyer.id:
            await callback.answer("❌ Вы не можете купить свою карточку.", show_alert=True)
            return
        if (buyer.balance or 0.0) < card.price:
            await callback.answer("❌ Недостаточно средств.", show_alert=True)
            return
        buyer.balance -= card.price
        seller.balance = (seller.balance or 0.0) + card.price

        purchase = Purchase(
            buyer_id=buyer.id,
            card_id=card.id,
            amount=card.price,
            created_at=datetime.now(timezone.utc),
        )
        session.add(purchase)

        card.status = CardStatus.sold
        card.updated_at = datetime.now(timezone.utc)

        await session.commit()

        purchases_total.inc()
        cards_total.dec()

        await safe_notify(
            callback.message.bot,
            seller.telegram_id,
            f"💸 Ваш товар «{card.title}» куплен! На баланс начислено {card.price:.2f}."
        )

    try:
        await callback.message.edit_reply_markup(
            reply_markup=Markups.user_card_purchased_keyboard()
        )
    except Exception as e:
        logger.error(f"Failed to edit message markup: {e}")
        await callback.message.answer(
            "🟢 Покупка успешно оформлена!",
            reply_markup=Markups.user_card_purchased_keyboard()
        )

    await callback.answer("🟢 Покупка успешно оформлена!", show_alert=True)
    await _go_main_menu_from_callback(callback)


@user_router.callback_query(F.data == "user-balance-0")
async def show_balance(callback: CallbackQuery, state: FSMContext) -> None:
    if di.repo is None:
        return
    user = await di.repo.get_user_by_telegram_id(callback.from_user.id)
    balance = user.balance if user else 0.0
    await Utils.answer(
        callback,
        Messages.balance(balance),
        markup=Markups.balance_keyboard(),
        edit_it=True,
    )


@user_router.callback_query(F.data == "user-withdraw-0")
async def withdraw_start(callback: CallbackQuery, state: FSMContext) -> None:
    if di.repo is None:
        return

    user = await di.repo.get_user_by_telegram_id(callback.from_user.id)
    if not user or not user.balance:
        await callback.answer("У вас нет средств.", show_alert=True)
        return

    await state.set_state(WithdrawStates.waiting_requisites)
    await state.update_data(amount=user.balance)

    await Utils.answer(
        callback,
        Messages.ask_withdraw_requisites(user.balance),
        markup=Markups.cancel_reply_kb(),
    )


@user_router.message(WithdrawStates.waiting_requisites)
async def withdraw_requisites(message: Message, state: FSMContext) -> None:
    if message.text == "Отмена":
        await state.clear()
        await Utils.answer(message, "Заявка отменена.", markup=Markups.remove_reply_kb())
        return await _go_main_menu_from_message(message)

    if di.db is None:
        return

    data = await state.get_data()
    amount = data["amount"]
    requisites = message.text.strip()

    async with di.db.async_sessionmaker() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalars().first()
        if not user:
            await state.clear()
            return await Utils.answer(message, "Пользователь не найден.", markup=Markups.remove_reply_kb())

        if user.balance < amount:
            amount = user.balance

        withdraw = WithdrawRequest(
            user_id=user.id,
            amount=amount,
            requisites=requisites,
            status=WithdrawStatus.pending,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(withdraw)

        user.balance -= amount
        await session.commit()

        withdraw_requests_total.inc()

    await state.clear()
    await Utils.answer(message, Messages.withdraw_created(), markup=Markups.remove_reply_kb())
    await _go_main_menu_from_message(message)
