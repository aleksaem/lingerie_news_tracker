"""
SearchService — fetches raw articles from external news sources.

Reads search queries from queries.json, calls NewsClient for each query,
deduplicates by URL within the batch, and returns up to MAX_RAW_ARTICLES.
"""

import json
from app.clients.news_client import NewsClient
from app.config import settings


class SearchService:

    def __init__(self, news_client: NewsClient):
        self.news_client = news_client

    async def fetch_articles(self) -> list[dict]:
        """
        Головний метод. Завантажує queries і збирає статті по кожному.
        Повертає список унікальних raw articles (дедуп по url всередині батча).
        """
        queries = self._load_queries()
        if not queries:
            print("[SearchService] Немає queries у файлі")
            return []

        print(f"[SearchService] Запускаємо пошук по {len(queries)} queries")

        all_articles = []
        seen_urls = set()

        for query in queries:
            articles = await self.news_client.search(query)
            print(f"[SearchService] '{query}' → {len(articles)} статей")

            for article in articles:
                url = article.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_articles.append(article)

        print(f"[SearchService] Разом унікальних статей: {len(all_articles)}")
        return all_articles[:settings.MAX_RAW_ARTICLES]

    def _load_queries(self) -> list[str]:
        """Читає queries з файлу queries.json."""
        try:
            with open(settings.QUERIES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("queries", [])
        except FileNotFoundError:
            print(f"[SearchService] Файл {settings.QUERIES_FILE} не знайдено")
            return []
        except json.JSONDecodeError as e:
            print(f"[SearchService] Помилка парсингу queries.json: {e}")
            return []
