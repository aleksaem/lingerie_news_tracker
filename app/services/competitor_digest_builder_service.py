from datetime import date
from typing import Tuple, List


class CompetitorDigestBuilderService:

    PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

    def _safe_title(self, title: str) -> str:
        """Прибирає символи які ламають Markdown."""
        title = title.replace('*', '').replace('_', '')
        title = title.replace('&', '&amp;')
        return title

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

        if len(brands) == 1:
            # Один бренд → 2-3 статті
            top = sorted_articles[:3]
        else:
            # Кілька брендів → по 1 на бренд
            seen_brands: dict[str, int] = {}
            top = []
            for article in sorted_articles:
                brand = article.get("matched_brand", "unknown")
                count = seen_brands.get(brand, 0)
                if count < 1:
                    top.append(article)
                    seen_brands[brand] = count + 1

        blocks = []
        for i, article in enumerate(top, start=1):
            title = article.get("title", "No title")
            url = article.get("url", "")
            summary = article.get("summary", "")
            why = article.get("why_it_matters", "")
            source = article.get("source", "")
            matched_brand = article.get("matched_brand", "")
            article_type = article.get("article_type", "")

            if len(brands) == 1:
                lines = [f"*{i}. {self._safe_title(title)}*"]
            else:
                lines = [
                    f"*{matched_brand or 'unknown'}*",
                    "",
                    f"*• {self._safe_title(title)}*",
                ]

            meta_parts = []
            if matched_brand and len(brands) == 1:
                meta_parts.append(matched_brand)
            if article_type and article_type != "other":
                meta_parts.append(article_type.replace("_", " "))
            if source:
                meta_parts.append(source)
            if meta_parts:
                lines.append(f"_{' · '.join(meta_parts)}_")

            if summary:
                lines.append(f"{summary}")
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
