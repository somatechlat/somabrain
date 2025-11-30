from __future__ import annotations
from typing import Sequence
from alembic import op
import sqlalchemy as sa

"""Phase 1 Outbox Enhancements for Idempotency and Performance

Revision ID: phase1_outbox_enhancements
Revises: b5c9f9a3d1ab
Create Date: 2025-11-15 10:30:00.000000

"""


# revision identifiers, used by Alembic.
revision: str = "phase1_outbox_enhancements"
down_revision: str | None = "b5c9f9a3d1ab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply Phase 1 enhancements to outbox_events table."""

    # Add index for improved dedupe_key lookup performance
    op.create_index(
        "ix_outbox_dedupe_key_tenant",
        "outbox_events",
        ["dedupe_key", "tenant_id"],
        unique=False,  # Not unique since we already have the composite unique constraint
    )

    # Add index for status and created_at queries (complements existing status_tenant_created index)
    op.create_index(
        "ix_outbox_status_created",
        "outbox_events",
        ["status", "created_at"],
    )

    # Add index for topic-based queries
    op.create_index(
        "ix_outbox_topic_status",
        "outbox_events",
        ["topic", "status"],
    )

    # Add index for retry management
    op.create_index(
        "ix_outbox_retries_status",
        "outbox_events",
        ["retries", "status"],
    )

    # Add index for tenant and topic queries
    op.create_index(
        "ix_outbox_tenant_topic",
        "outbox_events",
        ["tenant_id", "topic"],
    )

    # Add composite index for efficient failed event queries
    op.create_index(
        "ix_outbox_failed_tenant_created",
        "outbox_events",
        ["status", "tenant_id", "created_at"],
        # This will be used with postgres partial index for status='failed'
        postgresql_where=sa.text("status = 'failed'"),
    )


def downgrade() -> None:
    """Remove Phase 1 enhancements from outbox_events table."""

    # Drop all added indices
    op.drop_index(
        "ix_outbox_failed_tenant_created",
        table_name="outbox_events",
    )

    op.drop_index(
        "ix_outbox_tenant_topic",
        table_name="outbox_events",
    )

    op.drop_index(
        "ix_outbox_retries_status",
        table_name="outbox_events",
    )

    op.drop_index(
        "ix_outbox_topic_status",
        table_name="outbox_events",
    )

    op.drop_index(
        "ix_outbox_status_created",
        table_name="outbox_events",
    )

    op.drop_index(
        "ix_outbox_dedupe_key_tenant",
        table_name="outbox_events",
    )
