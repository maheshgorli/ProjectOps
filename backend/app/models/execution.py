"""ORM models for mutable task execution states."""

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.project import ProjectORM


class TaskExecutionStateORM(Base, UUIDPrimaryKeyMixin):
    """
    Mutable runtime execution state for an individual project task.

    Domain Decision:
    - Immutable plan snapshots retain the planned baseline truth.
    - Mutable task execution state tracks actual execution progress.
    - Statuses: TODO, IN_PROGRESS, BLOCKED, COMPLETED.
    - OVERDUE is strictly derived at runtime, never stored.
    """

    __tablename__ = "task_execution_states"
    __table_args__ = (
        UniqueConstraint("project_id", "task_id", name="uq_task_execution_project_task"),
    )

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="TODO", nullable=False)
    actual_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_finish: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    percent_complete: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[str] = mapped_column(String(255), default="system", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    project: Mapped["ProjectORM"] = relationship(
        "ProjectORM", back_populates="task_execution_states"
    )
