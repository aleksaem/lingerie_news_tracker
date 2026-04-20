from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📰 Top News"),
                KeyboardButton(text="🏷 Competitors"),
            ],
            [
                KeyboardButton(text="📋 News by Topics"),
                KeyboardButton(text="📡 News by Sources"),
            ],
            [
                KeyboardButton(text="⚙️ Settings"),
            ],
        ],
        resize_keyboard=True,
        persistent=True,
    )
