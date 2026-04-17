from datetime import date
from pathlib import Path
from typing import Tuple, List, Optional
from app.repositories.article_repository import ArticleRepository
from app.repositories.digest_repository import DigestRepository
from app.repositories.user_brand_repository import UserBrandRepository
from app.services.competitor_search_service import CompetitorSearchService
from app.services.deduplication_service import DeduplicationService
from app.services.article_filter_service import ArticleFilterService
from app.services.competitor_digest_builder_service import CompetitorDigestBuilderService

COMPETITOR_PROMPT_PATH = Path("app/prompts/competitor_filter_prompt.txt")

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

    async def execute(self, user_id: int) -> Tuple[str, Optional[List[str]]]:
        """
        Returns (text, None) for no-brands and cache-hit cases.
        Returns (header, blocks) when running full pipeline.
        """
        today = date.today().isoformat()

        print(f"[CompetitorsSkill] user_id={user_id}, date={today}")
        brands = await self.user_brand_repo.list_brands(user_id)
        if not brands:
            print("[CompetitorsSkill] Немає брендів — повертаємо підказку")
            return NO_BRANDS_MESSAGE, None

        print(f"[CompetitorsSkill] Бренди користувача: {brands}")

        cached = await self.digest_repo.get_by_date_and_type(
            today, digest_type="competitors", user_id=user_id,
        )
        if cached:
            print("[CompetitorsSkill] Знайдено кешований digest")
            return cached.content, None

        print("[CompetitorsSkill] Запускаємо pipeline")

        print("[CompetitorsSkill] Крок 1: пошук статей по брендах")
        raw_articles = await self.search_service.fetch_articles(brands)
        if not raw_articles:
            digest_text = self.builder_service.build_as_text([], brands)
            await self.digest_repo.save(
                today, digest_text, digest_type="competitors", user_id=user_id,
            )
            return digest_text, None

        print("[CompetitorsSkill] Крок 2: дедуплікація")
        unique_articles = await self.deduplication_service.remove_duplicates(raw_articles)

        print("[CompetitorsSkill] Крок 3: AI фільтрація")
        filter_service = ArticleFilterService(
            llm_client=self.llm_client,
            prompt_path=COMPETITOR_PROMPT_PATH,
        )
        filtered_articles = await filter_service.process_articles(unique_articles)

        print("[CompetitorsSkill] Крок 4: збереження статей")
        if filtered_articles:
            saved = await self.article_repo.save_many(filtered_articles)
            print(f"[CompetitorsSkill] Збережено статей: {saved}")

        print("[CompetitorsSkill] Крок 5: побудова digest")
        header, blocks = self.builder_service.build(filtered_articles, brands)
        digest_text = self.builder_service.build_as_text(filtered_articles, brands)

        print("[CompetitorsSkill] Крок 6: збереження digest")
        await self.digest_repo.save(
            today, digest_text, digest_type="competitors", user_id=user_id,
        )

        return header, blocks
