from datetime import date
from typing import Tuple, List


class CompetitorDigestBuilderService:

    PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    MAX_ARTICLES = 3

    def build(self, articles: list, brands: list) -> Tuple[str, List[str]]:
        today = date.today().strftime("%d.%m.%Y")
        brands_str = ", ".join(brands) if brands else "—"

        header = (
            f"🏷 *Competitor Updates — {today}*\n\n"
            f"Brands tracked: _{brands_str}_\n"
        )

        if not articles:
            return header, ["No relevant competitor news found for today."]

        sorted_articles = sorted(
            articles,
            key=lambda a: self.PRIORITY_ORDER.get(a.get("priority", "LOW"), 2)
        )
        top = sorted_articles[:self.MAX_ARTICLES]

        blocks = []
        for i, article in enumerate(top, start=1):
            title = article.get("title", "No title")
            url = article.get("url", "")
            summary = article.get("summary", "")
            why = article.get("why_it_matters", "")
            source = article.get("source", "")
            matched_brand = article.get("matched_brand", "")
            article_type = article.get("article_type", "")

            lines = [f"*{i}. {title}*"]

            meta_parts = []
            if matched_brand:
                meta_parts.append(matched_brand)
            if article_type and article_type != "other":
                meta_parts.append(article_type.replace("_", " "))
            if source:
                meta_parts.append(source)
            if meta_parts:
                lines.append(f"_{' · '.join(meta_parts)}_")

            if summary:
                lines.append(summary)
            if why:
                lines.append(f"💡 {why}")
            if url:
                lines.append(f"[Read more]({url})")

            blocks.append("\n".join(lines))

        return header, blocks

    def build_as_text(self, articles: list, brands: list) -> str:
        header, blocks = self.build(articles, brands)
        if not blocks:
            return header
        return header + "\n\n" + "\n\n".join(blocks)
