"""
Main menu keyboard. Shown on /start and as persistent reply keyboard.
Currently contains only the 'Top News' button.
"""

from aiogram.types import ReplyKeyboardMarkup

# TODO: import KeyboardButton, configure resize_keyboard=True, one_time_keyboard=False


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Build and return the main menu reply keyboard.
    Buttons: ['Top News']
    """
    # TODO: construct ReplyKeyboardMarkup with 'Top News' button
    raise NotImplementedError
