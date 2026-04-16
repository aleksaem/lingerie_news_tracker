"""
NewsClient — wrapper around external news search API (e.g. NewsAPI, Bing News, or Brave Search).

Called by SearchService for each query string.
Returns raw article dicts; normalization happens in SearchService.
"""

# TODO: import httpx, Settings — decide which news API to use


class NewsClient:
    """
    Fetches news articles from external search API by query string.
    """

    def __init__(self):
        # TODO: init httpx.AsyncClient with base_url and auth headers
        pass

    async def search(self, query: str) -> list[dict]:
        """
        Search for articles matching query.
        Returns list of raw article dicts from API response.
        Each dict should contain: url, title, published_at, source, content/description.
        """
        # TODO: GET /search?q=query, parse response, return normalized list
        raise NotImplementedError
