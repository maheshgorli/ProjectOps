"""SQLAlchemy 2.x Declarative Base and common mixins."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy 2.x declarative models."""

    pass


class UUIDPrimaryKeyMixin:
    """Mixin providing a UUID string primary key."""

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        sort_order=-10,
    )


class TimestampMixin:
    """Mixin providing UTC timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
