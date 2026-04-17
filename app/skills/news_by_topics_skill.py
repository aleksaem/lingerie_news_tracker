from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

from app.repositories.article_repository import ArticleRepository
from app.repositories.digest_repository import DigestRepository
from app.repositories.user_topic_repository import UserTopicRepository
from app.services.article_filter_service import ArticleFilterService
from app.services.deduplication_service import DeduplicationService
from app.services.topic_digest_builder_service import (
    TopicDigestBuilderService,
)
from app.services.topic_search_service import TopicSearchService

TOPIC_PROMPT_PATH = Path("app/prompts/topic_filter_prompt.txt")

NO_TOPICS_MESSAGE = (
    "📋 You have no topics configured yet.\n\n"
    "Go to ⚙️ Settings → Add Topic to start tracking "
    "topics you care about.\n\n"
    "Examples: _Pricing_, _Sustainability_, _Retail_, "
    "_Campaigns_, _Partnerships_"
)


class NewsByTopicsSkill:

    def __init__(
        self,
        user_topic_repo: UserTopicRepository,
        article_repo: ArticleRepository,
        digest_repo: DigestRepository,
        search_service: TopicSearchService,
        deduplication_service: DeduplicationService,
        llm_client,
        builder_service: TopicDigestBuilderService,
    ):
        self.user_topic_repo = user_topic_repo
        self.article_repo = article_repo
        self.digest_repo = digest_repo
        self.search_service = search_service
        self.deduplication_service = deduplication_service
        self.llm_client = llm_client
        self.builder_service = builder_service

    async def execute_menu(
        self, user_id: int
    ) -> Tuple[str, Optional[List[str]]]:
        """
        Крок 1 - показати меню вибору топіків.
        Якщо топіків немає -> повертає підказку.
        Якщо є -> повертає (prompt_text, topics_list),
        щоб handler міг побудувати inline клавіатуру.
        """
        topics = await self.user_topic_repo.list_topics(user_id)

        if not topics:
            return NO_TOPICS_MESSAGE, None

        prompt_text = (
            "📋 *News by Topics*\n\n"
            "Select a topic or tap *All* to see "
            "the best article from each topic:"
        )
        return prompt_text, topics

    async def execute_topic(
        self, user_id: int, topic: str
    ) -> Tuple[str, Optional[List[str]]]:
        """
        Крок 2A - digest для конкретного топіка.
        Перевіряє кеш -> якщо є повертає одразу.
        Якщо немає -> повний pipeline для цього топіка.
        """
        today = date.today().isoformat()

        print(f"[NewsByTopicsSkill] topic={topic}, user_id={user_id}")

        cached = await self.digest_repo.get_by_date_and_type(
            today,
            digest_type="topic_news",
            user_id=user_id,
            topic_name=topic,
        )
        if cached:
            print(f"[NewsByTopicsSkill] Кеш знайдено для '{topic}'")
            return cached.content, None

        print(f"[NewsByTopicsSkill] Pipeline для '{topic}'")

        raw_articles = await self.search_service.fetch_for_single_topic(
            topic
        )
        if not raw_articles:
            digest_text = self.builder_service.build_single_topic_as_text(
                [], topic
            )
            await self.digest_repo.save(
                today,
                digest_text,
                digest_type="topic_news",
                user_id=user_id,
                topic_name=topic,
            )
            return digest_text, None

        unique_articles = await self.deduplication_service.remove_duplicates(
            raw_articles
        )

        filter_service = ArticleFilterService(
            llm_client=self.llm_client,
            prompt_path=TOPIC_PROMPT_PATH,
        )
        filtered_articles = await filter_service.process_articles(
            unique_articles
        )
        self._attach_user_id(filtered_articles, user_id)

        if filtered_articles:
            await self.article_repo.save_many(filtered_articles)

        header, blocks = self.builder_service.build_single_topic(
            filtered_articles, topic
        )
        digest_text = self.builder_service.build_single_topic_as_text(
            filtered_articles, topic
        )

        await self.digest_repo.save(
            today,
            digest_text,
            digest_type="topic_news",
            user_id=user_id,
            topic_name=topic,
        )

        return header, blocks

    async def execute_all(
        self, user_id: int
    ) -> Tuple[str, Optional[List[str]]]:
        """
        Крок 2B - All режим.
        Збирає по 1 найкращій статті з кожного топіка.

        Логіка економії:
        1. Для кожного топіка перевіряємо кеш
        2. Якщо кеш є - беремо статті звідти
        3. Якщо кешу немає - запускаємо pipeline тільки для цього топіка
        4. Збираємо все разом через build_all_topics
        """
        today = date.today().isoformat()
        topics = await self.user_topic_repo.list_topics(user_id)

        if not topics:
            return NO_TOPICS_MESSAGE, None

        print(
            f"[NewsByTopicsSkill] execute_all "
            f"для {len(topics)} топіків"
        )

        articles_by_topic: dict[str, list[dict]] = {}

        for topic in topics:
            topic_articles = await self._get_or_build_topic(
                user_id, topic, today
            )
            articles_by_topic[topic] = topic_articles
            print(
                f"[NewsByTopicsSkill] '{topic}': "
                f"{len(topic_articles)} статей"
            )

        header, blocks = self.builder_service.build_all_topics(
            articles_by_topic, topics
        )

        return header, blocks

    async def _get_or_build_topic(
        self,
        user_id: int,
        topic: str,
        today: str,
    ) -> list[dict]:
        """
        Допоміжний метод для execute_all.
        Повертає відфільтровані статті для топіка:
        - з кешу якщо digest вже є
        - через pipeline якщо немає

        Важливо: при побудові через pipeline зберігає
        digest в кеш щоб наступний виклик execute_topic
        або execute_all не повторював роботу.
        """
        cached = await self.digest_repo.get_by_date_and_type(
            today,
            digest_type="topic_news",
            user_id=user_id,
            topic_name=topic,
        )
        if cached:
            print(f"[NewsByTopicsSkill] '{topic}' - з кешу")
            return await self._get_cached_articles(
                user_id, topic, today
            )

        print(f"[NewsByTopicsSkill] '{topic}' - запускаємо pipeline")
        raw_articles = await self.search_service.fetch_for_single_topic(
            topic
        )
        if not raw_articles:
            digest_text = self.builder_service.build_single_topic_as_text(
                [], topic
            )
            await self.digest_repo.save(
                today,
                digest_text,
                digest_type="topic_news",
                user_id=user_id,
                topic_name=topic,
            )
            return []

        unique_articles = await self.deduplication_service.remove_duplicates(
            raw_articles
        )

        filter_service = ArticleFilterService(
            llm_client=self.llm_client,
            prompt_path=TOPIC_PROMPT_PATH,
        )
        filtered_articles = await filter_service.process_articles(
            unique_articles
        )
        self._attach_user_id(filtered_articles, user_id)

        if filtered_articles:
            await self.article_repo.save_many(filtered_articles)

        digest_text = self.builder_service.build_single_topic_as_text(
            filtered_articles, topic
        )
        await self.digest_repo.save(
            today,
            digest_text,
            digest_type="topic_news",
            user_id=user_id,
            topic_name=topic,
        )

        return filtered_articles

    async def _get_cached_articles(
        self,
        user_id: int,
        topic: str,
        today: str,
    ) -> list[dict]:
        """
        Дістає статті з article_repo для кешованого топіка.
        Повертає список dict для build_all_topics.
        """
        articles = await self.article_repo.get_by_topic(
            user_id=user_id,
            topic=topic,
            date=today,
        )

        return [
            {
                "title": a.title,
                "url": a.url,
                "source": a.source,
                "summary": a.summary,
                "why_it_matters": a.why_it_matters,
                "priority": a.priority,
                "article_type": a.article_type,
                "matched_topic": a.matched_topic,
            }
            for a in articles
        ]

    def _attach_user_id(
        self, articles: list[dict], user_id: int
    ) -> None:
        for article in articles:
            article["user_id"] = user_id
