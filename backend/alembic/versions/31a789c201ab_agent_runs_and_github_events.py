"""Add agent_runs and github_events tables

Revision ID: 31a789c201ab
Revises: 204a33832988
Create Date: 2026-10-07 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "31a789c201ab"
down_revision: str | Sequence[str] | None = "204a33832988"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema to add agent_runs and github_events."""
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("loop_stage", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("triggered_by", sa.String(length=100), nullable=False),
        sa.Column("sequence_num", sa.BigInteger(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_runs_project_id"), "agent_runs", ["project_id"], unique=False)
    op.create_index(
        op.f("ix_agent_runs_sequence_num"), "agent_runs", ["sequence_num"], unique=False
    )
    op.create_index(op.f("ix_agent_runs_recorded_at"), "agent_runs", ["recorded_at"], unique=False)

    op.create_table(
        "github_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("sender", sa.String(length=255), nullable=False),
        sa.Column("ref", sa.String(length=255), nullable=True),
        sa.Column("commit_sha", sa.String(length=100), nullable=True),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("raw_payload_json", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_github_events_project_id"), "github_events", ["project_id"], unique=False
    )
    op.create_index(
        op.f("ix_github_events_event_type"), "github_events", ["event_type"], unique=False
    )
    op.create_index(
        op.f("ix_github_events_recorded_at"), "github_events", ["recorded_at"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_github_events_recorded_at"), table_name="github_events")
    op.drop_index(op.f("ix_github_events_event_type"), table_name="github_events")
    op.drop_index(op.f("ix_github_events_project_id"), table_name="github_events")
    op.drop_table("github_events")

    op.drop_index(op.f("ix_agent_runs_recorded_at"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_loop_stage"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_project_id"), table_name="agent_runs")
    op.drop_table("agent_runs")
