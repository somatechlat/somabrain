"""Pydantic schemas for the Sleep System endpoints.

Both the utility and cognitive sleep APIs share a minimal request model that
specifies the desired target state and an optional TTL (in seconds) for auto‑
wake. The response models are defined directly in the endpoint functions to
avoid circular imports.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, validator

from somabrain.sleep import SleepState


class SleepTargetState(str, Enum):
    """Sleeptargetstate class implementation."""

    ACTIVE = "active"
    LIGHT = "light"
    DEEP = "deep"
    FREEZE = "freeze"


class SleepRequest(BaseModel):
    """Request model for ``POST /api/util/sleep``.

    * ``target_state`` – Desired sleep state (must be one of the ``SleepState``
      enumeration values).
    * ``ttl_seconds`` – Optional time‑to‑live after which the system should
      automatically revert to ``ACTIVE``. Must be a positive integer if
      provided.
    """

    target_state: SleepTargetState = Field(..., description="Desired sleep state")
    ttl_seconds: Optional[int] = Field(
        None,
        ge=1,
        description="Optional TTL in seconds after which the state auto‑resets to ACTIVE",
    )
    # ``async`` flag – when true the endpoint returns immediately and the actual
    # sleep is performed in the background. This satisfies SRS requirement U‑3.
    async_mode: bool = Field(
        False,
        description="If true, perform the sleep asynchronously (non‑blocking)",
    )
    # Optional trace identifier for observability pipelines (SRS U‑1).
    trace_id: Optional[str] = Field(
        None,
        description="Arbitrary trace identifier propagated to logs/metrics",
    )

    @validator("target_state")
    def _validate_target(cls, v: SleepTargetState) -> SleepTargetState:
        # Ensure the value maps to the internal SleepState enum.
        """Execute validate target.

        Args:
            v: The v.
        """

        if v.value not in {s.value for s in SleepState}:
            raise ValueError(f"Invalid sleep state: {v}")
        return v
