from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    waiting_for_brand_name = State()
    waiting_for_topic_name = State()
