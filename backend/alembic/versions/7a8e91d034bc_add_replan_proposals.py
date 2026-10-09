"""Add replan_proposals table

Revision ID: 7a8e91d034bc
Revises: 48c9031ef012
Create Date: 2026-10-09 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7a8e91d034bc"
down_revision: str | Sequence[str] | None = "48c9031ef012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema to add replan_proposals table."""
    op.create_table(
        "replan_proposals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("baseline_version", sa.Integer(), nullable=False),
        sa.Column("candidate_plan", sa.JSON(), nullable=False),
        sa.Column("risks_addressed", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("created_by", sa.String(length=100), nullable=False, server_default="engine"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_by", sa.String(length=100), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_replan_proposals_project_id"),
        "replan_proposals",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_replan_proposals_baseline_version"),
        "replan_proposals",
        ["baseline_version"],
        unique=False,
    )
    op.create_index(
        op.f("ix_replan_proposals_status"),
        "replan_proposals",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema to drop replan_proposals table."""
    op.drop_index(
        op.f("ix_replan_proposals_status"),
        table_name="replan_proposals",
    )
    op.drop_index(
        op.f("ix_replan_proposals_baseline_version"),
        table_name="replan_proposals",
    )
    op.drop_index(
        op.f("ix_replan_proposals_project_id"),
        table_name="replan_proposals",
    )
    op.drop_table("replan_proposals")
