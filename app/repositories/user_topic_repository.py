from datetime import date
from typing import List
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.db.models import UserTopic, Digest


class UserTopicRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def normalize(topic_name: str) -> str:
        return topic_name.strip().title()

    async def add_topic(self, user_id: int, topic_name: str) -> bool:
        normalized = self.normalize(topic_name)
        if not normalized:
            return False

        stmt = sqlite_insert(UserTopic).values(
            user_id=user_id,
            topic_name=normalized,
        ).prefix_with("OR IGNORE")

        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def remove_topic(self, user_id: int, topic_name: str) -> bool:
        normalized = self.normalize(topic_name)

        result = await self.session.execute(
            delete(UserTopic).where(
                UserTopic.user_id == user_id,
                UserTopic.topic_name == normalized,
            )
        )
        await self.session.commit()
        return result.rowcount > 0

    async def list_topics(self, user_id: int) -> List[str]:
        result = await self.session.execute(
            select(UserTopic.topic_name)
            .where(UserTopic.user_id == user_id)
            .order_by(UserTopic.created_at)
        )
        return [row[0] for row in result]

    async def has_topics(self, user_id: int) -> bool:
        result = await self.session.execute(
            select(UserTopic.id)
            .where(UserTopic.user_id == user_id)
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def invalidate_topic_digests(self, user_id: int) -> int:
        """Delete all topic_news digests for user today. Call on any topic list change."""
        today = date.today().isoformat()

        result = await self.session.execute(
            delete(Digest).where(
                Digest.user_id == user_id,
                Digest.digest_type == "topic_news",
                Digest.digest_date == today,
            )
        )
        await self.session.commit()
        return result.rowcount
