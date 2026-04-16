"""
DigestRepository — persistence layer for Digest records.

Digest is a daily cached summary. Check get_by_date before running the pipeline;
save after DigestBuilderService.build() completes.
"""

# TODO: import Digest model, get_session


class DigestRepository:
    """
    CRUD operations for Digest entities.
    """

    async def get_by_date(self, date) -> dict | None:
        """
        Return today's digest dict if it exists, else None.
        Called by top_news_handler to check cache before running pipeline.
        """
        # TODO: query Digest by date field
        raise NotImplementedError

    async def save(self, date, text: str) -> None:
        """
        Persist a new digest for the given date.
        """
        # TODO: create and commit Digest record
        raise NotImplementedError
