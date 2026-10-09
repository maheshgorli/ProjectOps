"""ORM models for Project and Member entities."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.execution import TaskExecutionStateORM
    from backend.app.models.plan import ProjectPlanORM
    from backend.app.models.proposal import ReplanProposalORM


class ProjectORM(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Project entity table."""

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    members: Mapped[list["MemberORM"]] = relationship(
        "MemberORM",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    plans: Mapped[list["ProjectPlanORM"]] = relationship(
        "ProjectPlanORM",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    task_execution_states: Mapped[list["TaskExecutionStateORM"]] = relationship(
        "TaskExecutionStateORM",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    replan_proposals: Mapped[list["ReplanProposalORM"]] = relationship(
        "ReplanProposalORM",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class MemberORM(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Team member assigned to a project."""

    __tablename__ = "members"

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(100), default="engineer", nullable=False)
    daily_capacity_hours: Mapped[float] = mapped_column(Float, default=8.0, nullable=False)

    project: Mapped["ProjectORM"] = relationship("ProjectORM", back_populates="members")
