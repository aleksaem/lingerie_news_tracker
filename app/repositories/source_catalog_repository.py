from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import SourceCatalog


class SourceCatalogRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_active(self) -> list[SourceCatalog]:
        """Повертає всі активні джерела каталогу."""
        result = await self.session.execute(
            select(SourceCatalog)
            .where(SourceCatalog.is_active == True)
            .order_by(SourceCatalog.display_name)
        )
        return result.scalars().all()

    async def find_by_name(
        self, name: str
    ) -> SourceCatalog | None:
        """
        Пошук по display_name — нечутливий до регістру.
        "business of fashion" знайде "Business of Fashion".
        """
        result = await self.session.execute(
            select(SourceCatalog).where(
                SourceCatalog.is_active == True,
                SourceCatalog.display_name.ilike(name.strip())
            )
        )
        return result.scalar_one_or_none()

    async def find_by_slug(
        self, slug: str
    ) -> SourceCatalog | None:
        """Пошук по slug."""
        result = await self.session.execute(
            select(SourceCatalog).where(
                SourceCatalog.slug == slug,
                SourceCatalog.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def find_by_id(
        self, source_id: int
    ) -> SourceCatalog | None:
        """Пошук по id."""
        result = await self.session.execute(
            select(SourceCatalog).where(
                SourceCatalog.id == source_id
            )
        )
        return result.scalar_one_or_none()

    async def get_available_names(self) -> list[str]:
        """
        Повертає список display_name всіх активних джерел.
        Використовується в повідомленні про помилку
        коли source не знайдено.
        """
        sources = await self.list_active()
        return [s.display_name for s in sources]
