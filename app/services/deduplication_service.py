"""
DeduplicationService — removes duplicate articles before AI filtering.

Deduplication strategy:
  1. Exact URL match
  2. Near-duplicate title detection (e.g. Jaccard similarity or URL normalization)
  3. Cross-reference with ArticleRepository to skip already-persisted URLs
"""

# TODO: import ArticleRepository if checking against DB


class DeduplicationService:
    """
    Removes duplicate articles from a list before further processing.
    """

    def __init__(self):
        # TODO: optionally inject ArticleRepository for DB-level dedup
        pass

    def remove_duplicates(self, articles: list[dict]) -> list[dict]:
        """
        Remove duplicates from articles list.
        Returns deduplicated list preserving original order.
        """
        # TODO: implement URL-based dedup, optionally title similarity
        raise NotImplementedError
