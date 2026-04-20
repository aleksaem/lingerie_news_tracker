from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_sources_keyboard(
    source_pairs: list[tuple[str, str]],
) -> InlineKeyboardMarkup:
    """
    Inline клавіатура з sources і кнопкою All.
    source_pairs: список (display_name, slug)
    display_name — текст кнопки
    slug — callback_data
    """
    buttons = [
        [InlineKeyboardButton(
            text=display_name,
            callback_data=f"source:{slug}",
        )]
        for display_name, slug in source_pairs
    ]

    buttons.append([
        InlineKeyboardButton(
            text="📡 All Sources",
            callback_data="source:__all__",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
