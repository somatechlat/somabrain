"""
Oak schemas - Options Architecture Kit request/response models.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class OakOptionCreateRequest(BaseModel):
    """Request payload for creating a new Oak option."""

    option_id: Optional[str] = None
    payload: str  # base64 encoded bytes


class OakPlanSuggestResponse(BaseModel):
    """Response model for Oak planning results."""

    plan: List[str]
