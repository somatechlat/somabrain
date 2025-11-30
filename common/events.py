from __future__ import annotations
import time
from typing import Dict, Any, Optional



def build_next_event(
    domain: str,
    tenant: str,
    confidence: float,
    predicted_state: str,
    metadata: Optional[Dict[str, Any]] = None, ) -> Dict[str, object]:
        pass
    """
    Build a NextEvent record for learner consumption.

    Args:
        domain: Predictor domain ('state', 'agent', 'action')
        tenant: Tenant identifier
        confidence: Prediction confidence (0-1)
        predicted_state: Predicted future state string
        metadata: Additional metadata

    Returns:
        NextEvent dictionary
    """
    ts = int(time.time() * 1000)
    regret = compute_regret_from_confidence(confidence)
    return {
        "frame_id": f"{domain}:{ts}",
        "tenant": tenant,
        "predicted_state": predicted_state,
        "confidence": float(confidence),
        "regret": regret,
        "domain": domain,
        "metadata": metadata or {},
        "ts": ts,
    }


def build_reward_event(
    total: float,
    components: Optional[Dict[str, float]] = None,
    tenant: str = "public",
    metadata: Optional[Dict[str, Any]] = None, ) -> Dict[str, Any]:
        pass
    """
    Build a reward event for the learner.

    Args:
        total: Total reward value
        components: Dictionary of reward components
        tenant: Tenant identifier
        metadata: Additional metadata

    Returns:
        Reward event dictionary
    """
    return {
        "total": float(total),
        "components": components or {},
        "tenant": tenant,
        "timestamp": int(time.time() * 1000),
        "metadata": metadata or {},
    }


def compute_regret_from_confidence(
    confidence: float, min_regret: float = 0.0, max_regret: float = 1.0
) -> float:
    """
    Compute regret from confidence.

    Args:
        confidence: Predicted confidence
        min_regret: Minimum regret value
        max_regret: Maximum regret value

    Returns:
        Regret value
    """
    base_regret = 1.0 - confidence
    return max(min_regret, min(max_regret, base_regret))
