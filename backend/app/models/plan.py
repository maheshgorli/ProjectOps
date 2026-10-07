"""ORM models for immutable versioned plan snapshots, tasks, and dependencies."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.project import ProjectORM


class ProjectPlanORM(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Immutable versioned snapshot of a project plan.
    Rule: Never overwrite history. Updates increment version number.
    """

    __tablename__ = "project_plans"
    __table_args__ = (UniqueConstraint("project_id", "version", name="uq_project_plan_version"),)

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    project: Mapped["ProjectORM"] = relationship("ProjectORM", back_populates="plans")
    tasks: Mapped[list["PlanTaskORM"]] = relationship(
        "PlanTaskORM",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    dependencies: Mapped[list["PlanDependencyORM"]] = relationship(
        "PlanDependencyORM",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PlanTaskORM(Base, UUIDPrimaryKeyMixin):
    """Task snapshot within a versioned plan."""

    __tablename__ = "plan_tasks"
    __table_args__ = (UniqueConstraint("plan_id", "task_id", name="uq_plan_task_id"),)

    plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("project_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Stored statuses: TODO, IN_PROGRESS, BLOCKED, COMPLETED. OVERDUE is derived, never stored!
    status: Mapped[str] = mapped_column(String(50), default="TODO", nullable=False)
    estimated_hours: Mapped[float] = mapped_column(Float, default=8.0, nullable=False)
    assigned_to_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    plan: Mapped["ProjectPlanORM"] = relationship("ProjectPlanORM", back_populates="tasks")


class PlanDependencyORM(Base, UUIDPrimaryKeyMixin):
    """Precedence dependency relationship within a versioned plan snapshot."""

    __tablename__ = "plan_dependencies"

    plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("project_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    predecessor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    successor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    dep_type: Mapped[str] = mapped_column(String(50), default="FINISH_TO_START", nullable=False)
    lag_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    plan: Mapped["ProjectPlanORM"] = relationship("ProjectPlanORM", back_populates="dependencies")
