"""ORM model for server-side Replan Proposals (Core Principle 4 & P0-1 fix)."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.project import ProjectORM


class ReplanProposalORM(Base, UUIDPrimaryKeyMixin):
    """
    Server-stored replan proposal snapshot.

    Enforces:
    - Rule 4: Replanning requires human approval. Never silently change a plan.
    - P0-1 Fix: Approval operates only on pre-stored, server-generated proposal snapshots.
    """

    __tablename__ = "replan_proposals"

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    baseline_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    candidate_plan: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    risks_addressed: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    explanation: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING",
        nullable=False,
        index=True,
    )
    created_by: Mapped[str] = mapped_column(
        String(100),
        default="engine",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    decided_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    rationale: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    project: Mapped["ProjectORM"] = relationship(
        "ProjectORM", back_populates="replan_proposals"
    )
