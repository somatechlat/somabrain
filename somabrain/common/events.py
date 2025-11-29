from __future__ import annotations

import time
from typing import Dict


def build_next_event(
    domain: str, tenant: str, confidence: float, predicted_state: str
) -> Dict[str, object]:
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    regret = max(0.0, min(1.0, 1.0 - float(confidence)))
    return {
        "frame_id": f"{domain}:{ts}",
        "tenant": tenant,
        "predicted_state": predicted_state,
        "confidence": float(confidence),
        "regret": regret,
        "ts": ts,
    }


def compute_regret_from_confidence(confidence: float) -> float:
    """Compute regret as 1 - confidence, clamped to [0,1].

    This is used by drift detection to form a simple regret proxy.
    """
    try:
        return max(0.0, min(1.0, 1.0 - float(confidence)))
    except Exception as exc: raise
        return 1.0
