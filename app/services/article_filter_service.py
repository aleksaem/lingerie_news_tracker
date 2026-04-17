"""
ArticleFilterService — uses LLM to score and filter articles for relevance.

For each article, sends content to LLMClient with article_filter_prompt.txt.
Parses JSON response: include, priority (HIGH/MEDIUM/LOW), summary, why_it_matters, tags.
Returns only articles where include=True, enriched with AI-generated metadata.
"""

import json
import asyncio
from pathlib import Path
from typing import Optional
from app.clients.llm_client import LLMClient


class ArticleFilterService:

    DEFAULT_PROMPT_PATH = Path("app/prompts/article_filter_prompt.txt")
    BATCH_DELAY = 0.5  # секунди між викликами щоб не словити rate limit

    def __init__(self, llm_client: LLMClient, prompt_path: Optional[Path] = None):
        self.llm_client = llm_client
        self._prompt_template = self._load_prompt(
            prompt_path or self.DEFAULT_PROMPT_PATH
        )

    def _load_prompt(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise RuntimeError(f"Промпт не знайдено: {path}")

    async def process_articles(self, articles: list[dict]) -> list[dict]:
        """
        Проганяє кожну статтю через LLM.
        Повертає тільки ті що include=True, збагачені AI полями.
        """
        if not articles:
            return []

        print(f"[ArticleFilterService] Фільтруємо {len(articles)} статей через AI")

        results = []
        for i, article in enumerate(articles):
            print(f"[ArticleFilterService] {i+1}/{len(articles)}: {article['title'][:50]}...")

            enriched = await self._process_single(article)

            if enriched and enriched.get("include"):
                results.append(enriched)

            # Пауза між запитами
            if i < len(articles) - 1:
                await asyncio.sleep(self.BATCH_DELAY)

        print(f"[ArticleFilterService] Релевантних статей: {len(results)}")
        return results

    async def _process_single(self, article: dict) -> Optional[dict]:
        """
        Обробляє одну статтю. Повертає збагачений dict або None при помилці.
        """
        # str.replace instead of .format() — prompt contains literal {} in JSON example
        prompt = (
            self._prompt_template
            .replace("{title}", article.get("title", ""))
            .replace("{source}", article.get("source", ""))
            .replace("{published_at}", article.get("published_at", ""))
            .replace("{content}", article.get("content", "")[:2000])
            .replace("{matched_brand}", article.get("matched_brand", ""))
            .replace("{matched_topic}", article.get("matched_topic", ""))
        )

        raw_response = await self.llm_client.complete(prompt)

        if not raw_response:
            return None

        ai_fields = self._parse_response(raw_response)
        if not ai_fields:
            return None

        # Мерджимо оригінальні поля з AI полями
        return {**article, **ai_fields}

    def _parse_response(self, raw: str) -> Optional[dict]:
        """
        Парсить JSON відповідь від LLM.
        Стійкий до зайвих пробілів і markdown огорток.
        """
        try:
            cleaned = raw.strip()

            # Видаляємо markdown блоки будь-якого формату:
            # ```json ... ``` або ``` ... ```
            if cleaned.startswith("```"):
                # Прибираємо перший рядок (```json або ```)
                # і останній рядок (```)
                lines = cleaned.split("\n")
                inner_lines = []
                for i, line in enumerate(lines):
                    if i == 0 and line.startswith("```"):
                        continue
                    if i == len(lines) - 1 and line.strip() == "```":
                        continue
                    inner_lines.append(line)
                cleaned = "\n".join(inner_lines).strip()

            data = json.loads(cleaned)

            required = {"include", "relevance", "priority", "summary"}
            if not required.issubset(data.keys()):
                print(f"[ArticleFilterService] Відсутні поля: {required - data.keys()}")
                return None

            tags = data.get("tags", [])
            if isinstance(tags, str):
                try:
                    data["tags"] = json.loads(tags)
                except (json.JSONDecodeError, ValueError):
                    data["tags"] = []
            elif tags is None:
                data["tags"] = []
            elif not isinstance(tags, list):
                data["tags"] = []

            competitor = data.get("competitor")
            if isinstance(competitor, list):
                data["competitor"] = competitor[0] if competitor else None

            return data

        except json.JSONDecodeError as e:
            print(f"[ArticleFilterService] JSON parse error: {e}")
            print(f"[ArticleFilterService] Raw: {raw[:300]}")
            return None
