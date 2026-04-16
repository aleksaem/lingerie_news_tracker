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

# TODO: import all services and repositories


class TopNewsSkill:
    """
    Orchestrates news fetch → dedup → filter → persist → digest pipeline.
    Called by top_news_handler when no cached digest exists for today.
    """

    def __init__(self):
        # TODO: inject SearchService, DeduplicationService, ArticleFilterService,
        #       DigestBuilderService, ArticleRepository, DigestRepository
        pass

    async def execute(self) -> str:
        """
        Run full pipeline. Returns formatted digest string ready to send via Telegram.
        """
        # TODO: implement pipeline steps
        raise NotImplementedError
