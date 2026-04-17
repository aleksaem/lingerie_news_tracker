from typing import Optional, List
from aiogram.types import Message

TELEGRAM_LIMIT = 4096


async def send_digest(
    message: Message,
    header: str,
    blocks: Optional[List[str]],
) -> None:
    if blocks is None:
        text = header
        if len(text) <= TELEGRAM_LIMIT:
            await message.answer(text, parse_mode="Markdown",
                                 disable_web_page_preview=True)
        else:
            for i in range(0, len(text), TELEGRAM_LIMIT):
                await message.answer(text[i:i + TELEGRAM_LIMIT],
                                     parse_mode="Markdown",
                                     disable_web_page_preview=True)
        return

    current = header
    for block in blocks:
        candidate = current + "\n\n" + block
        if len(candidate) <= TELEGRAM_LIMIT:
            current = candidate
        else:
            await message.answer(current.strip(), parse_mode="Markdown",
                                 disable_web_page_preview=True)
            current = block

    if current.strip():
        await message.answer(current.strip(), parse_mode="Markdown",
                             disable_web_page_preview=True)
