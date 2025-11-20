"""Memory Service Module for SomaBrain.

Provides a high‑level ``MemoryService`` class that wraps a backend client and
delegates circuit‑breaker logic to the shared :class:`~somabrain.infrastructure.
 circuit_breaker.CircuitBreaker` implementation.
"""

from __future__ import annotations

from typing import Any, Iterable

# Local imports – placed after the standard library imports to avoid circular
# dependencies when the ``metrics`` module lazily imports ``MemoryService``.
from ..infrastructure.circuit_breaker import CircuitBreaker
from ..infrastructure.tenant import tenant_label, resolve_namespace


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

    # A single shared circuit‑breaker for all service instances.
    _circuit_breaker: CircuitBreaker = CircuitBreaker()

    def __init__(self, backend: Any, namespace: str | None = None) -> None:
        self._backend = backend
        self.namespace = namespace or ""

    # ---------------------------------------------------------------------
    # Backend accessor helpers
    # ---------------------------------------------------------------------
    def client(self) -> Any:
        """Return a client scoped to this instance's namespace.

        The backend is expected to provide a ``for_namespace`` method that
        returns an object with the actual memory‑operation methods (``remember``,
        ``link`` …).  For the unit tests a tiny mock backend is supplied.
        """
        return self._backend.for_namespace(self.namespace)

    # ---------------------------------------------------------------------
    # Circuit‑breaker delegation helpers
    # ---------------------------------------------------------------------
    def _is_circuit_open(self) -> bool:
        return self.__class__._circuit_breaker.is_open(self.tenant_id)

    def _mark_success(self) -> None:
        self.__class__._circuit_breaker.record_success(self.tenant_id)

    def _mark_failure(self) -> None:
        self.__class__._circuit_breaker.record_failure(self.tenant_id)

    # ---------------------------------------------------------------------
    # Public API used by the application and tests
    # ---------------------------------------------------------------------
    def remember(self, key: str, payload: dict, universe: str | None = None):
        if universe and "universe" not in payload:
            payload["universe"] = universe
        if self._is_circuit_open():
            raise RuntimeError("Memory service unavailable (circuit open)")
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
            raise RuntimeError("Memory service unavailable (circuit open)")
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
            raise RuntimeError("Memory service unavailable (circuit open)")
        try:
            coords = await self.client().aremember_bulk(prepared)
            self._mark_success()
            return list(coords)
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

    def link(self, from_coord, to_coord, link_type: str = "related", weight: float = 1.0):
        if self._is_circuit_open():
            raise RuntimeError("Memory service unavailable (circuit open)")
        try:
            result = self.client().link(from_coord, to_coord, link_type, weight)
            self._mark_success()
            return result
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

    async def alink(self, from_coord, to_coord, link_type: str = "related", weight: float = 1.0):
        if self._is_circuit_open():
            raise RuntimeError("Memory service unavailable (circuit open)")
        try:
            result = await self.client().alink(from_coord, to_coord, link_type, weight)
            self._mark_success()
            return result
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

    def payloads_for_coords(self, coords, universe: str | None = None):
        return self.client().payloads_for_coords(coords, universe)

    def delete(self, coordinate):
        return self.client().delete(coordinate)

    def links_from(self, start, type_filter: str | None = None, limit: int = 50):
        return self.client().links_from(start, type_filter, limit)

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
        # Add compatibility fields expected by the legacy test suite.
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
        # Placeholder – real implementation would interact with Prometheus.
        return None

    @staticmethod
    def _update_tenant_outbox_metric(tenant: str, count: int) -> None:
        # Placeholder – kept to satisfy tests that only verify existence.
        return None
