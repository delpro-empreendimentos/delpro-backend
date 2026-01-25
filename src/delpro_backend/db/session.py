"""Docstring for delpro_backend.db.session."""

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from delpro_backend.utils.settings import settings

engine: AsyncEngine = create_async_engine(settings.DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """Yield an async database session.

    Inputs:
    None.

    Returns:
    An AsyncSession instance via generator.
    """
    async with SessionLocal() as session:
        yield session
