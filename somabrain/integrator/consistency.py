"""Module consistency."""

from __future__ import annotations

from typing import Dict, Optional


# Simple feasibility table mapping agent intent -> allowed next actions
_ALLOWED: Dict[str, set[str]] = {
    "browse": {"search", "quote"},
    "purchase": {"checkout", "cancel", "quote"},
    "support": {"cancel", "quote"},
}


def consistency_score(
    agent_posterior: Dict[str, object] | None,
    action_posterior: Dict[str, object] | None,
) -> Optional[float]:
    """Return 1.0 if action is feasible for intent, 0.0 if infeasible, None if unknown.

    - agent_posterior is expected to contain key "intent" (str)
    - action_posterior is expected to contain key "next_action" (str)
    """

    if not isinstance(agent_posterior, dict) or not isinstance(action_posterior, dict):
        return None
    try:
        intent = str(agent_posterior.get("intent") or "").strip().lower()
        action = str(action_posterior.get("next_action") or "").strip().lower()
    except Exception:
        return None
    if not intent or not action:
        return None
    allowed = _ALLOWED.get(intent)
    if allowed is None:
        return None
    return 1.0 if action in allowed else 0.0
