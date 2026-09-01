from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from .config import AsyncSessionLocal


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_async_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for async database session (for use outside FastAPI)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
