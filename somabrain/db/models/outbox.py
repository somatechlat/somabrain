"""
SQLAlchemy model for the transactional outbox.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    func,
    UniqueConstraint,
    Index,
)

# SQLAlchemy JSON type import with fallback for older versions.
# Type ignores: JSON type location varies across SQLAlchemy versions (1.x vs 2.x).
# This pattern ensures compatibility while maintaining type safety at runtime.
try:  # Prefer native JSON/JSONB when SQLAlchemy is available
    from sqlalchemy import JSON  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - compatibility fallback
    from sqlalchemy.types import Text as JSON  # type: ignore[attr-defined]
from somabrain.storage.db import Base


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "dedupe_key", name="uq_outbox_tenant_dedupe"),
        Index("ix_outbox_status_tenant_created", "status", "tenant_id", "created_at"),
    )

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=func.now())
    topic = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String, default="pending")  # pending, sent, failed
    retries = Column(Integer, default=0)
    dedupe_key = Column(String, nullable=False)
    tenant_id = Column(String, nullable=True)
    last_error = Column(String, nullable=True)

    def __repr__(self):
        return (
            f"<OutboxEvent(id={self.id}, topic='{self.topic}', status='{self.status}')>"
        )
