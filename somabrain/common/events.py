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
