"""Context route validation helpers.

Extracted from api/context_route.py per monolithic-decomposition spec.
Provides payload validation functions for evaluate and feedback endpoints.
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Optional

from ninja.errors import HttpError

from somabrain.api.schemas.context import MemoryItem
from somabrain.context.builder import ContextBundle


def validate_evaluate_response(
    bundle: ContextBundle,
    memories: List[MemoryItem],
    prompt: str,
    residual_vector: List[float],
    working_memory: List[Dict],
) -> None:
    """Validate evaluate response payload sizes.

    Args:
        bundle: The context bundle
        memories: List of memory items
        prompt: The generated prompt
        residual_vector: The residual vector
        working_memory: Working memory snapshot

    Raises:
        HTTPException: If any validation fails
    """
    if len(memories) > 20:
        raise HttpError(400, "memories exceeds 20 items")
    if len(prompt) > 4096:
        raise HttpError(
            400, "prompt length exceeds 4096 characters"
        )
    if len(residual_vector) > 2048:
        raise HttpError(
            400, "residual vector exceeds 2048 floats"
        )
    if len(working_memory) > 10:
        raise HttpError(400, "working memory exceeds 10 items")


def validate_evaluate_response_size(response_dict: Dict[str, Any]) -> None:
    """Validate total response size.

    Args:
        response_dict: The response dictionary

    Raises:
        HTTPException: If response exceeds 128 KB
    """
    if len(json.dumps(response_dict)) > 128 * 1024:
        raise HttpError(400, "response size exceeds 128 KB")


def validate_feedback_fields(
    session_id: Optional[str],
    query: Optional[str],
    prompt: Optional[str],
    response_text: Optional[str],
) -> None:
    """Validate feedback request field lengths.

    Args:
        session_id: Session identifier
        query: Query string
        prompt: Prompt string
        response_text: Response text

    Raises:
        HTTPException: If any field exceeds 1024 characters
    """
    for field in [session_id, query, prompt, response_text]:
        if field and len(field) > 1024:
            raise HttpError(
                400, "input field exceeds 1024 characters"
            )


def validate_feedback_metadata(metadata: Optional[Dict[str, Any]]) -> None:
    """Validate feedback metadata size.

    Args:
        metadata: Optional metadata dictionary

    Raises:
        HTTPException: If metadata is invalid or exceeds 8 KB
    """
    if metadata is not None:
        try:
            encoded_metadata = json.dumps(metadata)
        except Exception:
            raise HttpError(400, "invalid metadata encoding")
        if len(encoded_metadata) > 8 * 1024:
            raise HttpError(400, "metadata exceeds 8 KB")


def validate_feedback_reward_utility(
    reward: Optional[float],
    utility: Optional[float],
) -> tuple[float, float]:
    """Validate and parse reward and utility values.

    Args:
        reward: Reward value
        utility: Utility value

    Returns:
        Tuple of (reward_val, utility_val)

    Raises:
        HTTPException: If values are missing, non-numeric, or out of bounds
    """
    if reward is None or utility is None:
        raise HttpError(400, "reward and utility are required")

    try:
        reward_val = float(reward)
    except Exception:
        raise HttpError(400, "reward must be numeric")

    if not math.isfinite(reward_val) or reward_val < -10_000 or reward_val > 10_000:
        raise HttpError(400, "reward out of bounds")

    try:
        util_val = float(utility)
    except Exception:
        raise HttpError(400, "utility must be numeric")

    if not math.isfinite(util_val) or util_val < -10_000 or util_val > 10_000:
        raise HttpError(400, "utility out of bounds")

    return reward_val, util_val