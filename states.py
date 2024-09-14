from aiogram.fsm.state import StatesGroup, State

class OrderFood(StatesGroup):
    wait_for_photo = State()
    admin_text = State()