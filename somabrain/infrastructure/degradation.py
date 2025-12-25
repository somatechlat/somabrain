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
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from somabrain.infrastructure.circuit_breaker import CircuitBreaker


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
            except Exception as exc:
                # Log circuit breaker check failure but continue with local state check
                import logging

                logging.getLogger(__name__).debug(
                    "Circuit breaker check failed for tenant %s: %s", tenant, exc
                )

        # Check local state
        state = self._get_state(tenant)
        return state.degraded_since is not None

    def _emit_degradation_metric(self, tenant: str, event_type: str) -> None:
        """Emit degradation event metric.

        Args:
            tenant: Tenant ID
            event_type: Either 'enter' or 'exit'
        """
        try:
            from somabrain.metrics.integration import SFM_DEGRADATION_EVENTS

            SFM_DEGRADATION_EVENTS.labels(tenant=tenant, event_type=event_type).inc()
        except Exception:
            # Metrics are optional; don't fail on metric emission errors
            pass

    def _mark_degraded(self, tenant: str) -> None:
        """Mark tenant as degraded (internal)."""
        state = self._get_state(tenant)
        if state.degraded_since is None:
            state.degraded_since = time.time()
            state.alert_triggered = False
            # Emit metric for entering degraded mode
            self._emit_degradation_metric(tenant, "enter")
            # Log state transition
            import logging

            logging.getLogger(__name__).warning(
                "Tenant %s entered degraded mode", tenant
            )

    def mark_degraded(self, tenant: str) -> None:
        """Explicitly mark tenant as degraded.

        Called when SFM operations fail.
        Per E1.1: When SFM unreachable, SB continues with WM-only (degraded=true).
        """
        self._mark_degraded(tenant)

    def mark_recovered(self, tenant: str) -> None:
        """Mark tenant as recovered from degradation.

        Called when SFM operations succeed after degradation.
        Per E1.3: When SFM recovers, clear degraded state.
        """
        state = self._get_state(tenant)
        if state.degraded_since is not None:
            # Log recovery with duration
            duration = time.time() - state.degraded_since
            import logging

            logging.getLogger(__name__).info(
                "Tenant %s recovered from degraded mode (duration: %.2fs)",
                tenant,
                duration,
            )
            # Emit metric for exiting degraded mode
            self._emit_degradation_metric(tenant, "exit")

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
                from somabrain.metrics.integration import record_degradation_event

                record_degradation_event(tenant, "alert")
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


def _create_degradation_manager() -> DegradationManager:
    """Factory function for DI container."""
    # Try to get circuit breaker from registry
    circuit_breaker = None
    try:
        from somabrain.infrastructure.cb_registry import get_cb

        circuit_breaker = get_cb()
    except Exception:
        pass

    return DegradationManager(circuit_breaker=circuit_breaker)


def get_degradation_manager() -> DegradationManager:
    """Get the DegradationManager instance from DI container.

    Uses the centralized DI container for singleton management,
    eliminating module-level mutable state per VIBE requirements.
    """
    from somabrain.core.container import container

    if not container.has("degradation_manager"):
        container.register("degradation_manager", _create_degradation_manager)
    return container.get("degradation_manager")


def reset_degradation_manager() -> None:
    """Reset the DegradationManager (for testing)."""
    from somabrain.core.container import container

    # Re-register to clear the instance
    container.register("degradation_manager", _create_degradation_manager)
