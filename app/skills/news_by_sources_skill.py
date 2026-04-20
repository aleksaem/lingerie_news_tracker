import asyncio
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

from app.repositories.article_repository import ArticleRepository
from app.repositories.digest_repository import DigestRepository
from app.repositories.source_catalog_repository import (
    SourceCatalogRepository,
)
from app.repositories.user_source_repository import (
    UserSourceRepository,
)
from app.services.article_filter_service import ArticleFilterService
from app.services.deduplication_service import DeduplicationService
from app.services.source_digest_builder_service import (
    SourceDigestBuilderService,
)
from app.services.source_search_service import SourceSearchService

SOURCE_PROMPT_PATH = Path(
    "app/prompts/source_filter_prompt.txt"
)

NO_SOURCES_MESSAGE = (
    "📡 You have no sources configured yet.\n\n"
    "Go to ⚙️ Settings → Add Source to start following "
    "specific publications.\n\n"
    "Available sources: _Business of Fashion_, "
    "_Vogue Business_, _FashionUnited_, _Retail Dive_, "
    "_WWD_, _Drapers_, _Glossy_, _Fashion Network_"
)


class NewsBySourcesSkill:

    def __init__(
        self,
        user_source_repo: UserSourceRepository,
        source_catalog_repo: SourceCatalogRepository,
        article_repo: ArticleRepository,
        digest_repo: DigestRepository,
        search_service: SourceSearchService,
        deduplication_service: DeduplicationService,
        llm_client,
        builder_service: SourceDigestBuilderService,
    ):
        self.user_source_repo = user_source_repo
        self.source_catalog_repo = source_catalog_repo
        self.article_repo = article_repo
        self.digest_repo = digest_repo
        self.search_service = search_service
        self.deduplication_service = deduplication_service
        self.llm_client = llm_client
        self.builder_service = builder_service
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_lock(
        self, user_id: int, filter_value: str
    ) -> asyncio.Lock:
        """Повертає лок для конкретного user + filter."""
        key = f"{user_id}:{filter_value}"
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    async def execute_menu(
        self, user_id: int
    ) -> Tuple[str, Optional[list]]:
        """
        Повертає меню вибору sources.
        Якщо немає sources → підказку.
        Якщо є → (prompt_text, list of (display_name, slug))
        щоб handler побудував inline клавіатуру.
        """
        sources = await self.user_source_repo.list_sources(
            user_id
        )

        if not sources:
            return NO_SOURCES_MESSAGE, None

        prompt_text = (
            "📡 *News by Sources*\n\n"
            "Select a source or tap *All* to see "
            "the best article from each:"
        )

        source_pairs = [
            (s.display_name, s.slug) for s in sources
        ]
        return prompt_text, source_pairs

    async def execute_source(
        self, user_id: int, source_slug: str
    ) -> Tuple[str, Optional[List[str]]]:
        """
        Digest для конкретного джерела.
        Перевіряє кеш → якщо є повертає одразу.
        Якщо немає → повний pipeline.
        """
        today = date.today().isoformat()

        source = await self.source_catalog_repo.find_by_slug(
            source_slug
        )
        if not source:
            return (
                f"⚠️ Source '{source_slug}' not found.",
                None,
            )

        print(
            f"[NewsBySourcesSkill] source={source.display_name}"
            f", user_id={user_id}"
        )

        cached = await self.digest_repo.get_by_date_and_type(
            today,
            digest_type="source_news",
            user_id=user_id,
            filter_value=source_slug,
        )
        if cached:
            print(
                f"[NewsBySourcesSkill] Кеш для "
                f"'{source.display_name}'"
            )
            return cached.content, None

        lock = self._get_lock(user_id, source_slug)
        async with lock:
            cached = await self.digest_repo.get_by_date_and_type(
                today,
                digest_type="source_news",
                user_id=user_id,
                filter_value=source_slug,
            )
            if cached:
                print(
                    f"[NewsBySourcesSkill] Кеш для "
                    f"'{source.display_name}' з'явився поки чекали"
                )
                return cached.content, None

            print(
                f"[NewsBySourcesSkill] Pipeline для "
                f"'{source.display_name}'"
            )

            raw_articles = await self.search_service.fetch_for_single_source(
                source
            )
            if not raw_articles:
                digest_text = self.builder_service.build_single_source_as_text(
                    [], source.display_name
                )
                await self.digest_repo.save(
                    today, digest_text,
                    digest_type="source_news",
                    user_id=user_id,
                    filter_value=source_slug,
                )
                return digest_text, None

            unique = await self.deduplication_service.remove_duplicates(
                raw_articles
            )

            filter_service = ArticleFilterService(
                llm_client=self.llm_client,
                prompt_path=SOURCE_PROMPT_PATH,
            )
            filtered = await filter_service.process_articles(unique)
            self._attach_user_id(filtered, user_id)

            if filtered:
                await self.article_repo.save_many(filtered)

            header, blocks = self.builder_service.build_single_source(
                filtered, source.display_name
            )
            digest_text = self.builder_service.build_single_source_as_text(
                filtered, source.display_name
            )

            await self.digest_repo.save(
                today, digest_text,
                digest_type="source_news",
                user_id=user_id,
                filter_value=source_slug,
            )

            return header, blocks

    async def execute_all(
        self, user_id: int
    ) -> Tuple[str, Optional[List[str]]]:
        """
        All режим — по 1 статті з кожного source.
        Збирає з кешу, добудовує відсутні.
        """
        today = date.today().isoformat()
        sources = await self.user_source_repo.list_sources(
            user_id
        )

        if not sources:
            return NO_SOURCES_MESSAGE, None

        print(
            f"[NewsBySourcesSkill] execute_all "
            f"для {len(sources)} sources"
        )

        articles_by_source: dict[str, list[dict]] = {}

        for source in sources:
            source_articles = await self._get_or_build_source(
                user_id, source, today
            )
            articles_by_source[source.display_name] = (
                source_articles
            )
            print(
                f"[NewsBySourcesSkill] '{source.display_name}'"
                f": {len(source_articles)} статей"
            )

        display_names = [s.display_name for s in sources]
        header, blocks = self.builder_service.build_all_sources(
            articles_by_source, display_names
        )

        return header, blocks

    async def _get_or_build_source(
        self,
        user_id: int,
        source,
        today: str,
    ) -> list[dict]:
        """
        Повертає відфільтровані статті для source.
        З кешу якщо є, через pipeline якщо немає.
        Зберігає в кеш після побудови.
        """
        cached = await self.digest_repo.get_by_date_and_type(
            today,
            digest_type="source_news",
            user_id=user_id,
            filter_value=source.slug,
        )
        if cached:
            print(
                f"[NewsBySourcesSkill] '{source.display_name}'"
                f" — з кешу"
            )
            return await self._get_cached_articles(
                user_id, source.display_name, today
            )

        lock = self._get_lock(user_id, source.slug)
        async with lock:
            cached = await self.digest_repo.get_by_date_and_type(
                today,
                digest_type="source_news",
                user_id=user_id,
                filter_value=source.slug,
            )
            if cached:
                print(
                    f"[NewsBySourcesSkill] '{source.display_name}'"
                    f" — з кешу"
                )
                return await self._get_cached_articles(
                    user_id, source.display_name, today
                )

            print(
                f"[NewsBySourcesSkill] '{source.display_name}'"
                f" — pipeline"
            )
            raw = await self.search_service.fetch_for_single_source(source)
            if not raw:
                digest_text = self.builder_service.build_single_source_as_text(
                    [], source.display_name
                )
                await self.digest_repo.save(
                    today, digest_text,
                    digest_type="source_news",
                    user_id=user_id,
                    filter_value=source.slug,
                )
                return []

            unique = await self.deduplication_service.remove_duplicates(raw)

            filter_service = ArticleFilterService(
                llm_client=self.llm_client,
                prompt_path=SOURCE_PROMPT_PATH,
            )
            filtered = await filter_service.process_articles(unique)
            self._attach_user_id(filtered, user_id)

            if filtered:
                await self.article_repo.save_many(filtered)

            digest_text = self.builder_service.build_single_source_as_text(
                filtered, source.display_name
            )
            await self.digest_repo.save(
                today, digest_text,
                digest_type="source_news",
                user_id=user_id,
                filter_value=source.slug,
            )

            return filtered

    async def _get_cached_articles(
        self,
        user_id: int,
        source_display_name: str,
        today: str,
    ) -> list[dict]:
        """
        Дістає статті з article_repo для кешованого source.
        """
        articles = await self.article_repo.get_by_source(
            user_id=user_id,
            source_display_name=source_display_name,
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
                "matched_source": a.matched_source,
            }
            for a in articles
        ]

    def _attach_user_id(
        self, articles: list[dict], user_id: int
    ) -> None:
        for article in articles:
            article["user_id"] = user_id
