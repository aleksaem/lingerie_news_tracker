from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_settings_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ Add Brand"),
                KeyboardButton(text="🗑 Remove Brand"),
            ],
            [
                KeyboardButton(text="➕ Add Topic"),
                KeyboardButton(text="🗑 Remove Topic"),
            ],
            [
                KeyboardButton(text="👁 View Settings"),
                KeyboardButton(text="⬅️ Back"),
            ],
        ],
        resize_keyboard=True,
        persistent=True,
    )


def get_remove_brand_keyboard(
    brands: list[str],
) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"🗑 {brand}",
            callback_data=f"remove_brand:{brand}",
        )]
        for brand in brands
    ]
    buttons.append([InlineKeyboardButton(
        text="Cancel",
        callback_data="remove_brand:cancel",
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_remove_topic_keyboard(
    topics: list[str],
) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"🗑 {topic}",
            callback_data=f"remove_topic:{topic}",
        )]
        for topic in topics
    ]
    buttons.append([InlineKeyboardButton(
        text="Cancel",
        callback_data="remove_topic:cancel",
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
