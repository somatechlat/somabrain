"""Degradation Manager for SomaBrain.

Manages SB degradation state when SFM is unavailable.
Per Requirements E1.1-E1.5:
- Tracks degraded state per tenant
- Triggers alerts when degraded > 5 minutes
- Enables WM-only mode during degradation
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class DegradationState:
    """State for a single tenant's degradation."""

    degraded_since: Optional[float] = None
    alert_triggered: bool = False
    last_check: float = field(default_factory=time.time)


class DegradationManager:
    """Manage SB degradation state when SFM is unavailable.

    Per Requirements E1.1-E1.5:
    - E1.1: When SFM unreachable, SB continues with WM-only (degraded=true)
    - E1.2: When degraded, all writes queue to outbox for later replay
    - E1.3: When SFM recovers, outbox replays without duplicates
    - E1.4: When replay completes, pending_count returns to zero
    - E1.5: When degraded > 5 minutes, alert is triggered via metrics
    """

    def __init__(
        self,
        circuit_breaker: Optional["CircuitBreaker"] = None,
        alert_threshold_seconds: float = 300.0,  # 5 minutes per E1.5
    ):
        """Initialize DegradationManager.

        Args:
            circuit_breaker: Optional circuit breaker for checking open state
            alert_threshold_seconds: Time before triggering alert (default 5 min)
        """
        self._circuit_breaker = circuit_breaker
        self._alert_threshold_seconds = alert_threshold_seconds
        self._tenant_states: Dict[str, DegradationState] = {}

    def _get_state(self, tenant: str) -> DegradationState:
        """Get or create state for tenant."""
        if tenant not in self._tenant_states:
            self._tenant_states[tenant] = DegradationState()
        return self._tenant_states[tenant]

    def is_degraded(self, tenant: str) -> bool:
        """Check if tenant is in degraded mode.

        Returns True if:
        - Circuit breaker is open for this tenant, OR
        - Tenant has been marked as degraded

        Per E1.1: When SFM unreachable, return True.
        """
        # Check circuit breaker first
        if self._circuit_breaker is not None:
            try:
                if self._circuit_breaker.is_open(tenant):
                    self._mark_degraded(tenant)
                    return True
            except Exception:
                pass

        # Check local state
        state = self._get_state(tenant)
        return state.degraded_since is not None

    def _mark_degraded(self, tenant: str) -> None:
        """Mark tenant as degraded (internal)."""
        state = self._get_state(tenant)
        if state.degraded_since is None:
            state.degraded_since = time.time()
            state.alert_triggered = False

    def mark_degraded(self, tenant: str) -> None:
        """Explicitly mark tenant as degraded.

        Called when SFM operations fail.
        """
        self._mark_degraded(tenant)

    def mark_recovered(self, tenant: str) -> None:
        """Mark tenant as recovered from degradation.

        Called when SFM operations succeed after degradation.
        Per E1.3: When SFM recovers, clear degraded state.
        """
        state = self._get_state(tenant)
        if state.degraded_since is not None:
            # Log recovery
            duration = time.time() - state.degraded_since
            try:
                from structlog import get_logger

                logger = get_logger()
                logger.info(
                    "Tenant recovered from degraded mode",
                    tenant=tenant,
                    degraded_duration_seconds=duration,
                )
            except Exception:
                pass

        state.degraded_since = None
        state.alert_triggered = False

    def check_alert(self, tenant: str) -> bool:
        """Check if degraded > 5 minutes and should trigger alert.

        Per E1.5: When degraded mode exceeds 5 minutes, alert SHALL be triggered.

        Returns:
            True if alert should be triggered (first time only)
        """
        if not self.is_degraded(tenant):
            return False

        state = self._get_state(tenant)
        if state.degraded_since is None:
            return False

        # Already triggered?
        if state.alert_triggered:
            return False

        # Check duration
        duration = time.time() - state.degraded_since
        if duration > self._alert_threshold_seconds:
            state.alert_triggered = True
            # Record metric
            try:
                from prometheus_client import Counter

                DEGRADATION_ALERT = Counter(
                    "sb_degradation_alert_total",
                    "Degradation alerts triggered",
                    ["tenant"],
                )
                DEGRADATION_ALERT.labels(tenant=tenant).inc()
            except Exception:
                pass
            return True

        return False

    def get_degraded_duration(self, tenant: str) -> Optional[float]:
        """Get how long tenant has been degraded in seconds.

        Returns None if not degraded.
        """
        state = self._get_state(tenant)
        if state.degraded_since is None:
            return None
        return time.time() - state.degraded_since

    def get_all_degraded_tenants(self) -> Dict[str, float]:
        """Get all degraded tenants and their durations.

        Returns:
            Dict mapping tenant ID to degradation duration in seconds
        """
        result = {}
        for tenant, state in self._tenant_states.items():
            if state.degraded_since is not None:
                result[tenant] = time.time() - state.degraded_since
        return result


# Global singleton instance
_degradation_manager: Optional[DegradationManager] = None


def get_degradation_manager() -> DegradationManager:
    """Get the global DegradationManager instance."""
    global _degradation_manager
    if _degradation_manager is None:
        # Try to get circuit breaker
        circuit_breaker = None
        try:
            from somabrain.infrastructure.circuit_breaker import get_circuit_breaker

            circuit_breaker = get_circuit_breaker()
        except Exception:
            pass

        _degradation_manager = DegradationManager(circuit_breaker=circuit_breaker)
    return _degradation_manager


def reset_degradation_manager() -> None:
    """Reset the global DegradationManager (for testing)."""
    global _degradation_manager
    _degradation_manager = None
