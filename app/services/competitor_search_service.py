from app.clients.news_client import NewsClient
from app.config import settings

BRAND_QUERY_TEMPLATES = [
    "{brand} launch",
    "{brand} campaign",
    "{brand} expansion",
    "{brand} retail",
    "{brand} partnership",
    "{brand} new collection",
    "{brand} ecommerce",
]


class CompetitorSearchService:

    def __init__(self, news_client: NewsClient):
        self.news_client = news_client

    async def fetch_articles(self, brands: list) -> list:
        if not brands:
            return []

        print(f"[CompetitorSearchService] Пошук по брендах: {brands}")

        all_articles = []
        seen_urls = set()

        for brand in brands:
            brand_articles = await self._fetch_for_brand(brand, seen_urls)
            all_articles.extend(brand_articles)
            print(f"[CompetitorSearchService] '{brand}' → {len(brand_articles)} статей")

        print(f"[CompetitorSearchService] Разом унікальних статей: {len(all_articles)}")

        return all_articles[:settings.MAX_RAW_ARTICLES]

    async def _fetch_for_brand(self, brand: str, seen_urls: set) -> list:
        brand_articles = []
        queries = self._build_queries(brand)

        for query in queries:
            articles = await self.news_client.search(query)

            for article in articles:
                url = article.get("url", "")
                if not url or url in seen_urls:
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

    def get_queries_preview(self, brands: list) -> list:
        queries = []
        for brand in brands:
            queries.extend(self._build_queries(brand))
        return queries
