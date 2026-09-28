"""
Oak schemas - Options Architecture Kit request/response models.
"""

from __future__ import annotations

from pydantic import BaseModel


class OakOptionCreateRequest(BaseModel):
    """Request payload for creating a new Oak option."""

    option_id: str | None = None
    payload: str  # base64 encoded bytes


class OakPlanSuggestResponse(BaseModel):
    """Response model for Oak planning results."""

    plan: list[str]
