"""Database connection and session lifecycle management."""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.core.config import settings
from backend.app.db.base import Base


def get_database_url() -> str:
    """Retrieve the database URL from settings or environment."""
    return os.getenv("DATABASE_URL", settings.database_url)


def create_engine(url: str | None = None) -> AsyncEngine:
    """Create an AsyncEngine instance."""
    db_url = url or get_database_url()
    # SQLite requires check_same_thread=False
    connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}
    return create_async_engine(
        db_url,
        echo=False,
        connect_args=connect_args,
        future=True,
    )


engine = create_engine()
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency generator yielding an AsyncSession."""
    async with async_session_maker() as session:
        yield session


async def create_all_tables(target_engine: AsyncEngine | None = None) -> None:
    """Create all tables in the database (useful for test runs and initial bootstrapping)."""
    eng = target_engine or engine
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables(target_engine: AsyncEngine | None = None) -> None:
    """Drop all tables in the database."""
    eng = target_engine or engine
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
