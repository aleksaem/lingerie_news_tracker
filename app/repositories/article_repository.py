"""
ArticleRepository — persistence layer for Article records.

Handles saving batches of fetched articles and querying by URL or date.
Used by DeduplicationService (URL check) and TopNewsSkill (save after filter).
"""

import json
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.db.models import Article


class ArticleRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    ALLOWED_FIELDS = {
        "title", "url", "source", "published_at", "content",
        "relevance", "include_in_digest", "priority", "article_type",
        "competitor", "summary", "why_it_matters", "tags",
        "search_scope", "user_id", "matched_brand", "matched_topic",
        "matched_source",
    }

    async def save_many(self, articles: list[dict]) -> int:
        """
        Зберігає список статей. Пропускає дублікати по url (INSERT OR IGNORE).
        Повертає кількість реально збережених статей.
        """
        if not articles:
            return 0

        saved = 0
        for article_data in articles:
            cleaned = {}
            for key, value in article_data.items():
                if key in self.ALLOWED_FIELDS:
                    cleaned[key] = value

            # apply after loop so it always overrides include_in_digest
            if "include" in article_data:
                cleaned["include_in_digest"] = article_data["include"]

            if "tags" in cleaned:
                tags = cleaned["tags"]
                if isinstance(tags, str):
                    try:
                        cleaned["tags"] = json.loads(tags)
                    except (json.JSONDecodeError, ValueError):
                        cleaned["tags"] = []
                elif not isinstance(tags, list):
                    cleaned["tags"] = []

            stmt = sqlite_insert(Article).values(**cleaned).prefix_with("OR IGNORE")
            result = await self.session.execute(stmt)
            saved += result.rowcount

        await self.session.commit()
        return saved

    async def url_exists(self, url: str) -> bool:
        """Перевіряє чи стаття з таким url вже є в БД."""
        result = await self.session.execute(
            select(Article.id).where(Article.url == url)
        )
        return result.scalar_one_or_none() is not None

    async def get_by_date(self, target_date: str) -> list[Article]:
        """
        Повертає всі статті за дату (за created_at).
        target_date — рядок формату "2025-04-16"
        Тільки ті що include_in_digest=True, відсортовані за priority.
        """
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

        result = await self.session.execute(
            select(Article).where(
                and_(
                    Article.include_in_digest == True,
                    Article.created_at >= f"{target_date} 00:00:00",
                    Article.created_at <= f"{target_date} 23:59:59",
                )
            )
        )
        articles = result.scalars().all()

        # Сортуємо в Python бо SQLite не знає про наш priority enum
        return sorted(articles, key=lambda a: priority_order.get(a.priority or "LOW", 2))

    async def filter_new_urls(self, urls: list[str]) -> list[str]:
        """
        Приймає список url, повертає тільки ті яких немає в БД.
        Використовується в DeduplicationService.
        """
        if not urls:
            return []

        result = await self.session.execute(
            select(Article.url).where(Article.url.in_(urls))
        )
        existing_urls = {row[0] for row in result}
        return [url for url in urls if url not in existing_urls]

    async def get_by_topic(
        self,
        user_id: int,
        topic: str,
        date: str,
    ) -> list:
        """
        Повертає відфільтровані статті для топіка за дату.
        Використовується в NewsByTopicsSkill._get_cached_articles.
        """
        result = await self.session.execute(
            select(Article).where(
                and_(
                    Article.include_in_digest == True,
                    Article.matched_topic == topic,
                    Article.user_id == user_id,
                    Article.created_at >= f"{date} 00:00:00",
                    Article.created_at <= f"{date} 23:59:59",
                )
            )
        )
        return result.scalars().all()

    async def get_by_brand(
        self,
        user_id: int,
        brand: str,
        date: str,
    ) -> list:
        """
        Повертає відфільтровані статті для бренду за дату.
        Використовується в CompetitorsSkill для brand-level cache.
        """
        result = await self.session.execute(
            select(Article).where(
                and_(
                    Article.include_in_digest == True,
                    Article.matched_brand == brand,
                    Article.user_id == user_id,
                    Article.created_at >= f"{date} 00:00:00",
                    Article.created_at <= f"{date} 23:59:59",
                )
            )
        )
        return result.scalars().all()

    async def get_by_source(
        self,
        user_id: int,
        source_display_name: str,
        date: str,
    ) -> list:
        """
        Повертає відфільтровані статті для source за дату.
        Використовується в NewsBySourcesSkill._get_cached_articles.
        """
        result = await self.session.execute(
            select(Article).where(
                and_(
                    Article.include_in_digest == True,
                    Article.matched_source == source_display_name,
                    Article.user_id == user_id,
                    Article.created_at >= f"{date} 00:00:00",
                    Article.created_at <= f"{date} 23:59:59",
                )
            )
        )
        return result.scalars().all()
