"""
Database session management.

get_session() — async context manager for repository use.
init_db() — creates all tables on startup (called from main.py).
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import settings
from app.db.models import Base


def _get_database_url() -> str:
    """
    Reads DATABASE_URL from Settings/env and adapts Railway Postgres URLs
    for SQLAlchemy async engine.
    """
    database_url = settings.DATABASE_URL

    if database_url.startswith("postgres://"):
        return database_url.replace(
            "postgres://", "postgresql+asyncpg://", 1
        )

    if database_url.startswith("postgresql://"):
        return database_url.replace(
            "postgresql://", "postgresql+asyncpg://", 1
        )

    return database_url


# Engine — створюється один раз при старті
engine = create_async_engine(
    _get_database_url(),
    echo=False,  # True для дебагу SQL запитів
)

# Фабрика сесій
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Створює всі таблиці якщо їх немає. Викликається при старті бота."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """
    Використовується як context manager:

    async with get_session() as session:
        result = await session.execute(...)
    """
    async with AsyncSessionLocal() as session:
        yield session
