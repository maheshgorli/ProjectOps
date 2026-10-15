"""Add login_audits table for persistent login activity auditing.

Revision ID: d1e2f3a4b5c6
Revises: c4b182d491bc
Create Date: 2026-10-15 10:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: str | Sequence[str] | None = "c4b182d491bc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create login_audits table."""
    op.create_table(
        "login_audits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("ip_address", sa.String(length=100), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("failure_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_login_audits_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_audits")),
    )
    op.create_index(
        op.f("ix_login_audits_user_id"),
        "login_audits",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_login_audits_email"),
        "login_audits",
        ["email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_login_audits_created_at"),
        "login_audits",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop login_audits table."""
    op.drop_index(op.f("ix_login_audits_created_at"), table_name="login_audits")
    op.drop_index(op.f("ix_login_audits_email"), table_name="login_audits")
    op.drop_index(op.f("ix_login_audits_user_id"), table_name="login_audits")
    op.drop_table("login_audits")
