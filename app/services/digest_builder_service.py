"""
DigestBuilderService — formats filtered articles into a Telegram-ready digest.

Sorts by priority, takes top MAX_ARTICLES_PER_DIGEST, returns header + per-article blocks
so the handler can split messages at article boundaries instead of mid-article.
"""

from datetime import date
from typing import Tuple, List
from app.config import settings


class DigestBuilderService:

    PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

    def build(self, articles: list) -> Tuple[str, List[str]]:
        """
        Returns (header, blocks) where each block is one formatted article.
        Returns ("", []) when articles is empty.
        """
        if not articles:
            return "", []

        today = date.today().strftime("%d.%m.%Y")
        header = f"📰 *Top News — {today}*\n"

        sorted_articles = sorted(
            articles,
            key=lambda a: self.PRIORITY_ORDER.get(a.get("priority", "LOW"), 2)
        )
        top = sorted_articles[:settings.MAX_ARTICLES_PER_DIGEST]

        blocks = []
        for i, article in enumerate(top, start=1):
            title = article.get("title", "No title")
            url = article.get("url", "")
            summary = article.get("summary", "")
            why = article.get("why_it_matters", "")
            source = article.get("source", "")

            lines = [f"*{i}. {title}*"]
            if source:
                lines.append(f"_{source}_")
            if summary:
                lines.append(summary)
            if why:
                lines.append(f"💡 {why}")
            if url:
                lines.append(f"[Read more]({url})")

            blocks.append("\n".join(lines))

        return header, blocks
