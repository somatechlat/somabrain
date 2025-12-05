"""Memory Service Module for SomaBrain.

Provides a high‑level ``MemoryService`` class that wraps a backend client and
delegates circuit‑breaker logic to the shared :class:`~somabrain.infrastructure.
 circuit_breaker.CircuitBreaker` implementation.
"""

from __future__ import annotations

import uuid
from typing import Any, Iterable

# Local imports – placed after the standard library imports to avoid circular
# dependencies when the ``metrics`` module lazily imports ``MemoryService``.
from somabrain.infrastructure.cb_registry import get_cb
from ..infrastructure.tenant import tenant_label, resolve_namespace
from common.config.settings import settings
from somabrain.journal import get_journal, JournalEvent


class MemoryService:
    """High‑level façade for the multi‑tenant memory backend.

    Parameters
    ----------
    backend:
        An object exposing a ``for_namespace(namespace)`` method that returns a
        client with the memory operations used by the service.
    namespace:
        The tenant/namespace string for which this instance operates.
    """

    _circuit_breaker = get_cb()

    def __init__(self, backend: Any, namespace: str | None = None) -> None:
        self._backend = backend
        self.namespace = namespace or ""
        self._cb = get_cb()
        self._degrade_queue = bool(getattr(settings, "memory_degrade_queue", True))
        self._degrade_readonly = bool(
            getattr(settings, "memory_degrade_readonly", False)
        )
        self._degrade_topic = getattr(
            settings, "memory_degrade_topic", "memory.degraded"
        )

    # ---------------------------------------------------------------------
    # Backend accessor helpers
    # ---------------------------------------------------------------------
    def client(self) -> Any:
        """Return a client scoped to this instance's namespace.

        The backend is expected to provide a ``for_namespace`` method that
        returns an object with the actual memory‑operation methods.
        """
        return self._backend.for_namespace(self.namespace)

    # ---------------------------------------------------------------------
    # Circuit‑breaker delegation helpers
    # ---------------------------------------------------------------------
    def _is_circuit_open(self) -> bool:
        return self._cb.is_open(self.tenant_id)

    def _mark_success(self) -> None:
        self._cb.record_success(self.tenant_id)

    def _mark_failure(self) -> None:
        self._cb.record_failure(self.tenant_id)

    # ---------------------------------------------------------------------
    # Degradation helpers
    # ---------------------------------------------------------------------
    def _queue_degraded(self, action: str, payload: dict) -> None:
        """Persist a degraded write to the local journal."""
        if not self._degrade_queue:
            return
        try:
            journal = get_journal()
            ev = JournalEvent(
                id=str(uuid.uuid4()),
                topic=self._degrade_topic,
                payload={"action": action, "payload": payload},
                tenant_id=self.tenant_id,
                timestamp=None,
            )
            journal.append_event(ev)
        except Exception:
            # Journal is best-effort; do not raise.
            return

    # ---------------------------------------------------------------------
    # Public API used by the application and tests
    # ---------------------------------------------------------------------
    def remember(self, key: str, payload: dict, universe: str | None = None):
        if universe and "universe" not in payload:
            payload["universe"] = universe
        if self._is_circuit_open():
            self._queue_degraded("remember", {"key": key, "payload": payload})
            message = "Memory service unavailable (circuit open)"
            if self._degrade_readonly:
                raise RuntimeError(message)
            raise RuntimeError(f"{message}; queued locally for replay")
        try:
            result = self.client().remember(key, payload)
            self._mark_success()
            return result
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

    async def aremember(self, key: str, payload: dict, universe: str | None = None):
        if universe and "universe" not in payload:
            payload["universe"] = universe
        if self._is_circuit_open():
            self._queue_degraded("remember", {"key": key, "payload": payload})
            message = "Memory service unavailable (circuit open)"
            if self._degrade_readonly:
                raise RuntimeError(message)
            raise RuntimeError(f"{message}; queued locally for replay")
        try:
            result = await self.client().aremember(key, payload)
            self._mark_success()
            return result
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

    async def aremember_bulk(
        self,
        items: Iterable[tuple[str, dict]],
        universe: str | None = None,
    ) -> list[tuple[float, float, float]]:
        prepared: list[tuple[str, dict]] = []
        for key, payload in items:
            body = dict(payload)
            if universe and "universe" not in body:
                body["universe"] = universe
            prepared.append((key, body))
        if not prepared:
            return []
        if self._is_circuit_open():
            for key, body in prepared:
                self._queue_degraded("remember", {"key": key, "payload": body})
            message = "Memory service unavailable (circuit open)"
            if self._degrade_readonly:
                raise RuntimeError(message)
            raise RuntimeError(f"{message}; queued locally for replay")
        try:
            coords = await self.client().aremember_bulk(prepared)
            self._mark_success()
            return list(coords)
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

    # ---------------------------------------------------------------------
    # Miscellaneous helper methods (mostly no‑ops for metrics)
    # ---------------------------------------------------------------------
    def _health_check(self) -> bool:
        try:
            health = self.client().health()
        except Exception:
            return False
        if isinstance(health, dict):
            if "http" in health:
                return bool(health.get("http"))
            return bool(health.get("ok"))
        return False

    def _reset_circuit_if_needed(self) -> bool:
        if not self._is_circuit_open():
            return False
        tenant = getattr(self, "namespace", "default")
        breaker = self.__class__._circuit_breaker
        if not breaker.should_attempt_reset(tenant):
            return False
        if self._health_check():
            breaker.record_success(tenant)
            return True
        return False

    # The following methods simply proxy to the backend client.
    def coord_for_key(self, key: str, universe: str | None = None):
        return self.client().coord_for_key(key, universe)

    def delete(self, coordinate):
        return self.client().delete(coordinate)

    # ---------------------------------------------------------------------
    # Circuit‑breaker state inspection (used by the test suite)
    # ---------------------------------------------------------------------
    def get_circuit_state(self) -> dict:
        """Return the circuit‑breaker snapshot for this tenant.

        The returned dictionary mirrors the structure produced by
        ``CircuitBreaker.get_state`` and includes the ``tenant`` and ``namespace``
        fields required by the tests.
        """
        state = self.__class__._circuit_breaker.get_state(self.tenant_id)
        # Add compatibility fields
        state.update({"tenant": self.tenant_id, "namespace": self.namespace})
        return state

    @classmethod
    def reset_circuit_for_tenant(cls, tenant: str) -> None:
        """Close the circuit for *tenant* by recording a successful request."""
        cls._circuit_breaker.record_success(tenant)

    @classmethod
    def configure_tenant_thresholds(
        cls,
        tenant: str,
        *,
        failure_threshold: int | None = None,
        reset_interval: float | None = None,
    ) -> None:
        cls._circuit_breaker.configure_tenant(
            tenant,
            failure_threshold=failure_threshold,
            reset_interval=reset_interval,
        )

    @classmethod
    def get_all_tenant_circuit_states(cls) -> dict:
        """Aggregate circuit states for all known tenants.

        ``CircuitBreaker`` stores per‑tenant data in private dictionaries.  For
        the purpose of the test suite we can safely inspect the ``_circuit_open``
        mapping to discover the set of tenants that have been touched.
        """
        breaker = cls._circuit_breaker
        tenants = list(breaker._circuit_open.keys())
        return {t: breaker.get_state(t) for t in tenants}

    @classmethod
    def _should_attempt_reset(cls, tenant: str) -> bool:
        return cls._circuit_breaker.should_attempt_reset(tenant)

    # ---------------------------------------------------------------------
    # Tenant‑label utilities – thin wrappers around the infrastructure module
    # ---------------------------------------------------------------------
    def _tenant_label(self, namespace: str) -> str:
        return tenant_label(namespace)

    def _resolve_namespace_for_label(self, label: str) -> str:
        return resolve_namespace(label)

    @property
    def tenant_id(self) -> str:
        """Canonical tenant identifier derived from ``self.namespace``."""
        return self._tenant_label(self.namespace)

    # ---------------------------------------------------------------------
    # Metric helpers – no‑ops in the CI environment but kept for API stability
    # ---------------------------------------------------------------------
    @staticmethod
    def _update_outbox_metric(tenant: str, count: int) -> None:
        try:
            from somabrain import metrics

            gauge = getattr(metrics, "OUTBOX_PENDING", None)
            if gauge is not None and hasattr(gauge, "labels"):
                gauge.labels(tenant_id=str(tenant)).set(float(count))
        except Exception:
            return None

    @staticmethod
    def _update_tenant_outbox_metric(tenant: str, count: int) -> None:
        try:
            from somabrain import metrics

            gauge = getattr(metrics, "OUTBOX_PENDING_BY_TENANT", None)
            if gauge is not None and hasattr(gauge, "labels"):
                gauge.labels(tenant_id=str(tenant)).set(float(count))
        except Exception:
            return None
