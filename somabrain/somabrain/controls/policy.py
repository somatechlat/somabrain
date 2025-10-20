from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class PolicyDecision:
    decision: str  # allow|deny|review
    reason: str
    hints: Dict[str, Any]


class PolicyEngine:
    def __init__(self, safety_threshold: float = 0.9):
        self.safety_threshold = float(safety_threshold)

    def _kill_switch(self) -> bool:
        return str(os.getenv("SOMABRAIN_KILL_SWITCH", "")).lower() in ("1", "true", "on", "yes")

    def evaluate(self, ctx: Dict[str, Any]) -> PolicyDecision:
        # Global kill switch
        if self._kill_switch():
            return PolicyDecision("deny", "kill_switch", {"operator_pause": True})
        # Human override header triggers review
        if str(ctx.get("headers", {}).get("x-soma-review", "")).lower() in ("1", "true"):
            return PolicyDecision("review", "human_review", {"require_human": True})
        # Simple safety gate: deny high-risk writes to memory unless provenance present
        path = str(ctx.get("path", ""))
        method = str(ctx.get("method", "")).upper()
        headers = {k.lower(): str(v) for k, v in (ctx.get("headers") or {}).items()}
        provenance = headers.get("x-provenance", "")
        if path.startswith("/remember") or (path.startswith("/act") and method == "POST"):
            # If middleware validated HMAC, rely on it; otherwise require header presence
            prov_valid = ctx.get("provenance_valid")
            prov_strict = bool(ctx.get("provenance_strict", False))
            if prov_valid is False:
                return PolicyDecision("deny" if prov_strict else "review", "invalid_provenance", {"require_provenance": True})
            if prov_valid is None and not provenance:
                return PolicyDecision("deny" if prov_strict else "review", "missing_provenance", {"require_provenance": True})
        return PolicyDecision("allow", "ok", {})
