"""Global pytest configuration and database fixtures."""

from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import backend.app.models  # noqa: F401 - ensure all ORM models are registered
from backend.app.db.base import Base


@pytest_asyncio.fixture
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated, in-memory SQLite AsyncSession for testing."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()
