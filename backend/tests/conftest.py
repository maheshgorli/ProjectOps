"""Global pytest configuration, database fixtures, and test HTTP client."""

from collections.abc import AsyncGenerator
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import backend.app.models  # noqa: F401 - ensure all ORM models are registered
from backend.app.auth.security import create_access_token, hash_password
from backend.app.core.config import settings
from backend.app.db.base import Base
from backend.app.db.session import get_async_session
from backend.app.main import app
from backend.app.models.auth import UserORM


@pytest.fixture(autouse=True)
def configure_test_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure test suite defaults to explicit mock LLM provider and test secret key."""
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "auth_secret_key", "test-auth-secret-key-at-least-32-chars-long!")


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
    """Provide an unauthenticated HTTP test client with overridden database session."""

    async def _get_test_session() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_async_session] = _get_test_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_user(test_session: AsyncSession) -> UserORM:
    """Provide a primary test user."""
    user = UserORM(
        id=str(uuid4()),
        email="testowner@example.com",
        display_name="Test Owner",
        password_hash=hash_password("Password123!"),
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest.fixture
def auth_token(auth_user: UserORM) -> str:
    """Provide a valid signed JWT for auth_user."""
    return create_access_token(auth_user.id)


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Provide bearer authorization headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture
async def auth_client(
    test_session: AsyncSession,
    auth_headers: dict[str, str],
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an authenticated client acting as auth_user."""

    async def _get_test_session() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_async_session] = _get_test_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers=auth_headers,
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def other_user(test_session: AsyncSession) -> UserORM:
    """Provide a secondary test user (non-member / stranger)."""
    user = UserORM(
        id=str(uuid4()),
        email="otheruser@example.com",
        display_name="Other User",
        password_hash=hash_password("Password123!"),
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_client(
    test_session: AsyncSession,
    other_user: UserORM,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an authenticated client acting as other_user (non-member)."""

    async def _get_test_session() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_async_session] = _get_test_session
    token = create_access_token(other_user.id)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
