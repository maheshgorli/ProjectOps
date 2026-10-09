"""Add task_execution_states table

Revision ID: 48c9031ef012
Revises: 31a789c201ab
Create Date: 2026-10-09 12:35:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "48c9031ef012"
down_revision: str | Sequence[str] | None = "31a789c201ab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema to add mutable task_execution_states."""
    op.create_table(
        "task_execution_states",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="TODO"),
        sa.Column("actual_start", sa.Date(), nullable=True),
        sa.Column("actual_finish", sa.Date(), nullable=True),
        sa.Column("actual_hours", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("percent_complete", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=False, server_default="system"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "task_id", name="uq_task_execution_project_task"),
    )
    op.create_index(
        op.f("ix_task_execution_states_project_id"),
        "task_execution_states",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_task_execution_states_task_id"),
        "task_execution_states",
        ["task_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema to drop task_execution_states."""
    op.drop_index(
        op.f("ix_task_execution_states_task_id"),
        table_name="task_execution_states",
    )
    op.drop_index(
        op.f("ix_task_execution_states_project_id"),
        table_name="task_execution_states",
    )
    op.drop_table("task_execution_states")
