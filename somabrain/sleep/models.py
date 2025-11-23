"""SQLAlchemy model for per‑tenant sleep state persistence.

The migration ``20251112_create_sleep_states`` creates the corresponding table.
This model is used by the Sleep System endpoints to store the current and
target sleep states, optional TTL for auto‑wake, and additional parameters.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy import Column, String, DateTime, Text, func

from somabrain.storage.db import Base


class TenantSleepState(Base):
    """Persisted sleep state for a tenant.

    Columns:
        tenant_id               Primary key – the tenant identifier.
        current_state           The state the system is currently in.
        target_state            The state the tenant requests (may differ until
                                the transition is applied).
        ttl                     Optional datetime after which the state should
                                automatically revert to ``ACTIVE``.
        scheduled_wake          Cached datetime when the auto‑wake should fire.
        circuit_breaker_state   Placeholder for future circuit‑breaker status.
        parameters_json         JSON‑encoded ``SleepParameters`` for debugging.
        updated_at              Timestamp of last update (auto‑managed).
    """

    __tablename__ = "tenant_sleep_states"

    tenant_id = Column(String(255), primary_key=True, nullable=False)
    current_state = Column(String(50), nullable=False, default="active")
    target_state = Column(String(50), nullable=False, default="active")
    ttl = Column(DateTime(timezone=True), nullable=True)
    scheduled_wake = Column(DateTime(timezone=True), nullable=True)
    circuit_breaker_state = Column(String(50), nullable=False, default="closed")
    parameters_json = Column(Text, nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def set_parameters(self, params: dict[str, Any] | None) -> None:
        """Store a JSON representation of sleep parameters.

        ``params`` may be ``None`` – in that case the column is cleared.
        """
        if params is None:
            self.parameters_json = None
        else:
            try:
                self.parameters_json = json.dumps(params, sort_keys=True)
            except Exception:
                # Fallback to string representation if JSON fails.
                self.parameters_json = str(params)

    def get_parameters(self) -> Optional[dict[str, Any]]:
        """Return the stored parameters as a dict, or ``None`` if missing."""
        if not self.parameters_json:
            return None
        try:
            return json.loads(self.parameters_json)
        except Exception:
            return None

    def __repr__(self) -> str:
        return (
            f"<TenantSleepState(tenant_id={self.tenant_id}, current={self.current_state}, "
            f"target={self.target_state}, ttl={self.ttl}, scheduled_wake={self.scheduled_wake})>"
        )
