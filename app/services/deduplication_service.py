"""
DeduplicationService — two-level duplicate removal before AI filtering.

Level 1: within-batch dedup by URL + fuzzy title match.
Level 2: DB dedup via ArticleRepository.filter_new_urls().
"""

from difflib import SequenceMatcher
from app.repositories.article_repository import ArticleRepository


class DeduplicationService:

    SIMILARITY_THRESHOLD = 0.80  # поріг для fuzzy match по title

    def __init__(self, article_repository: ArticleRepository):
        self.article_repo = article_repository

    async def remove_duplicates(self, articles: list[dict]) -> list[dict]:
        """
        Головний метод. Два рівні дедуплікації:
        1. Всередині поточного батча (по URL + fuzzy title)
        2. Проти БД (по URL)
        Повертає список унікальних статей.
        """
        if not articles:
            return []

        print(f"[DeduplicationService] Отримано статей: {len(articles)}")

        # Рівень 1 — дедуп всередині батча
        unique_in_batch = self._deduplicate_batch(articles)
        print(f"[DeduplicationService] Після дедупу батча: {len(unique_in_batch)}")

        # Рівень 2 — фільтрація проти БД
        unique_urls = [a["url"] for a in unique_in_batch]
        new_urls = await self.article_repo.filter_new_urls(unique_urls)
        new_urls_set = set(new_urls)

        result = [a for a in unique_in_batch if a["url"] in new_urls_set]
        print(f"[DeduplicationService] Після фільтрації проти БД: {len(result)}")

        return result

    def _deduplicate_batch(self, articles: list[dict]) -> list[dict]:
        """
        Дедуплікація всередині одного батча.
        Крок 1: прибирає дублікати по однаковому URL.
        Крок 2: fuzzy match по title — якщо схожість >= threshold,
                залишає статтю з довшим content.
        """
        # Крок 1 — унікальні URL
        seen_urls = set()
        url_unique = []
        for article in articles:
            url = article.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                url_unique.append(article)

        # Крок 2 — fuzzy match по title
        result = []
        for candidate in url_unique:
            candidate_title = candidate.get("title", "").lower()
            is_duplicate = False

            for kept in result:
                kept_title = kept.get("title", "").lower()
                similarity = self._title_similarity(candidate_title, kept_title)

                if similarity >= self.SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    # Залишаємо статтю з довшим content
                    if len(candidate.get("content", "")) > len(kept.get("content", "")):
                        result.remove(kept)
                        result.append(candidate)
                    break

            if not is_duplicate:
                result.append(candidate)

        return result

    def _title_similarity(self, title_a: str, title_b: str) -> float:
        """Повертає float 0.0–1.0 схожості двох заголовків."""
        if not title_a or not title_b:
            return 0.0
        return SequenceMatcher(None, title_a, title_b).ratio()
