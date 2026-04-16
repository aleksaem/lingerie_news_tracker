"""
Handler for the "Top News" button.

Flow: user taps "Top News" → check DB for today's digest → if found, return it;
otherwise trigger TopNewsSkill to fetch/filter/save/build digest, then return result.
"""

from aiogram.types import Message

# TODO: import TopNewsSkill, wire up router, register handler with dispatcher


async def top_news_handler(message: Message):
    """
    Handle 'Top News' button press.
    Returns today's digest — from DB cache or freshly built.
    """
    # TODO:
    # 1. Call DigestRepository.get_by_date(today)
    # 2. If found → message.answer(digest.text)
    # 3. If not found → await TopNewsSkill().execute() → message.answer(result)
    raise NotImplementedError
