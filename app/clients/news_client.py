"""
NewsClient — wrapper around external news search API.

Primary: NewsAPI (newsapi.org) if NEWS_API_KEY is set.
Fallback: Google News RSS via httpx — no key required.
"""

import httpx
from app.config import settings


class NewsClient:

    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self):
        self.api_key = settings.NEWS_API_KEY
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    async def search(self, query: str, days_back: int = 1) -> list[dict]:
        """
        Шукає статті по query за останні days_back днів.
        Повертає список raw dict у єдиному форматі.
        """
        if not self.api_key:
            return await self._search_rss(query)

        from datetime import date, timedelta
        from_date = (date.today() - timedelta(days=days_back)).isoformat()

        params = {
            "q": query,
            "from": from_date,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": 10,
            "apiKey": self.api_key,
        }

        try:
            response = await self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            return [
                self._normalize(article)
                for article in data.get("articles", [])
                if article.get("title") and article.get("url")
            ]

        except httpx.HTTPError as e:
            print(f"[NewsClient] HTTP error for query '{query}': {e}")
            return []
        except Exception as e:
            print(f"[NewsClient] Unexpected error for query '{query}': {e}")
            return []

    def _normalize(self, raw: dict) -> dict:
        """
        Приводить сирий article від NewsAPI до внутрішнього формату.
        Цей формат — єдиний по всьому проєкту.
        """
        return {
            "title": raw.get("title", "")[:500],
            "url": raw.get("url", ""),
            "source": raw.get("source", {}).get("name", "unknown"),
            "published_at": raw.get("publishedAt", "")[:100],
            "content": raw.get("description") or raw.get("content") or "",
        }

    async def _search_rss(self, query: str) -> list[dict]:
        """
        Fallback якщо немає NEWS_API_KEY.
        Google News RSS — безкоштовно, без ключа.
        """
        import urllib.parse
        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en&gl=US&ceid=US:en"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return self._parse_rss(response.text, query)
        except Exception as e:
            print(f"[NewsClient] RSS fallback failed for '{query}': {e}")
            return []

    def _parse_rss(self, xml_text: str, source: str) -> list[dict]:
        """Парсить Google News RSS без зовнішніх бібліотек."""
        import xml.etree.ElementTree as ET

        articles = []
        try:
            root = ET.fromstring(xml_text)
            items = root.findall(".//item")[:10]

            for item in items:
                title = item.findtext("title") or ""
                url = item.findtext("link") or ""
                pub_date = item.findtext("pubDate") or ""

                if not title or not url:
                    continue

                articles.append({
                    "title": title[:500],
                    "url": url,
                    "source": item.findtext("source") or "Google News",
                    "published_at": pub_date[:100],
                    "content": item.findtext("description") or "",
                })

        except ET.ParseError as e:
            print(f"[NewsClient] RSS parse error: {e}")

        return articles

    async def close(self):
        await self.client.aclose()
