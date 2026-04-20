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
        url = (
            f"https://news.google.com/rss/search"
            f"?q={encoded}&hl=en&gl=US&ceid=US:en"
        )

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            articles = self._parse_rss(response.text, query)

            # Розгортаємо Google News URLs
            if articles:
                print(
                    f"[NewsClient] Розгортаємо {len(articles)} URLs..."
                )
                articles = await self._resolve_articles_urls(
                    articles
                )

            return articles
        except Exception as e:
            print(f"[NewsClient] RSS fallback failed: {e}")
            return []

    async def _resolve_google_news_url(
        self, url: str
    ) -> str:
        """
        Розгортає Google News редирект URL до реального.
        Якщо не вдалось — повертає оригінальний URL.
        """
        if "news.google.com" not in url:
            return url

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=10.0,
            ) as client:
                response = await client.get(url)
                final_url = str(response.url)
                # Якщо все ще google — щось пішло не так
                if "news.google.com" in final_url:
                    return url
                return final_url
        except Exception as e:
            print(f"[NewsClient] URL resolve failed: {e}")
            return url

    async def _resolve_articles_urls(
        self, articles: list[dict]
    ) -> list[dict]:
        """
        Розгортає Google News URLs для списку статей.
        Обробляє паралельно для швидкості.
        """
        import asyncio

        async def resolve_one(article: dict) -> dict:
            url = article.get("url", "")
            if "news.google.com" in url:
                resolved = await self._resolve_google_news_url(url)
                return {**article, "url": resolved}
            return article

        # Паралельно але не більше 5 одночасно
        # щоб не перевантажити
        semaphore = asyncio.Semaphore(5)

        async def resolve_with_limit(article):
            async with semaphore:
                return await resolve_one(article)

        return await asyncio.gather(
            *[resolve_with_limit(a) for a in articles]
        )

    def _parse_rss(self, xml_text: str, source: str) -> list[dict]:
        import xml.etree.ElementTree as ET

        articles = []
        try:
            root = ET.fromstring(xml_text)
            items = root.findall(".//item")[:10]

            for item in items:
                title = item.findtext("title") or ""

                # Google News RSS — url буває в guid або link
                guid = item.findtext("guid") or ""
                link = item.findtext("link") or ""
                url = guid if guid.startswith("http") else link

                # Валідація — має бути повний URL
                if not url.startswith("http"):
                    continue

                # Обрізаємо якщо URL явно зламаний
                # (менше 20 символів після домену)
                if len(url) < 30:
                    continue

                pub_date = item.findtext("pubDate") or ""
                source_tag = item.findtext("source") or source

                articles.append({
                    "title": title[:500],
                    "url": url,
                    "source": source_tag,
                    "published_at": pub_date[:100],
                    "content": item.findtext("description") or "",
                })

        except ET.ParseError as e:
            print(f"[NewsClient] RSS parse error: {e}")

        return articles

    async def close(self):
        await self.client.aclose()
