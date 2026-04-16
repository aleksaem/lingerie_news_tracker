"""
DigestRepository — persistence layer for Digest records.

Digest is a daily cached summary. Check get_by_date before running the pipeline;
save after DigestBuilderService.build() completes.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Digest


class DigestRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_date(self, target_date: str) -> Optional[Digest]:
        """
        Повертає digest за дату або None якщо немає.
        target_date — рядок формату "2025-04-16"
        Це головна перевірка кешу в TopNewsSkill.
        """
        result = await self.session.execute(
            select(Digest).where(Digest.digest_date == target_date)
        )
        return result.scalar_one_or_none()

    async def save(self, target_date: str, content: str) -> Digest:
        """
        Зберігає digest за дату.
        Якщо за цю дату вже є — оновлює content (на випадок повторного запуску).
        """
        existing = await self.get_by_date(target_date)

        if existing:
            existing.content = content
            await self.session.commit()
            return existing

        digest = Digest(digest_date=target_date, content=content)
        self.session.add(digest)
        await self.session.commit()
        return digest
