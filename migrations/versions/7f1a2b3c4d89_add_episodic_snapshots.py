"""Add episodic_snapshots table

Revision ID: 7f1a2b3c4d89
Revises: 3c1a2b4c5d67
Create Date: 2025-10-26 14:20:00.000000

"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7f1a2b3c4d89"
down_revision: str | None = "cf8b36c30d81"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "episodic_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.String(length=128), nullable=True),
        sa.Column("namespace", sa.String(length=64), nullable=True),
        sa.Column("key", sa.String(length=256), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("policy_tags", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_episodic_snapshots_tenant_created",
        "episodic_snapshots",
        ["tenant_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_episodic_snapshots_tenant_created", table_name="episodic_snapshots"
    )
    op.drop_table("episodic_snapshots")
