"""
Application entry point.

Initializes DB, registers handlers, starts aiogram polling.
"""

import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings
from app.db.session import init_db, AsyncSessionLocal
from app.clients.llm_client import LLMClient
from app.clients.news_client import NewsClient
from app.repositories.article_repository import ArticleRepository
from app.repositories.digest_repository import DigestRepository
from app.services.search_service import SearchService
from app.services.deduplication_service import DeduplicationService
from app.services.article_filter_service import ArticleFilterService
from app.services.digest_builder_service import DigestBuilderService
from app.skills.top_news_skill import TopNewsSkill
from app.bot.handlers.top_news import setup_handlers


async def main():
    await init_db()
    print("[Main] DB initialized")

    news_client = NewsClient()
    llm_client = LLMClient()

    session = AsyncSessionLocal()

    article_repo = ArticleRepository(session)
    digest_repo = DigestRepository(session)

    search_service = SearchService(news_client)
    dedup_service = DeduplicationService(article_repo)
    filter_service = ArticleFilterService(llm_client)
    builder_service = DigestBuilderService()

    skill = TopNewsSkill(
        article_repo=article_repo,
        digest_repo=digest_repo,
        search_service=search_service,
        deduplication_service=dedup_service,
        filter_service=filter_service,
        builder_service=builder_service,
    )

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()

    router = setup_handlers(skill)
    dp.include_router(router)

    print("[Main] Bot started. Ctrl+C to stop.")

    try:
        await dp.start_polling(bot)
    finally:
        await session.close()
        await news_client.close()
        await bot.session.close()
        print("[Main] Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
