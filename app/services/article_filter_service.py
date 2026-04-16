"""
ArticleFilterService — uses LLM to score and filter articles for relevance.

For each article, sends content to LLMClient with article_filter_prompt.txt.
Parses JSON response: include, priority (HIGH/MEDIUM/LOW), summary, why_it_matters, tags.
Returns only articles where include=True, sorted by priority.
"""

# TODO: import LLMClient, load prompt from prompts/article_filter_prompt.txt


class ArticleFilterService:
    """
    AI-powered relevance filter. Enriches articles with LLM-generated metadata.
    """

    def __init__(self):
        # TODO: inject LLMClient, load prompt text
        pass

    async def process_articles(self, articles: list[dict]) -> list[dict]:
        """
        Filter and enrich articles using LLM.
        Returns list of relevant articles with added fields:
        priority, summary, why_it_matters, tags.
        """
        # TODO:
        # 1. For each article, format prompt with title + content
        # 2. Call LLMClient.complete(prompt)
        # 3. Parse JSON response
        # 4. Keep only include=True, attach metadata to dict
        # 5. Sort by priority: HIGH → MEDIUM → LOW
        raise NotImplementedError
