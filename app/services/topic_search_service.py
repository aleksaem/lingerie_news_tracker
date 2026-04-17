from app.clients.news_client import NewsClient
from app.config import settings

# Словник тем -> набір специфічних queries з lingerie/fashion контекстом.
# Для кожної теми queries мають бути достатньо специфічними,
# щоб уникнути нерелевантних результатів.
TOPIC_QUERY_MAP: dict[str, list[str]] = {
    "Pricing": [
        "lingerie pricing trends 2025",
        "underwear brand price positioning",
        "fashion lingerie price increase market",
        "intimate apparel pricing strategy",
    ],
    "Sustainability": [
        "lingerie sustainability news",
        "sustainable underwear materials",
        "fashion lingerie ESG update",
        "intimate apparel recycled fabrics",
        "lingerie environmental regulation",
    ],
    "Retail": [
        "lingerie retail expansion news",
        "underwear brand store opening",
        "intimate apparel retail strategy",
        "lingerie direct to consumer retail",
    ],
    "Campaigns": [
        "lingerie brand campaign launch",
        "underwear marketing campaign 2025",
        "intimate apparel advertising news",
        "lingerie brand ambassador campaign",
    ],
    "Partnerships": [
        "lingerie brand partnership news",
        "underwear brand collaboration",
        "intimate apparel licensing deal",
        "lingerie celebrity collaboration",
    ],
    "Compliance": [
        "lingerie textile regulation EU",
        "underwear labeling compliance news",
        "fashion intimate apparel regulation",
        "lingerie digital product passport",
    ],
    "Market Trends": [
        "lingerie market trends 2025",
        "intimate apparel industry report",
        "underwear market growth forecast",
        "lingerie consumer behavior shift",
    ],
    "Shapewear": [
        "shapewear market news",
        "shapewear brand launch",
        "body shaping underwear trends",
        "shapewear industry update",
    ],
    "Materials": [
        "lingerie fabric innovation news",
        "underwear sustainable materials",
        "intimate apparel textile technology",
        "lingerie new fabric launch",
    ],
    "E-Commerce": [
        "lingerie ecommerce strategy news",
        "underwear brand online sales",
        "intimate apparel digital retail",
        "lingerie direct to consumer online",
    ],
}

# Fallback шаблони для тем, яких немає в словнику.
FALLBACK_TEMPLATES = [
    "{topic} lingerie news",
    "{topic} fashion intimate apparel",
    "{topic} underwear brand",
]


class TopicSearchService:

    def __init__(self, news_client: NewsClient):
        self.news_client = news_client

    async def fetch_articles(self, topics: list[str]) -> list[dict]:
        """
        Головний метод. Приймає список топіків.
        Повертає унікальні статті з matched_topic полем.
        """
        if not topics:
            return []

        print(f"[TopicSearchService] Пошук по топіках: {topics}")

        per_topic_limit = max(10, settings.MAX_RAW_ARTICLES // len(topics))

        all_articles = []
        seen_urls = set()

        for topic in topics:
            topic_articles = await self._fetch_for_topic(
                topic, seen_urls, limit=per_topic_limit
            )
            all_articles.extend(topic_articles)
            print(
                f"[TopicSearchService] '{topic}' "
                f"-> {len(topic_articles)} статей"
            )

        print(
            f"[TopicSearchService] "
            f"Разом унікальних статей: {len(all_articles)}"
        )
        return all_articles

    async def fetch_for_single_topic(self, topic: str) -> list[dict]:
        """
        Пошук тільки для одного топіка.
        Використовується в execute_topic NewsByTopicsSkill.
        """
        seen_urls: set = set()
        articles = await self._fetch_for_topic(
            topic, seen_urls, limit=settings.MAX_RAW_ARTICLES
        )
        print(
            f"[TopicSearchService] '{topic}' "
            f"-> {len(articles)} статей (single mode)"
        )
        return articles

    async def _fetch_for_topic(
        self,
        topic: str,
        seen_urls: set,
        limit: int = 10,
    ) -> list[dict]:
        """
        Збирає статті для одного топіка.
        Додає matched_topic і search_scope до кожної статті.
        """
        topic_articles = []
        queries = self._get_queries(topic)

        for query in queries:
            if len(topic_articles) >= limit:
                break

            articles = await self.news_client.search(query)

            for article in articles:
                if len(topic_articles) >= limit:
                    break

                url = article.get("url", "")
                if not url or url in seen_urls:
                    continue

                seen_urls.add(url)
                topic_articles.append({
                    **article,
                    "matched_topic": topic,
                    "search_scope": "topics",
                })

        return topic_articles

    def _get_queries(self, topic: str) -> list[str]:
        """
        Повертає queries для теми.
        Якщо тема є в TOPIC_QUERY_MAP - беремо готові queries.
        Якщо немає - генеруємо через fallback шаблони.
        """
        if topic in TOPIC_QUERY_MAP:
            return TOPIC_QUERY_MAP[topic]

        print(
            f"[TopicSearchService] '{topic}' не в TOPIC_QUERY_MAP "
            f"- використовуємо fallback"
        )
        return [
            template.format(topic=topic.lower())
            for template in FALLBACK_TEMPLATES
        ]

    def get_queries_preview(self, topics: list[str]) -> dict[str, list[str]]:
        """
        Утиліта для дебагу - показує всі queries по темах.
        """
        return {
            topic: self._get_queries(topic)
            for topic in topics
        }
