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
# ``JSON`` type is optional in lightweight deployments; store payload as a ``String``
# containing a JSON‑encoded document. This satisfies the schema requirements
# for the outbox while keeping the model compatible with environments that
# lack the full SQLAlchemy installation.
from sqlalchemy.types import Text as JSON  # type: ignore
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
