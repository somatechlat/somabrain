"""Create tenant sleep states table.

Revision ID: 20251112_create_sleep_states
Revises: cf8b36c30d81
Create Date: 2025-11-12 14:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251112_create_sleep_states"
down_revision = "cf8b36c30d81"
branch_labels = None
depends_on = None


def upgrade():
    """Create tenant_sleep_states table."""
    op.create_table(
        "tenant_sleep_states",
        sa.Column("tenant_id", sa.String(255), primary_key=True, nullable=False),
        sa.Column("current_state", sa.String(50), nullable=False, default="active"),
        sa.Column("target_state", sa.String(50), nullable=False, default="active"),
        sa.Column("ttl", sa.DateTime, nullable=True),
        sa.Column("scheduled_wake", sa.DateTime, nullable=True),
        sa.Column(
            "circuit_breaker_state", sa.String(50), nullable=False, default="closed"
        ),
        sa.Column("parameters_json", sa.Text, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Index("idx_sleep_tenant_ttl", "tenant_id", "ttl"),
        sa.Index("idx_sleep_scheduled_wake", "scheduled_wake"),
        sa.Index("idx_sleep_updated", "updated_at"),
    )


def downgrade():
    """Drop tenant_sleep_states table."""
    op.drop_table("tenant_sleep_states")
