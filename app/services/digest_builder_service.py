"""
DigestBuilderService — formats filtered articles into a Telegram-ready digest string.

Sorts by priority, takes top MAX_ARTICLES_PER_DIGEST, formats as MarkdownV2-compatible text.
"""

from datetime import date
from app.config import settings


class DigestBuilderService:

    PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

    def build(self, articles: list[dict]) -> str:
        """
        Приймає відфільтровані статті, повертає готовий Telegram текст.
        """
        if not articles:
            return "📰 No relevant news found for today."

        today = date.today().strftime("%d.%m.%Y")

        sorted_articles = sorted(
            articles,
            key=lambda a: self.PRIORITY_ORDER.get(a.get("priority", "LOW"), 2)
        )

        top = sorted_articles[:settings.MAX_ARTICLES_PER_DIGEST]

        lines = [f"📰 *Top News — {today}*\n"]

        for i, article in enumerate(top, start=1):
            title = article.get("title", "No title")
            url = article.get("url", "")
            summary = article.get("summary", "")
            why = article.get("why_it_matters", "")
            source = article.get("source", "")

            lines.append(f"*{i}. {title}*")
            if source:
                lines.append(f"_{source}_")
            if summary:
                lines.append(f"{summary}")
            if why:
                lines.append(f"💡 {why}")
            if url:
                lines.append(f"[Read more]({url})")
            lines.append("")

        return "\n".join(lines).strip()
