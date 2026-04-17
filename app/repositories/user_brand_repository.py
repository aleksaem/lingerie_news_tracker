from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.db.models import UserBrand, Digest


class UserBrandRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_brand(self, user_id: int, brand_name: str) -> bool:
        brand_name = brand_name.strip()
        if not brand_name:
            return False

        stmt = sqlite_insert(UserBrand).values(
            user_id=user_id,
            brand_name=brand_name,
        ).prefix_with("OR IGNORE")

        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def remove_brand(self, user_id: int, brand_name: str) -> bool:
        result = await self.session.execute(
            delete(UserBrand).where(
                UserBrand.user_id == user_id,
                UserBrand.brand_name == brand_name,
            )
        )
        await self.session.commit()
        return result.rowcount > 0

    async def list_brands(self, user_id: int) -> list:
        result = await self.session.execute(
            select(UserBrand.brand_name)
            .where(UserBrand.user_id == user_id)
            .order_by(UserBrand.created_at)
        )
        return [row[0] for row in result]

    async def has_brands(self, user_id: int) -> bool:
        result = await self.session.execute(
            select(UserBrand.id)
            .where(UserBrand.user_id == user_id)
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def invalidate_competitor_digest(self, user_id: int, date: str) -> None:
        await self.session.execute(
            delete(Digest).where(
                Digest.user_id == user_id,
                Digest.digest_type == "competitors",
                Digest.digest_date == date,
            )
        )
        await self.session.commit()
