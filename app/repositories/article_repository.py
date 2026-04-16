"""
ArticleRepository — persistence layer for Article records.

Handles saving batches of fetched articles and querying by URL or date.
Used by DeduplicationService (URL check) and TopNewsSkill (save after filter).
"""

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.db.models import Article


class ArticleRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_many(self, articles: list[dict]) -> int:
        """
        Зберігає список статей. Пропускає дублікати по url (INSERT OR IGNORE).
        Повертає кількість реально збережених статей.
        """
        if not articles:
            return 0

        saved = 0
        for article_data in articles:
            stmt = sqlite_insert(Article).values(**article_data).prefix_with("OR IGNORE")
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
