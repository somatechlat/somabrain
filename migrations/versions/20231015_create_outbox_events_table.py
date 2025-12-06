"""Create outbox_events table

Revision ID: cf8b36c30d81
Revises: 0001_context_feedback
Create Date: 2025-10-15 14:00:00.000000
"""

from __future__ import annotations
from typing import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "cf8b36c30d81"
down_revision: str | None = "0001_context_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        # New events start as pending so the sync loop knows they need processing.
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("retries", sa.Integer(), nullable=True),
        sa.Column("dedupe_key", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key"),
    )


def downgrade() -> None:
    op.drop_table("outbox_events")
