import asyncio
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple
from app.repositories.article_repository import ArticleRepository
from app.repositories.digest_repository import DigestRepository
from app.repositories.user_brand_repository import UserBrandRepository
from app.services.competitor_search_service import (
    CompetitorSearchService,
)
from app.services.deduplication_service import DeduplicationService
from app.services.article_filter_service import ArticleFilterService
from app.services.competitor_digest_builder_service import (
    CompetitorDigestBuilderService,
)

COMPETITOR_PROMPT_PATH = Path(
    "app/prompts/competitor_filter_prompt.txt"
)

NO_BRANDS_MESSAGE = (
    "🏷 You have no competitor brands tracked yet.\n\n"
    "Go to ⚙️ Settings → Add Brand to start tracking "
    "your competitors."
)


class CompetitorsSkill:

    def __init__(
        self,
        user_brand_repo: UserBrandRepository,
        article_repo: ArticleRepository,
        digest_repo: DigestRepository,
        search_service: CompetitorSearchService,
        deduplication_service: DeduplicationService,
        llm_client,
        builder_service: CompetitorDigestBuilderService,
    ):
        self.user_brand_repo = user_brand_repo
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
    ) -> Tuple[str, Optional[List[str]]]:
        """
        Повертає меню вибору брендів.
        Якщо немає брендів → підказку.
        Якщо є → (prompt_text, list of brand names)
        """
        brands = await self.user_brand_repo.list_brands(user_id)

        if not brands:
            return NO_BRANDS_MESSAGE, None

        prompt_text = (
            "🏷 *Competitor News*\n\n"
            "Select a brand or tap *All* to see "
            "the best article from each competitor:"
        )
        return prompt_text, brands

    async def execute_brand(
        self, user_id: int, brand: str
    ) -> Tuple[str, Optional[List[str]]]:
        """
        Digest для конкретного бренду.
        Перевіряє кеш → якщо є повертає одразу.
        Якщо немає → повний pipeline.
        """
        today = date.today().isoformat()

        print(
            f"[CompetitorsSkill] brand={brand}, "
            f"user_id={user_id}"
        )

        # Перевірка кешу — filter_value = brand
        cached = await self.digest_repo.get_by_date_and_type(
            today,
            digest_type="competitors",
            user_id=user_id,
            filter_value=brand,
        )
        if cached:
            print(
                f"[CompetitorsSkill] Кеш для '{brand}'"
            )
            return cached.content, None

        lock = self._get_lock(user_id, brand)
        async with lock:
            cached = await self.digest_repo.get_by_date_and_type(
                today,
                digest_type="competitors",
                user_id=user_id,
                filter_value=brand,
            )
            if cached:
                print(
                    f"[CompetitorsSkill] Кеш для '{brand}' "
                    f"з'явився поки чекали"
                )
                return cached.content, None

            # Повний pipeline для одного бренду
            print(f"[CompetitorsSkill] Pipeline для '{brand}'")

            # Крок 1 — пошук тільки по цьому бренду
            raw_articles = await self.search_service.fetch_articles(
                [brand]
            )
            if not raw_articles:
                digest_text = self._empty_digest(brand)
                await self.digest_repo.save(
                    today, digest_text,
                    digest_type="competitors",
                    user_id=user_id,
                    filter_value=brand,
                )
                return digest_text, None

            # Крок 2 — дедуплікація
            unique = await self.deduplication_service\
                .remove_duplicates(raw_articles)

            # Крок 3 — AI фільтрація
            filter_service = ArticleFilterService(
                llm_client=self.llm_client,
                prompt_path=COMPETITOR_PROMPT_PATH,
            )
            filtered = await filter_service.process_articles(unique)

            for article in filtered:
                article["user_id"] = user_id

            # Крок 4 — збереження статей
            if filtered:
                await self.article_repo.save_many(filtered)

            # Крок 5 — побудова digest (2-3 статті)
            header, blocks = self.builder_service.build(
                filtered, [brand]
            )
            digest_text = self.builder_service.build_as_text(
                filtered, [brand]
            )

            # Крок 6 — збереження digest
            await self.digest_repo.save(
                today, digest_text,
                digest_type="competitors",
                user_id=user_id,
                filter_value=brand,
            )

            return header, blocks

    async def execute_all(
        self, user_id: int
    ) -> Tuple[str, Optional[List[str]]]:
        """
        All режим — по 1 статті з кожного бренду.
        Збирає з кешу, добудовує відсутні.
        """
        today = date.today().isoformat()
        brands = await self.user_brand_repo.list_brands(user_id)

        if not brands:
            return NO_BRANDS_MESSAGE, None

        print(
            f"[CompetitorsSkill] execute_all "
            f"для {len(brands)} брендів"
        )

        articles_by_brand: dict[str, list[dict]] = {}

        for brand in brands:
            brand_articles = await self._get_or_build_brand(
                user_id, brand, today
            )
            articles_by_brand[brand] = brand_articles
            print(
                f"[CompetitorsSkill] '{brand}': "
                f"{len(brand_articles)} статей"
            )

        # Будуємо All digest через існуючий builder
        # Передаємо всі статті разом
        all_articles = []
        for articles in articles_by_brand.values():
            all_articles.extend(articles)

        header, blocks = self.builder_service.build(
            all_articles, brands
        )

        return header, blocks

    async def execute(
        self, user_id: int
    ) -> Tuple[str, Optional[List[str]]]:
        """Backward-compatible wrapper for the current handler."""
        return await self.execute_all(user_id)

    async def _get_or_build_brand(
        self,
        user_id: int,
        brand: str,
        today: str,
    ) -> list[dict]:
        """
        Повертає статті для бренду з кешу або через pipeline.
        """
        cached = await self.digest_repo.get_by_date_and_type(
            today,
            digest_type="competitors",
            user_id=user_id,
            filter_value=brand,
        )
        if cached:
            print(f"[CompetitorsSkill] '{brand}' — з кешу")
            return await self._get_cached_articles(
                user_id, brand, today
            )

        lock = self._get_lock(user_id, brand)
        async with lock:
            cached = await self.digest_repo.get_by_date_and_type(
                today,
                digest_type="competitors",
                user_id=user_id,
                filter_value=brand,
            )
            if cached:
                print(f"[CompetitorsSkill] '{brand}' — з кешу")
                return await self._get_cached_articles(
                    user_id, brand, today
                )

            # Pipeline для одного бренду
            print(f"[CompetitorsSkill] '{brand}' — pipeline")
            raw = await self.search_service.fetch_articles([brand])
            if not raw:
                return []

            unique = await self.deduplication_service\
                .remove_duplicates(raw)

            filter_service = ArticleFilterService(
                llm_client=self.llm_client,
                prompt_path=COMPETITOR_PROMPT_PATH,
            )
            filtered = await filter_service.process_articles(unique)

            for article in filtered:
                article["user_id"] = user_id

            if filtered:
                await self.article_repo.save_many(filtered)

            digest_text = self._empty_digest(brand) \
                if not filtered \
                else self.builder_service.build_as_text(
                    filtered, [brand]
                )
            await self.digest_repo.save(
                today,
                digest_text,
                digest_type="competitors",
                user_id=user_id,
                filter_value=brand,
            )

            return filtered

    async def _get_cached_articles(
        self,
        user_id: int,
        brand: str,
        today: str,
    ) -> list[dict]:
        """Дістає статті з article_repo для кешованого бренду."""
        articles = await self.article_repo.get_by_brand(
            user_id=user_id,
            brand=brand,
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
                "matched_brand": a.matched_brand,
                "competitor": a.competitor,
            }
            for a in articles
        ]

    def _empty_digest(self, brand: str) -> str:
        from datetime import date as d
        today = d.today().strftime("%d.%m.%Y")
        return (
            f"🏷 *{brand} — {today}*\n\n"
            f"No relevant news found for *{brand}* today."
        )
