"""
ArticleRepository — persistence layer for Article records.

Handles saving batches of fetched articles and querying by URL or date.
Used by DeduplicationService (URL check) and TopNewsSkill (save after filter).
"""

# TODO: import Article model, get_session


class ArticleRepository:
    """
    CRUD operations for Article entities.
    """

    async def save_many(self, articles: list[dict]) -> None:
        """
        Persist a batch of article dicts as Article records.
        Skip articles with URLs that already exist in DB.
        """
        # TODO: upsert by URL, map dict fields to Article model fields
        raise NotImplementedError

    async def get_by_url(self, url: str) -> dict | None:
        """
        Return article dict if URL exists in DB, else None.
        Used for deduplication against previously seen articles.
        """
        # TODO: query Article by url field
        raise NotImplementedError

    async def get_by_date(self, date) -> list[dict]:
        """
        Return all articles saved on the given date.
        """
        # TODO: filter Article by published_at or created_at date
        raise NotImplementedError
