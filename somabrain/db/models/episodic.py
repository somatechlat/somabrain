from __future__ import annotations
from sqlalchemy import (
from somabrain.storage.db import Base

"""
SQLAlchemy model for episodic memory snapshots.
"""


    Column,
    Integer,
    String,
    DateTime,
    JSON,
    func, )


class EpisodicSnapshot(Base):
    __tablename__ = "episodic_snapshots"

    id = Column(Integer, primary_key=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    tenant_id = Column(String, nullable=True)
    namespace = Column(String, nullable=True)
    key = Column(String, nullable=False)
    value = Column(JSON, nullable=False)
    tags = Column(JSON, nullable=True)
    policy_tags = Column(JSON, nullable=True)

def __repr__(self) -> str:
        return f"<EpisodicSnapshot(id={self.id}, tenant_id={self.tenant_id}, key='{self.key}')>"
