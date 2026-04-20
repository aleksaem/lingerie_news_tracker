from __future__ import annotations

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Digest


class DigestRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_date(
        self, target_date: str
    ) -> Digest | None:
        """Зворотна сумісність — глобальний top_news."""
        return await self.get_by_date_and_type(
            target_date,
            digest_type="top_news",
            user_id=None,
            filter_value=None,
        )

    async def get_by_date_and_type(
        self,
        target_date: str,
        digest_type: str,
        user_id: int | None = None,
        filter_value: str | None = None,
    ) -> Digest | None:
        """
        Універсальний метод для всіх типів digest.
        filter_value:
          - None для top_news і competitors
          - topic name для topic_news
          - source slug для source_news
        """
        query = select(Digest).where(
            Digest.digest_date == target_date,
            Digest.digest_type == digest_type,
        )

        if user_id is None:
            query = query.where(Digest.user_id.is_(None))
        else:
            query = query.where(Digest.user_id == user_id)

        if filter_value is None:
            query = query.where(
                Digest.filter_value.is_(None)
            )
        else:
            query = query.where(
                Digest.filter_value == filter_value
            )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def save(
        self,
        target_date: str,
        content: str,
        digest_type: str = "top_news",
        user_id: int | None = None,
        filter_value: str | None = None,
    ) -> Digest:
        existing = await self.get_by_date_and_type(
            target_date, digest_type, user_id, filter_value
        )

        if existing:
            existing.content = content
            await self.session.commit()
            return existing

        digest = Digest(
            digest_date=target_date,
            digest_type=digest_type,
            user_id=user_id,
            filter_value=filter_value,
            content=content,
        )
        self.session.add(digest)
        await self.session.commit()
        return digest

    async def invalidate(
        self,
        target_date: str,
        digest_type: str,
        user_id: int | None = None,
        filter_value: str | None = None,
    ) -> bool:
        query = delete(Digest).where(
            Digest.digest_date == target_date,
            Digest.digest_type == digest_type,
        )

        if user_id is None:
            query = query.where(Digest.user_id.is_(None))
        else:
            query = query.where(Digest.user_id == user_id)

        if filter_value is None:
            query = query.where(
                Digest.filter_value.is_(None)
            )
        else:
            query = query.where(
                Digest.filter_value == filter_value
            )

        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0

    async def invalidate_by_type(
        self,
        target_date: str,
        digest_type: str,
        user_id: int,
    ) -> int:
        """
        Видаляє всі digest-и конкретного типу для user
        за дату. Використовується при зміні sources або
        topics — інвалідує всі одразу.
        """
        result = await self.session.execute(
            delete(Digest).where(
                Digest.digest_date == target_date,
                Digest.digest_type == digest_type,
                Digest.user_id == user_id,
            )
        )
        await self.session.commit()
        return result.rowcount
