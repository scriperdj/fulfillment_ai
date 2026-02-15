"""Database initialization — creates all tables idempotently."""

from sqlalchemy import create_engine

from src.config.settings import get_settings
from src.db.models import Base


async def init_db() -> None:
    """Create all tables using the async engine. Idempotent (safe to call multiple times)."""
    from sqlalchemy.ext.asyncio import create_async_engine

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


def init_db_sync() -> None:
    """Create all tables using the sync engine. Idempotent (safe to call multiple times)."""
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL_SYNC)
    Base.metadata.create_all(bind=engine)
    engine.dispose()
