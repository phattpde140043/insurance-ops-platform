from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.core_database_pool_size,
    max_overflow=settings.core_database_max_overflow,
)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)
ai_engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.ai_database_pool_size,
    max_overflow=settings.ai_database_max_overflow,
    pool_timeout=settings.ai_database_pool_timeout_seconds,
)
AiAsyncSessionLocal = async_sessionmaker(
    bind=ai_engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_ai_db_session() -> AsyncIterator[AsyncSession]:
    async with AiAsyncSessionLocal() as session:
        yield session


def get_ai_pool_status() -> dict[str, int]:
    return {
        "checked_out": ai_engine.pool.checkedout(),
        "size": ai_engine.pool.size(),
        "overflow": ai_engine.pool.overflow(),
    }
