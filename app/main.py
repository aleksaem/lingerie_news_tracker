import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.db.session import init_db, AsyncSessionLocal

from app.clients.llm_client import LLMClient
from app.clients.news_client import NewsClient

from app.repositories.article_repository import ArticleRepository
from app.repositories.digest_repository import DigestRepository
from app.repositories.user_brand_repository import UserBrandRepository
from app.repositories.user_topic_repository import UserTopicRepository

from app.services.search_service import SearchService
from app.services.competitor_search_service import (
    CompetitorSearchService,
)
from app.services.topic_search_service import TopicSearchService
from app.services.deduplication_service import DeduplicationService
from app.services.article_filter_service import ArticleFilterService
from app.services.digest_builder_service import DigestBuilderService
from app.services.competitor_digest_builder_service import (
    CompetitorDigestBuilderService,
)
from app.services.topic_digest_builder_service import (
    TopicDigestBuilderService,
)

from app.skills.top_news_skill import TopNewsSkill
from app.skills.competitors_skill import CompetitorsSkill
from app.skills.news_by_topics_skill import NewsByTopicsSkill
from app.skills.brand_settings_skill import BrandSettingsSkill
from app.skills.topic_settings_skill import TopicSettingsSkill

from app.bot.handlers.top_news import setup_handlers
from app.bot.handlers.competitors import setup_competitors_handler
from app.bot.handlers.topic_news import setup_topic_news_handler
from app.bot.handlers.settings import setup_settings_handler


async def main():

    # --- БД ---
    await init_db()
    print("[Main] БД ініціалізована")

    # --- Клієнти ---
    news_client = NewsClient()
    llm_client = LLMClient()

    # --- Сесія БД ---
    session = AsyncSessionLocal()

    # --- Репозиторії ---
    article_repo = ArticleRepository(session)
    digest_repo = DigestRepository(session)
    user_brand_repo = UserBrandRepository(session)
    user_topic_repo = UserTopicRepository(session)

    # --- Сервіси ---
    search_service = SearchService(news_client)
    competitor_search_service = CompetitorSearchService(news_client)
    topic_search_service = TopicSearchService(news_client)
    dedup_service = DeduplicationService(article_repo)
    builder_service = DigestBuilderService()
    competitor_builder_service = CompetitorDigestBuilderService()
    topic_builder_service = TopicDigestBuilderService()

    # --- Skills ---
    top_news_skill = TopNewsSkill(
        article_repo=article_repo,
        digest_repo=digest_repo,
        search_service=search_service,
        deduplication_service=dedup_service,
        filter_service=ArticleFilterService(llm_client),
        builder_service=builder_service,
    )

    competitors_skill = CompetitorsSkill(
        user_brand_repo=user_brand_repo,
        article_repo=article_repo,
        digest_repo=digest_repo,
        search_service=competitor_search_service,
        deduplication_service=dedup_service,
        llm_client=llm_client,
        builder_service=competitor_builder_service,
    )

    news_by_topics_skill = NewsByTopicsSkill(
        user_topic_repo=user_topic_repo,
        article_repo=article_repo,
        digest_repo=digest_repo,
        search_service=topic_search_service,
        deduplication_service=dedup_service,
        llm_client=llm_client,
        builder_service=topic_builder_service,
    )

    brand_settings_skill = BrandSettingsSkill(
        user_brand_repo=user_brand_repo,
        digest_repo=digest_repo,
        user_topic_repo=user_topic_repo,
    )

    topic_settings_skill = TopicSettingsSkill(
        user_topic_repo=user_topic_repo,
        digest_repo=digest_repo,
    )

    # --- Bot і Dispatcher ---
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.MARKDOWN
        ),
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # --- Реєструємо роутери ---
    # Порядок важливий — специфічніші handlers першими
    dp.include_router(setup_handlers(top_news_skill))
    dp.include_router(
        setup_competitors_handler(competitors_skill)
    )
    dp.include_router(
        setup_topic_news_handler(news_by_topics_skill)
    )
    dp.include_router(
        setup_settings_handler(
            brand_skill=brand_settings_skill,
            topic_skill=topic_settings_skill,
        )
    )

    print("[Main] Бот запущений. Натисни Ctrl+C щоб зупинити.")

    try:
        await dp.start_polling(bot)
    finally:
        await session.close()
        await news_client.close()
        await bot.session.close()
        print("[Main] Бот зупинений")


if __name__ == "__main__":
    asyncio.run(main())
