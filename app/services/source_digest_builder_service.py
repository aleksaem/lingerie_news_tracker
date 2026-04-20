from datetime import date


class SourceDigestBuilderService:

    PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

    def _safe_title(self, title: str) -> str:
        """Прибирає символи які ламають Markdown."""
        title = title.replace('*', '').replace('_', '')
        title = title.replace('&', '&amp;')
        return title

    def build_single_source(
        self,
        articles: list[dict],
        source_display_name: str,
    ) -> tuple[str, list[str]]:
        """
        Digest для одного конкретного джерела.
        Показує 2-3 найкращі статті.
        Повертає (header, blocks).
        """
        today = date.today().strftime("%d.%m.%Y")
        header = (
            f"📡 *Source: {source_display_name} — {today}*\n"
        )

        if not articles:
            return header, [
                f"No relevant articles found from "
                f"*{source_display_name}* today."
            ]

        sorted_articles = sorted(
            articles,
            key=lambda a: self.PRIORITY_ORDER.get(
                a.get("priority", "LOW"), 2
            )
        )
        top = sorted_articles[:3]

        blocks = [
            self._build_block(i, article)
            for i, article in enumerate(top, start=1)
        ]

        return header, blocks

    def build_all_sources(
        self,
        articles_by_source: dict[str, list[dict]],
        sources_display_names: list[str],
    ) -> tuple[str, list[str]]:
        """
        Digest по всіх джерелах — All режим.
        articles_by_source: {display_name: [articles]}

        Логіка:
        - 1 source → 2-3 статті
        - 2+ sources → 1 стаття на source
        Повертає (header, blocks).
        """
        today = date.today().strftime("%d.%m.%Y")
        header = f"📡 *News by Sources — {today}*\n"

        if not sources_display_names:
            return header, ["No sources configured."]

        limit_per_source = (
            3 if len(sources_display_names) == 1 else 1
        )

        blocks = []
        for display_name in sources_display_names:
            source_articles = articles_by_source.get(
                display_name, []
            )

            if not source_articles:
                blocks.append(
                    f"*{display_name}*\n"
                    f"_No relevant articles found today._"
                )
                continue

            sorted_articles = sorted(
                source_articles,
                key=lambda a: self.PRIORITY_ORDER.get(
                    a.get("priority", "LOW"), 2
                )
            )
            top = sorted_articles[:limit_per_source]

            source_lines = [f"*{display_name}*", ""]
            for article in top:
                title = article.get("title", "No title")
                url = article.get("url", "")
                summary = article.get("summary", "")
                why = article.get("why_it_matters", "")

                source_lines.append(f"*• {self._safe_title(title)}*")
                if summary:
                    source_lines.append(f"{summary}")
                if why:
                    source_lines.append(f"💡 {why}")
                if url:
                    source_lines.append(
                        f"[Read more]({url})"
                    )

            blocks.append("\n".join(source_lines))

        return header, blocks

    def build_single_source_as_text(
        self,
        articles: list[dict],
        source_display_name: str,
    ) -> str:
        """Зручна обгортка для збереження в БД."""
        header, blocks = self.build_single_source(
            articles, source_display_name
        )
        if not blocks:
            return header
        return header + "\n\n" + "\n\n".join(blocks)

    def _build_block(
        self, index: int, article: dict
    ) -> str:
        """Будує один блок статті."""
        title = article.get("title", "No title")
        url = article.get("url", "")
        summary = article.get("summary", "")
        why = article.get("why_it_matters", "")
        article_type = article.get("article_type", "")

        lines = [f"*{index}. {self._safe_title(title)}*"]

        if article_type and article_type != "other":
            lines.append(
                f"_{article_type.replace('_', ' ')}_"
            )

        if summary:
            lines.append(summary)
        if why:
            lines.append(f"💡 {why}")
        if url:
            lines.append(f"[Read more]({url})")

        return "\n".join(lines)
