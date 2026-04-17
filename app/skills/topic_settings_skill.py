from app.repositories.digest_repository import DigestRepository
from app.repositories.user_topic_repository import UserTopicRepository

MAX_TOPICS = 10


class TopicSettingsSkill:

    def __init__(
        self,
        user_topic_repo: UserTopicRepository,
        digest_repo: DigestRepository,
    ):
        self.user_topic_repo = user_topic_repo
        self.digest_repo = digest_repo

    async def add_topic(
        self, user_id: int, topic_name: str
    ) -> str:
        """
        Додає топік і інвалідує topic digest за сьогодні.
        Повертає текст підтвердження для Telegram.
        """
        topic_name = topic_name.strip()

        if not topic_name:
            return "⚠️ Topic name cannot be empty. Please try again."

        if len(topic_name) > 100:
            return "⚠️ Topic name is too long. Max 100 characters."

        topics = await self.user_topic_repo.list_topics(user_id)
        if len(topics) >= MAX_TOPICS:
            return (
                f"⚠️ You have reached the maximum of "
                f"{MAX_TOPICS} topics.\n"
                f"Please remove one before adding a new one."
            )

        added = await self.user_topic_repo.add_topic(
            user_id, topic_name
        )

        normalized = self.user_topic_repo.normalize(topic_name)

        if not added:
            return (
                f"ℹ️ *{normalized}* is already in your tracked topics."
            )

        await self.user_topic_repo.invalidate_topic_digests(user_id)

        return (
            f"✅ *{normalized}* added to your tracked topics.\n\n"
            f"Next time you tap 📋 News by Topics, "
            f"it will include news about this topic."
        )

    async def remove_topic(
        self, user_id: int, topic_name: str
    ) -> str:
        """
        Видаляє топік і інвалідує topic digest за сьогодні.
        Повертає текст підтвердження для Telegram.
        """
        normalized = self.user_topic_repo.normalize(topic_name)
        removed = await self.user_topic_repo.remove_topic(
            user_id, topic_name
        )

        if not removed:
            return (
                f"⚠️ *{normalized}* not found in your tracked topics."
            )

        await self.user_topic_repo.invalidate_topic_digests(user_id)

        return (
            f"🗑 *{normalized}* removed from your tracked topics.\n\n"
            f"Your next News by Topics digest will be updated."
        )

    async def list_topics(self, user_id: int) -> list[str]:
        """
        Повертає список топіків для inline клавіатури.
        """
        return await self.user_topic_repo.list_topics(user_id)
