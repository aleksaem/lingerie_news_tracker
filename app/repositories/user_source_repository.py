from datetime import date
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.db.models import UserSource, SourceCatalog, Digest


class UserSourceRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_source(
        self, user_id: int, source_id: int
    ) -> bool:
        """
        Додає source для користувача по source_id з каталогу.
        Повертає True якщо додано, False якщо вже існував.
        """
        stmt = sqlite_insert(UserSource).values(
            user_id=user_id,
            source_id=source_id,
        ).prefix_with("OR IGNORE")

        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def remove_source(
        self, user_id: int, source_id: int
    ) -> bool:
        """
        Видаляє source для користувача.
        Повертає True якщо видалено, False якщо не існував.
        """
        result = await self.session.execute(
            delete(UserSource).where(
                UserSource.user_id == user_id,
                UserSource.source_id == source_id,
            )
        )
        await self.session.commit()
        return result.rowcount > 0

    async def list_sources(
        self, user_id: int
    ) -> list[SourceCatalog]:
        """
        Повертає список SourceCatalog об'єктів
        для цього користувача, відсортованих
        за датою додавання.
        """
        result = await self.session.execute(
            select(SourceCatalog)
            .join(
                UserSource,
                UserSource.source_id == SourceCatalog.id,
            )
            .where(
                UserSource.user_id == user_id,
                SourceCatalog.is_active == True,
            )
            .order_by(UserSource.created_at)
        )
        return result.scalars().all()

    async def list_source_slugs(
        self, user_id: int
    ) -> list[str]:
        """
        Повертає список slug-ів для цього користувача.
        Зручно для пошуку і побудови digest.
        """
        sources = await self.list_sources(user_id)
        return [s.slug for s in sources]

    async def has_sources(self, user_id: int) -> bool:
        """Швидка перевірка — чи є хоч одне джерело."""
        result = await self.session.execute(
            select(UserSource.id)
            .join(
                SourceCatalog,
                UserSource.source_id == SourceCatalog.id,
            )
            .where(
                UserSource.user_id == user_id,
                SourceCatalog.is_active == True,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def invalidate_source_digests(
        self, user_id: int
    ) -> int:
        """
        Видаляє всі source_news digest-и користувача
        за сьогодні. Викликається при add/remove source.
        Повертає кількість видалених записів.
        """
        today = date.today().isoformat()

        result = await self.session.execute(
            delete(Digest).where(
                Digest.user_id == user_id,
                Digest.digest_type == "source_news",
                Digest.digest_date == today,
            )
        )
        await self.session.commit()
        return result.rowcount
