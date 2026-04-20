from app.clients.news_client import NewsClient
from app.config import settings

BRAND_QUERY_TEMPLATES = [
    "{brand} fashion brand launch",
    "{brand} clothing brand campaign",
    "{brand} fashion brand expansion",
    "{brand} apparel brand partnership",
    "{brand} fashion new collection",
    "{brand} clothing brand strategy",
    "{brand} lingerie brand news",
]


class CompetitorSearchService:

    def __init__(self, news_client: NewsClient):
        self.news_client = news_client

    async def fetch_articles(self, brands: list) -> list:
        if not brands:
            return []

        print(f"[CompetitorSearchService] Пошук по брендах: {brands}")

        per_brand_limit = max(10, settings.MAX_RAW_ARTICLES // len(brands))

        all_articles = []
        seen_urls = set()

        for brand in brands:
            brand_articles = await self._fetch_for_brand(brand, seen_urls, limit=per_brand_limit)
            all_articles.extend(brand_articles)
            print(f"[CompetitorSearchService] '{brand}' → {len(brand_articles)} статей (ліміт {per_brand_limit})")

        print(f"[CompetitorSearchService] Разом унікальних статей: {len(all_articles)}")
        return all_articles

    async def _fetch_for_brand(self, brand: str, seen_urls: set, limit: int = 10) -> list:
        brand_articles = []
        queries = self._build_queries(brand)

        for query in queries:
            if len(brand_articles) >= limit:
                break

            articles = await self.news_client.search(query)

            for article in articles:
                if len(brand_articles) >= limit:
                    break
                url = article.get("url", "")
                if not url or url in seen_urls:
                    continue

                # Перевіряємо що стаття дійсно про цей бренд
                if not self._is_relevant(article, brand):
                    continue

                seen_urls.add(url)
                brand_articles.append({
                    **article,
                    "matched_brand": brand,
                    "search_scope": "competitors",
                })

        return brand_articles

    def _build_queries(self, brand: str) -> list:
        return [template.format(brand=brand) for template in BRAND_QUERY_TEMPLATES]

    def _is_relevant(
        self, article: dict, brand: str
    ) -> bool:
        """
        Перевіряє що стаття реально про цей бренд.
        Захист від загальних слів як Staff, Next, Gap.
        """
        title = article.get("title", "").lower()
        content = article.get("content", "").lower()
        brand_lower = brand.lower()
        text = f"{title} {content}"

        # Бренд має бути в заголовку або контенті
        # як окреме слово (не частина іншого слова)
        import re
        pattern = r'\b' + re.escape(brand_lower) + r'\b'

        in_title = bool(re.search(pattern, title))
        in_content = bool(re.search(pattern, content))

        if not (in_title or in_content):
            return False

        if brand_lower == "staff":
            employment_phrases = [
                "staff stories",
                "expand staff",
                "staff by",
                "staff feedback",
                "staff bonus",
                "staff member",
                "staff members",
                "staff cuts",
                "staff layoffs",
                "staff shortage",
                "staff union",
                "staff pay",
            ]
            if any(phrase in text for phrase in employment_phrases):
                return False

        return True

    def get_queries_preview(self, brands: list) -> list:
        queries = []
        for brand in brands:
            queries.extend(self._build_queries(brand))
        return queries
