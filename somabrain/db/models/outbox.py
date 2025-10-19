"""
SQLAlchemy model for the transactional outbox.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    JSON,
    func,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=func.now())
    topic = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String, default="pending")  # pending, sent, failed
    retries = Column(Integer, default=0)
    dedupe_key = Column(String, unique=True, nullable=False)
    tenant_id = Column(String, nullable=True)
    last_error = Column(String, nullable=True)

    def __repr__(self):
        return (
            f"<OutboxEvent(id={self.id}, topic='{self.topic}', status='{self.status}')>"
        )
