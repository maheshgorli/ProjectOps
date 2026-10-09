"""Global pytest configuration, database fixtures, and test HTTP client."""

from collections.abc import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import backend.app.models  # noqa: F401 - ensure all ORM models are registered
from backend.app.core.config import settings
from backend.app.db.base import Base
from backend.app.db.session import get_async_session
from backend.app.main import app


@pytest.fixture(autouse=True)
def configure_test_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure test suite defaults to explicit mock LLM provider."""
    monkeypatch.setattr(settings, "llm_provider", "mock")


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


@pytest_asyncio.fixture
async def client(test_session: AsyncSession) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an HTTP test client with overridden database session."""

    async def _get_test_session() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_async_session] = _get_test_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
