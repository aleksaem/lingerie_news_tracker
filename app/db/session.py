"""
Database session management.

get_session() — async context manager for repository use.
init_db() — creates all tables on startup (called from main.py).
"""

# TODO: import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
#       import Base from models, Settings


def get_session():
    """
    Async context manager that yields an AsyncSession.
    Usage: async with get_session() as session: ...
    """
    # TODO: yield session from async_sessionmaker
    raise NotImplementedError


async def init_db() -> None:
    """
    Create all tables defined in models.py.
    Call once at bot startup before dispatcher starts polling.
    """
    # TODO: async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    raise NotImplementedError
