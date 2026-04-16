"""
DigestBuilderService — formats filtered articles into a Telegram-ready digest string.

Produces a structured text message with sections by priority.
Handles Telegram message length limits (4096 chars).
"""


class DigestBuilderService:
    """
    Builds a formatted digest string from a list of enriched articles.
    """

    def build(self, articles: list[dict]) -> str:
        """
        Format articles into a human-readable digest for Telegram.
        Groups by priority. Each item includes title, summary, why_it_matters, source URL.
        Returns plain text or MarkdownV2 formatted string.
        """
        # TODO:
        # 1. Group articles by priority (HIGH / MEDIUM / LOW)
        # 2. Format each group with header and article entries
        # 3. Truncate or paginate if total length > 4096 chars
        raise NotImplementedError
