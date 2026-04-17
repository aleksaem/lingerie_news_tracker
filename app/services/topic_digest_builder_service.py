from datetime import date


class TopicDigestBuilderService:

    PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

    def build_single_topic(
        self,
        articles: list[dict],
        topic: str,
    ) -> tuple[str, list[str]]:
        """
        Digest для одного конкретного топіка.
        Показує 2-3 найкращі статті.
        Повертає (header, blocks).
        """
        today = date.today().strftime("%d.%m.%Y")
        header = f"📋 *Topic: {topic} — {today}*\n"

        if not articles:
            return header, [
                f"No relevant news found for *{topic}* today."
            ]

        sorted_articles = sorted(
            articles,
            key=lambda a: self.PRIORITY_ORDER.get(
                a.get("priority", "LOW"), 2
            )
        )

        # 1 топік -> 2-3 статті
        top = sorted_articles[:3]
        blocks = [
            self._build_block(i, article)
            for i, article in enumerate(top, start=1)
        ]

        return header, blocks

    def build_all_topics(
        self,
        articles_by_topic: dict[str, list[dict]],
        topics: list[str],
    ) -> tuple[str, list[str]]:
        """
        Digest по всіх топіках - All режим.
        articles_by_topic: {topic_name: [filtered articles]}

        Логіка:
        - 1 топік -> 2-3 статті
        - 2+ топіки -> 1 стаття на топік
        Повертає (header, blocks).
        """
        today = date.today().strftime("%d.%m.%Y")
        header = f"📋 *News by Topics — {today}*\n"

        if not topics:
            return header, ["No topics configured."]

        limit_per_topic = 3 if len(topics) == 1 else 1

        blocks = []
        for topic in topics:
            topic_articles = articles_by_topic.get(topic, [])

            if not topic_articles:
                blocks.append(
                    f"*{topic}*\n"
                    f"_No relevant news found today._"
                )
                continue

            sorted_articles = sorted(
                topic_articles,
                key=lambda a: self.PRIORITY_ORDER.get(
                    a.get("priority", "LOW"), 2
                )
            )
            top = sorted_articles[:limit_per_topic]

            topic_lines = [f"*{topic}*"]
            for article in top:
                title = article.get("title", "No title")
                url = article.get("url", "")
                summary = article.get("summary", "")
                why = article.get("why_it_matters", "")

                topic_lines.append(f"• {title}")
                if summary:
                    topic_lines.append(f"  {summary}")
                if why:
                    topic_lines.append(f"  💡 {why}")
                if url:
                    topic_lines.append(f"  [Read more]({url})")

            blocks.append("\n".join(topic_lines))

        return header, blocks

    def build_single_topic_as_text(
        self,
        articles: list[dict],
        topic: str,
    ) -> str:
        """Зручна обгортка для збереження в БД."""
        header, blocks = self.build_single_topic(articles, topic)
        if not blocks:
            return header
        return header + "\n\n" + "\n\n".join(blocks)

    def _build_block(
        self, index: int, article: dict
    ) -> str:
        """Будує один блок статті для single topic режиму."""
        title = article.get("title", "No title")
        url = article.get("url", "")
        summary = article.get("summary", "")
        why = article.get("why_it_matters", "")
        source = article.get("source", "")
        article_type = article.get("article_type", "")

        lines = [f"*{index}. {title}*"]

        meta_parts = []
        if article_type and article_type != "other":
            meta_parts.append(article_type)
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

        return "\n".join(lines)
