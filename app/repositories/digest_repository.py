from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Digest


class DigestRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_date(self, target_date: str) -> Optional[Digest]:
        """Backward compat — returns global top_news digest."""
        return await self.get_by_date_and_type(
            target_date,
            digest_type="top_news",
            user_id=None,
        )

    async def get_by_date_and_type(
        self,
        target_date: str,
        digest_type: str,
        user_id: Optional[int] = None,
        topic_name: Optional[str] = None,
    ) -> Optional[Digest]:
        query = select(Digest).where(
            Digest.digest_date == target_date,
            Digest.digest_type == digest_type,
        )

        if user_id is None:
            query = query.where(Digest.user_id.is_(None))
        else:
            query = query.where(Digest.user_id == user_id)

        if topic_name is None:
            query = query.where(Digest.topic_name.is_(None))
        else:
            query = query.where(Digest.topic_name == topic_name)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def save(
        self,
        target_date: str,
        content: str,
        digest_type: str = "top_news",
        user_id: Optional[int] = None,
        topic_name: Optional[str] = None,
    ) -> Digest:
        existing = await self.get_by_date_and_type(target_date, digest_type, user_id, topic_name)

        if existing:
            existing.content = content
            await self.session.commit()
            return existing

        digest = Digest(
            digest_date=target_date,
            digest_type=digest_type,
            user_id=user_id,
            topic_name=topic_name,
            content=content,
        )
        self.session.add(digest)
        await self.session.commit()
        return digest

    async def invalidate(
        self,
        target_date: str,
        digest_type: str,
        user_id: Optional[int] = None,
        topic_name: Optional[str] = None,
    ) -> bool:
        query = delete(Digest).where(
            Digest.digest_date == target_date,
            Digest.digest_type == digest_type,
        )

        if user_id is None:
            query = query.where(Digest.user_id.is_(None))
        else:
            query = query.where(Digest.user_id == user_id)

        if topic_name is None:
            query = query.where(Digest.topic_name.is_(None))
        else:
            query = query.where(Digest.topic_name == topic_name)

        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0

    async def invalidate_all_topics(
        self,
        target_date: str,
        user_id: Optional[int] = None,
    ) -> int:
        """Delete all topic_news digests for a user on a given date."""
        query = delete(Digest).where(
            Digest.digest_date == target_date,
            Digest.digest_type == "topic_news",
        )

        if user_id is None:
            query = query.where(Digest.user_id.is_(None))
        else:
            query = query.where(Digest.user_id == user_id)

        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount
