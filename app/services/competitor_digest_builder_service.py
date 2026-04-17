from datetime import date
from typing import Tuple, List, Dict


class CompetitorDigestBuilderService:

    PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

    def _get_limit_per_brand(self, brands: list) -> int:
        if len(brands) == 1:
            return 3
        return 1

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

        limit_per_brand = self._get_limit_per_brand(brands)

        seen_brands: Dict[str, int] = {}
        top = []
        for article in sorted_articles:
            brand = article.get("matched_brand", "unknown")
            count = seen_brands.get(brand, 0)
            if count < limit_per_brand:
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
