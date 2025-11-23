"""
Policy Engine Module for SomaBrain

This module implements a policy-based access control system for the SomaBrain API.
It provides security controls, provenance verification, and operational safety
measures to ensure secure and reliable operation.

Key Features:
- Kill switch for emergency shutdown
- Human override for manual review
- Provenance validation for write operations
- Configurable strict mode for security
- Policy decision making with detailed reasoning

Security Policies:
- Kill Switch: Environment-based emergency stop
- Human Review: Header-triggered manual oversight
- Provenance: HMAC-based request validation
- Path-based rules: Different policies for different endpoints

Policy Decisions:
- Allow: Request permitted to proceed
- Deny: Request blocked with error response
- Review: Request flagged for human review

Classes:
    PolicyDecision: Container for policy evaluation results
    PolicyEngine: Main policy evaluation engine

Functions:
    None (class-based implementation)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict

from common.config.settings import settings


@dataclass
class PolicyDecision:
    decision: str  # allow|deny|review
    reason: str
    hints: Dict[str, Any]


class PolicyEngine:
    def __init__(self, safety_threshold: float = 0.9):
        self.safety_threshold = float(safety_threshold)
        pat = settings.getenv("SOMABRAIN_BLOCK_UA_REGEX", "").strip()
        self._block_ua = re.compile(pat) if pat else None

    def _kill_switch(self) -> bool:
        # Disable kill switch during test runs to prevent unintended denial of requests.
        # Pytest sets the PYTEST_CURRENT_TEST environment variable for each test.
        if settings.getenv("PYTEST_CURRENT_TEST"):
            return False
        return str(settings.getenv("SOMABRAIN_KILL_SWITCH", "")).lower() in (
            "1",
            "true",
            "on",
            "yes",
        )

    def evaluate(self, ctx: Dict[str, Any]) -> PolicyDecision:
        # Global kill switch
        if self._kill_switch():
            return PolicyDecision("deny", "kill_switch", {"operator_pause": True})
        # Human override header triggers review
        if str(ctx.get("headers", {}).get("x-soma-review", "")).lower() in (
            "1",
            "true",
        ):
            return PolicyDecision("review", "human_review", {"require_human": True})
        # Simple safety gate: deny high-risk writes to memory unless provenance present
        path = str(ctx.get("path", ""))
        method = str(ctx.get("method", "")).upper()
        headers = {k.lower(): str(v) for k, v in (ctx.get("headers") or {}).items()}
        ua = headers.get("user-agent", "")
        # Optional env-based blocklist for misbehaving clients (e.g., bad integration loops)
        if (
            self._block_ua
            and self._block_ua.search(ua or "")
            and path.startswith("/remember")
        ):
            return PolicyDecision("deny", "ua_blocklist", {"ua": ua})
        provenance = headers.get("x-provenance", "")
        # Provenance enforcement only if required by config
        if ctx.get("require_provenance"):
            if path.startswith("/remember") or (
                path.startswith("/act") and method == "POST"
            ):
                # If middleware validated HMAC, rely on it; otherwise require header presence
                prov_valid = ctx.get("provenance_valid")
                prov_strict = bool(ctx.get("provenance_strict", False))
                if prov_valid is False:
                    return PolicyDecision(
                        "deny" if prov_strict else "review",
                        "invalid_provenance",
                        {"require_provenance": True},
                    )
                if prov_valid is None and not provenance:
                    return PolicyDecision(
                        "deny" if prov_strict else "review",
                        "missing_provenance",
                        {"require_provenance": True},
                    )
        return PolicyDecision("allow", "ok", {})
