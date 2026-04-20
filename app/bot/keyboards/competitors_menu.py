from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_competitors_keyboard(
    brands: list[str],
) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=brand,
            callback_data=f"competitor:{brand}",
        )]
        for brand in brands
    ]
    buttons.append([
        InlineKeyboardButton(
            text="🏷 All Competitors",
            callback_data="competitor:__all__",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
