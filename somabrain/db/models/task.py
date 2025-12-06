"""
SQLAlchemy model for the Dynamic Task Registry.
Stores task definitions, schemas, and configuration for agent workflows.
"""

from __future__ import annotations

import datetime as dt
from sqlalchemy import (
    Column,
    String,
    DateTime,
    JSON,
    Integer,
    func,
)
from somabrain.storage.db import Base


class TaskRegistry(Base):
    __tablename__ = "task_registry"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), unique=True, nullable=False, index=True)
    description = Column(String(512), nullable=True)

    # JSON Schema defining the input parameters for this task
    schema = Column(JSON, nullable=False)

    # Version string (e.g., "1.0.0")
    version = Column(String(32), nullable=False, default="1.0.0")

    # Rate limiting configuration
    rate_limit_per_min = Column(Integer, nullable=True, default=60)

    # OPA policy tags or required permissions
    policy_tags = Column(JSON, nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<TaskRegistry(id='{self.id}', name='{self.name}', version='{self.version}')>"
