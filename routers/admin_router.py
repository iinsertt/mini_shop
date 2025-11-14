from datetime import datetime, timezone
from typing import Optional

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, BufferedInputFile

from core.notifier import safe_notify
from core.database import (
    Card,
    CardStatus,
    User,
    WithdrawRequest,
    WithdrawStatus,
)
from core.metrics import users_total, cards_total
import core.di as di
from core.filters import AdminFilter
from core.states import AdminEditCardStates
from core.utils import Utils
from misc import BotLogger
from template.markup import Markups
from template.message import Messages

from sqlalchemy import select
from sqlalchemy.orm import selectinload

import io
import xlsxwriter

admin_router = Router(name="admin_router")
admin_router.message.filter(AdminFilter())
admin_router.callback_query.filter(AdminFilter())
logger = BotLogger.get_logger(__name__)


@admin_router.callback_query(F.data == "admin-menu-0")
async def admin_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await Utils.answer(callback, Messages.admin_menu(), markup=Markups.admin_menu(), edit_it=True)


@admin_router.callback_query(F.data == "admin-back-0")
async def admin_back(callback: CallbackQuery, state: FSMContext) -> None:
    if di.repo is None:
        logger.error("Repository is not initialized")
        return
    user = await di.repo.get_user_by_telegram_id(callback.from_user.id)
    is_admin = bool(user and user.is_admin)
    from template.message import Messages as Msgs
    from template.markup import Markups as Mk
    await Utils.answer(
        callback,
        Msgs.start(callback.from_user.first_name),
        markup=Mk.start_menu(is_admin=is_admin),
    )


async def _fetch_pending_card_with_neighbors(offset: int) -> tuple[Optional[Card], bool, bool]:
    if di.db is None:
        return None, False, False
    async with di.db.async_sessionmaker() as session:
        result = await session.execute(
            select(Card)
            .where(Card.status == CardStatus.pending)
            .order_by(Card.id)
            .offset(offset)
            .limit(2)
            .options(selectinload(Card.owner))
        )
        cards = result.scalars().all()
        if not cards:
            return None, False, False
        card = cards[0]
        has_prev = offset > 0
        has_next = len(cards) > 1
        return card, has_prev, has_next


async def _show_moderation_card(target: CallbackQuery | Message, offset: int, edit: bool) -> None:
    card, has_prev, has_next = await _fetch_pending_card_with_neighbors(offset)
    if not card:
        await Utils.answer(
            target,
            Messages.moderation_empty(),
            markup=Markups.admin_menu(),
            edit_it=False,
        )
        return

    kb = Markups.admin_moderation_keyboard(
        offset=offset,
        has_prev=has_prev,
        has_next=has_next,
        card=card,
    )
    text = Messages.format_card(
        card_title=card.title,
        card_description=card.description,
        price=card.price,
        owner_username=card.owner.username if card.owner else None,
        show_owner=True,
    )

    await Utils.answer(target, text, markup=kb, edit_it=edit, file_id=card.photo_file_id)


@admin_router.callback_query(F.data == "admin-moderation-0")
async def moderation_start(callback: CallbackQuery, state: FSMContext) -> None:
    await _show_moderation_card(callback, offset=0, edit=False)


@admin_router.callback_query(F.data.startswith("admin-mod_prev-"))
async def moderation_prev(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split("-")
    try:
        offset = int(parts[2])
    except (IndexError, ValueError):
        offset = 0
    new_offset = max(offset - 1, 0)
    await _show_moderation_card(callback, offset=new_offset, edit=True)


@admin_router.callback_query(F.data.startswith("admin-mod_next-"))
async def moderation_next(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split("-")
    try:
        offset = int(parts[2])
    except (IndexError, ValueError):
        offset = 0
    new_offset = max(offset + 1, 0)
    await _show_moderation_card(callback, offset=new_offset, edit=True)


@admin_router.callback_query(F.data.startswith("admin-modapprove-"))
async def moderation_approve(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split("-")
    try:
        card_id = int(parts[2])
    except (IndexError, ValueError):
        await callback.answer("Ошибка карточки.")
        return

    if di.db is None:
        logger.error("DB is not initialized")
        return

    async with di.db.async_sessionmaker() as session:
        result = await session.execute(
            select(Card)
            .options(selectinload(Card.owner))
            .where(Card.id == card_id)
        )
        card: Card | None = result.scalars().first()

        if not card:
            await callback.answer("Карточка не найдена.")
            return

        if card.status != CardStatus.pending:
            await callback.answer("Карточка уже промодерирована.")
            return

        card.status = CardStatus.approved
        card.updated_at = datetime.now(timezone.utc)
        await session.commit()

        logger.info("Карточка %s одобрена", card_id)

        if card.owner:
            await safe_notify(
                callback.message.bot,
                card.owner.telegram_id,
                f"✅ Ваша карточка «{card.title}» была одобрена и добавлена в каталог!",
            )

    try:
        await callback.message.edit_reply_markup(
            reply_markup=Markups.admin_card_result_keyboard(approved=True)
        )
    except Exception as e:
        logger.error(f"Failed to edit moderation keyboard: {e}")

    await _show_moderation_card(callback, offset=0, edit=False)
    await callback.answer("Карточка одобрена.", show_alert=True)


@admin_router.callback_query(F.data.startswith("admin-modreject-"))
async def moderation_reject(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split("-")
    try:
        card_id = int(parts[2])
    except (IndexError, ValueError):
        await callback.answer("Ошибка карточки.")
        return

    if di.db is None:
        logger.error("DB is not initialized")
        return

    async with di.db.async_sessionmaker() as session:
        result = await session.execute(
            select(Card)
            .options(selectinload(Card.owner))
            .where(Card.id == card_id)
        )
        card: Card | None = result.scalars().first()

        if not card:
            await callback.answer("Карточка не найдена.")
            return

        if card.status != CardStatus.pending:
            await callback.answer("Карточка уже промодерирована.")
            return

        card.status = CardStatus.rejected
        card.updated_at = datetime.now(timezone.utc)
        await session.commit()

        logger.info("Карточка %s отклонена", card_id)

        if card.owner:
            await safe_notify(
                callback.message.bot,
                card.owner.telegram_id,
                f"❌ Ваша карточка «{card.title}» была отклонена модерацией.",
            )

    try:
        await callback.message.edit_reply_markup(
            reply_markup=Markups.admin_card_result_keyboard(approved=False)
        )
    except Exception as e:
        logger.error(f"Failed to edit moderation keyboard: {e}")

    await _show_moderation_card(callback, offset=0, edit=False)
    await callback.answer("Карточка отклонена.", show_alert=True)


@admin_router.callback_query(F.data.startswith("admin-modedit-"))
async def moderation_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split("-")
    try:
        card_id = int(parts[2])
    except (IndexError, ValueError):
        await callback.answer("Ошибка карточки.")
        return

    if di.db is None:
        logger.error("DB is not initialized")
        return

    async with di.db.async_sessionmaker() as session:
        card = await session.get(Card, card_id)
        if not card:
            await callback.answer("Карточка не найдена.")
            return
        if card.status != CardStatus.pending:
            await callback.answer(
                "Нельзя изменять карточку после модерации.",
                show_alert=True,
            )
            return

    await state.set_state(AdminEditCardStates.waiting_field_choice)
    await state.update_data(card_id=card_id)
    await Utils.answer(callback, "Выберите поле для изменения:", markup=None)


@admin_router.message(AdminEditCardStates.waiting_field_choice, F.text)
async def moderation_edit_choose_field(message: Message, state: FSMContext) -> None:
    choice = message.text.strip()
    if choice == "Отмена":
        await state.clear()
        await message.answer("Изменение карточки отменено.", reply_markup=Markups.remove_reply_kb())
        return

    field_map = {
        "Название": "title",
        "Описание": "description",
        "Цена": "price",
        "Фото": "photo_file_id",
    }
    field = field_map.get(choice)
    if not field:
        await message.answer("Неверный выбор. Попробуйте ещё раз.")
        return

    await state.update_data(field=field)
    await state.set_state(AdminEditCardStates.waiting_new_value)

    if field == "photo_file_id":
        await message.answer("Отправьте новое фото карточки.", reply_markup=Markups.cancel_reply_kb())
    elif field == "price":
        await message.answer("Введите новую цену (число).", reply_markup=Markups.cancel_reply_kb())
    else:
        await message.answer("Введите новое значение.", reply_markup=Markups.cancel_reply_kb())


@admin_router.message(AdminEditCardStates.waiting_new_value)
async def moderation_edit_apply(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    card_id = data.get("card_id")
    field = data.get("field")

    if message.text == "Отмена":
        await state.clear()
        await message.answer("Изменение карточки отменено.", reply_markup=Markups.remove_reply_kb())
        return

    if di.db is None:
        logger.error("DB is not initialized")
        return

    new_value = None
    if field == "photo_file_id":
        if not message.photo:
            await message.answer("Нужно отправить фото.")
            return
        new_value = message.photo[-1].file_id
    elif field == "price":
        try:
            new_value = float(message.text.replace(",", "."))
        except (TypeError, ValueError):
            await message.answer("Цена должна быть числом. Попробуйте ещё раз.")
            return
    else:
        new_value = message.text.strip()

    async with di.db.async_sessionmaker() as session:
        result = await session.execute(
            select(Card)
            .options(selectinload(Card.owner))
            .where(Card.id == card_id)
        )
        card: Card | None = result.scalars().first()
        if not card:
            await message.answer("Карточка не найдена.", reply_markup=Markups.remove_reply_kb())
            await state.clear()
            return

        if card.status != CardStatus.pending:
            await message.answer(
                "Нельзя изменять карточку после модерации.",
                reply_markup=Markups.remove_reply_kb(),
            )
            await state.clear()
            return

        setattr(card, field, new_value)
        card.updated_at = datetime.now(timezone.utc)
        await session.commit()
        logger.info("Карточка %s обновлена. Поле %s", card_id, field)

        text = Messages.format_card(
            card_title=card.title,
            card_description=card.description,
            price=card.price,
            owner_username=card.owner.username if card.owner else None,
            show_owner=True,
        )
        photo_id = card.photo_file_id

    await state.clear()
    await message.answer(Messages.card_updated(), reply_markup=Markups.remove_reply_kb())

    await Utils.answer(
        message,
        text,
        markup=Markups.admin_moderation_keyboard(offset=0, has_prev=False, has_next=False, card=card),
        edit_it=False,
        file_id=photo_id,
    )


@admin_router.callback_query(F.data == "admin-stats-0")
async def admin_stats(callback: CallbackQuery, state: FSMContext) -> None:
    if di.db is None:
        logger.error("DB is not initialized")
        return

    async with di.db.async_sessionmaker() as session:
        result = await session.execute(
            select(User).options(selectinload(User.cards))
        )
        users = result.scalars().all()

    if not users:
        users_total.set(0)
        cards_total.set(0)
        await Utils.answer(callback, Messages.stats_header() + "\nПользователей нет.")
        return

    total_cards = sum(len(u.cards) for u in users)
    users_total.set(len(users))
    cards_total.set(total_cards)

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    worksheet = workbook.add_worksheet("Статистика")

    headers = ["Пользователь", "Всего карточек", "Одобрено", "Отклонено"]
    for col, h in enumerate(headers):
        worksheet.write(0, col, h)

    row = 1
    for u in users:
        total = len(u.cards)
        approved = len([c for c in u.cards if c.status == CardStatus.approved])
        rejected = len([c for c in u.cards if c.status == CardStatus.rejected])
        worksheet.write(row, 0, u.username or f"id:{u.id}")
        worksheet.write(row, 1, total)
        worksheet.write(row, 2, approved)
        worksheet.write(row, 3, rejected)
        row += 1

    workbook.close()
    output.seek(0)

    file = BufferedInputFile(output.read(), filename="stats.xlsx")
    await callback.message.answer_document(file, caption="📊 Статистика пользователей")
    logger.info("Статистика выгружена в XLSX")


async def _fetch_withdraw_with_neighbors(offset: int) -> tuple[Optional[WithdrawRequest], bool, bool]:
    if di.db is None:
        return None, False, False
    async with di.db.async_sessionmaker() as session:
        result = await session.execute(
            select(WithdrawRequest)
            .where(WithdrawRequest.status == WithdrawStatus.pending)
            .order_by(WithdrawRequest.id)
            .offset(offset)
            .limit(2)
            .options(selectinload(WithdrawRequest.user))
        )
        withdraws = result.scalars().all()
        if not withdraws:
            return None, False, False
        w = withdraws[0]
        has_prev = offset > 0
        has_next = len(withdraws) > 1
        return w, has_prev, has_next


async def _show_withdraw(callback: CallbackQuery, offset: int, edit: bool) -> None:
    w, has_prev, has_next = await _fetch_withdraw_with_neighbors(offset)
    if not w:
        await Utils.answer(
            callback,
            Messages.withdraws_empty(),
            markup=Markups.admin_menu(),
            edit_it=False,
        )
        return

    kb = Markups.admin_withdraw_keyboard(
        offset=offset,
        has_prev=has_prev,
        has_next=has_next,
        request=w,
    )
    text = Messages.withdraw_request_text(
        username=w.user.username if w.user else None,
        amount=w.amount,
        requisites=w.requisites,
    )

    await Utils.answer(callback, text, markup=kb, edit_it=edit)


@admin_router.callback_query(F.data == "admin-withdraws-0")
async def admin_withdraws_start(callback: CallbackQuery, state: FSMContext) -> None:
    await _show_withdraw(callback, offset=0, edit=False)


@admin_router.callback_query(F.data.startswith("admin-wd_prev-"))
async def admin_withdraws_prev(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split("-")
    try:
        offset = int(parts[2])
    except (IndexError, ValueError):
        offset = 0
    new_offset = max(offset - 1, 0)
    await _show_withdraw(callback, offset=new_offset, edit=True)


@admin_router.callback_query(F.data.startswith("admin-wd_next-"))
async def admin_withdraws_next(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split("-")
    try:
        offset = int(parts[2])
    except (IndexError, ValueError):
        offset = 0
    new_offset = max(offset + 1, 0)
    await _show_withdraw(callback, offset=new_offset, edit=True)


@admin_router.callback_query(F.data.startswith("admin-wdpaid-"))
async def admin_withdraw_paid(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split("-")
    try:
        req_id = int(parts[2])
    except (IndexError, ValueError):
        await callback.answer("Ошибка заявки.")
        return

    if di.db is None:
        logger.error("DB is not initialized")
        return

    async with di.db.async_sessionmaker() as session:
        result = await session.execute(
            select(WithdrawRequest)
            .options(selectinload(WithdrawRequest.user))
            .where(WithdrawRequest.id == req_id)
        )
        w: WithdrawRequest | None = result.scalars().first()

        if not w:
            await callback.answer("Заявка не найдена.")
            return

        if w.status != WithdrawStatus.pending:
            await callback.answer("Заявка уже обработана.")
            return

        w.status = WithdrawStatus.completed
        w.updated_at = datetime.now(timezone.utc)
        await session.commit()

        logger.info("Заявка %s отмечена как выплаченная", req_id)

        if w.user:
            await safe_notify(
                callback.message.bot,
                w.user.telegram_id,
                f"💰 Ваша заявка на вывод {w.amount:.2f} была успешно выплачена!",
            )

    try:
        await callback.message.edit_reply_markup(
            reply_markup=Markups.admin_withdraw_result_keyboard()
        )
    except Exception as e:
        logger.error(f"Failed to edit withdraw keyboard: {e}")

    await _show_withdraw(callback, offset=0, edit=False)
    await callback.answer("Выплата отмечена как проведённая.", show_alert=True)
