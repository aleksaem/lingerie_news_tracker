from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_topics_keyboard(
    topics: list[str],
) -> InlineKeyboardMarkup:
    """
    Inline клавіатура з топіками і кнопкою All.
    Кожен топік - окрема кнопка.
    All - завжди остання кнопка.
    """
    buttons = [
        [InlineKeyboardButton(
            text=topic,
            callback_data=f"topic:{topic}",
        )]
        for topic in topics
    ]

    buttons.append([
        InlineKeyboardButton(
            text="📋 All Topics",
            callback_data="topic:__all__",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
