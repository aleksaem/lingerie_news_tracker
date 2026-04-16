"""
SearchService — fetches raw articles from external news sources.

Reads search queries from queries.json, calls NewsClient for each query,
and returns a flat list of raw article dicts.
"""

# TODO: import NewsClient, load queries.json


class SearchService:
    """
    Fetches raw articles for all configured search queries.
    """

    def __init__(self):
        # TODO: inject NewsClient, load queries from queries.json
        pass

    async def fetch_articles(self) -> list[dict]:
        """
        Run all queries concurrently. Returns flat list of raw article dicts.
        Each dict should contain at minimum: url, title, published_at, source, content.
        """
        # TODO: iterate queries, call NewsClient.search(), gather results, flatten
        raise NotImplementedError
