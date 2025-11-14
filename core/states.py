from aiogram.fsm.state import State, StatesGroup


class AddCardStates(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_price = State()
    waiting_photo = State()


class WithdrawStates(StatesGroup):
    waiting_requisites = State()


class AdminEditCardStates(StatesGroup):
    waiting_field_choice = State()
    waiting_new_value = State()
