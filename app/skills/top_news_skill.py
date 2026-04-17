"""
TopNewsSkill — orchestrates the full pipeline for building today's news digest.

Pipeline:
  SearchService.fetch_articles()
  → DeduplicationService.remove_duplicates()
  → ArticleFilterService.process_articles()
  → ArticleRepository.save_many()
  → DigestBuilderService.build()
  → DigestRepository.save()
  → return digest text
"""

from datetime import date
from typing import Tuple, List, Optional
from app.repositories.article_repository import ArticleRepository
from app.repositories.digest_repository import DigestRepository
from app.services.search_service import SearchService
from app.services.deduplication_service import DeduplicationService
from app.services.article_filter_service import ArticleFilterService
from app.services.digest_builder_service import DigestBuilderService


class TopNewsSkill:

    def __init__(
        self,
        article_repo: ArticleRepository,
        digest_repo: DigestRepository,
        search_service: SearchService,
        deduplication_service: DeduplicationService,
        filter_service: ArticleFilterService,
        builder_service: DigestBuilderService,
    ):
        self.article_repo = article_repo
        self.digest_repo = digest_repo
        self.search_service = search_service
        self.deduplication_service = deduplication_service
        self.filter_service = filter_service
        self.builder_service = builder_service

    async def execute(self) -> Tuple[str, Optional[List[str]]]:
        """
        Returns (text, None) when serving from cache.
        Returns (header, blocks) when running full pipeline.
        """
        today = date.today().isoformat()

        print(f"[TopNewsSkill] Checking digest for {today}")
        cached = await self.digest_repo.get_by_date(today)
        if cached:
            print("[TopNewsSkill] Cache hit")
            return cached.content, None

        print("[TopNewsSkill] No cache — running pipeline")

        print("[TopNewsSkill] Step 1: fetch")
        raw_articles = await self.search_service.fetch_articles()
        if not raw_articles:
            return "📰 No articles found today. Please try again later.", None

        print("[TopNewsSkill] Step 2: dedup")
        unique_articles = await self.deduplication_service.remove_duplicates(raw_articles)
        if not unique_articles:
            return "📰 No new articles found today.", None

        print("[TopNewsSkill] Step 3: AI filter")
        filtered_articles = await self.filter_service.process_articles(unique_articles)

        print("[TopNewsSkill] Step 4: save articles")
        if filtered_articles:
            saved = await self.article_repo.save_many(filtered_articles)
            print(f"[TopNewsSkill] Saved: {saved}")

        print("[TopNewsSkill] Step 5: build digest")
        header, blocks = self.builder_service.build(filtered_articles)
        digest_text = header + "\n\n".join(blocks)

        print("[TopNewsSkill] Step 6: save digest")
        await self.digest_repo.save(today, digest_text)

        return header, blocks
