from app.clients.news_client import NewsClient
from app.db.models import SourceCatalog
from app.config import settings


SEARCH_TOPICS = [
    "lingerie",
    "fashion news",
    "intimate apparel",
    "retail",
    "brand",
]


class SourceSearchService:

    def __init__(self, news_client: NewsClient):
        self.news_client = news_client

    async def fetch_for_single_source(
        self, source: SourceCatalog
    ) -> list[dict]:
        seen_urls: set = set()
        all_articles = []
        queries = self._build_queries(source.display_name)

        print(
            f"[SourceSearchService] '{source.display_name}' "
            f"— {len(queries)} queries"
        )

        for query in queries:
            if len(all_articles) >= settings.MAX_RAW_ARTICLES:
                break

            articles = await self.news_client.search(query)

            for article in articles:
                if len(all_articles) >= settings.MAX_RAW_ARTICLES:
                    break

                url = article.get("url", "")
                if not url or url in seen_urls:
                    continue

                if not self._is_from_source(article, source):
                    continue

                seen_urls.add(url)
                all_articles.append({
                    **article,
                    "matched_source": source.display_name,
                    "matched_source_slug": source.slug,
                    "search_scope": "sources",
                })

        print(
            f"[SourceSearchService] '{source.display_name}' "
            f"→ {len(all_articles)} статей"
        )
        return all_articles

    async def fetch_for_sources(
        self, sources: list[SourceCatalog]
    ) -> list[dict]:
        if not sources:
            return []

        per_source_limit = max(
            5, settings.MAX_RAW_ARTICLES // len(sources)
        )

        all_articles = []
        seen_urls: set = set()

        for source in sources:
            source_articles = await self._fetch_limited(
                source, seen_urls, limit=per_source_limit
            )
            all_articles.extend(source_articles)
            print(
                f"[SourceSearchService] '{source.display_name}'"
                f" → {len(source_articles)} статей"
            )

        return all_articles

    def _build_queries(self, display_name: str) -> list[str]:
        """
        Будує queries з назвою видання + тематика.
        """
        return [
            f"{display_name} {topic}"
            for topic in SEARCH_TOPICS
        ]

    def _is_from_source(
        self, article: dict, source: SourceCatalog
    ) -> bool:
        """
        Перевіряє що стаття з правильного видання.
        Порівнює по source полю статті і по domain в URL.
        """
        article_source = article.get("source", "").lower()
        display_name = source.display_name.lower()
        domain = source.domain.lower()

        # Перевірка 1 — domain в URL
        url = article.get("url", "").lower()
        if domain in url:
            return True

        # Перевірка 2 — source поле містить назву видання
        # Беремо перші 2 значущих слова (довші за 3 символи)
        source_words = [
            w for w in display_name.split()
            if len(w) > 3
        ]
        if source_words and any(
            word in article_source for word in source_words
        ):
            return True

        # Перевірка 3 — назва видання в заголовку
        # (для випадків коли source поле порожнє)
        title = article.get("title", "").lower()
        if source_words and any(
            word in title for word in source_words
        ):
            return True

        return False

    def get_queries_preview(
        self, source: SourceCatalog
    ) -> list[str]:
        return self._build_queries(source.display_name)

    async def _fetch_limited(
        self,
        source: SourceCatalog,
        seen_urls: set,
        limit: int,
    ) -> list[dict]:
        articles = []
        queries = self._build_queries(source.display_name)

        for query in queries:
            if len(articles) >= limit:
                break

            raw = await self.news_client.search(query)

            for article in raw:
                if len(articles) >= limit:
                    break

                url = article.get("url", "")
                if not url or url in seen_urls:
                    continue

                if not self._is_from_source(article, source):
                    continue

                seen_urls.add(url)
                articles.append({
                    **article,
                    "matched_source": source.display_name,
                    "matched_source_slug": source.slug,
                    "search_scope": "sources",
                })

        return articles
