"""Memory Service Module for SomaBrain.

Provides a high‑level ``MemoryService`` class that wraps a backend client and
delegates circuit‑breaker logic to the shared :class:`~somabrain.infrastructure.
 circuit_breaker.CircuitBreaker` implementation.
"""

from __future__ import annotations

import uuid
from typing import Any, Iterable, List

# Local imports – placed after the standard library imports to avoid circular
# dependencies when the ``metrics`` module lazily imports ``MemoryService``.
from somabrain.infrastructure.cb_registry import get_cb
from ..infrastructure.tenant import tenant_label, resolve_namespace
from django.conf import settings
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
        """Initialize the instance."""

        self._backend = backend
        self.namespace = namespace or ""
        self._cb = get_cb()
        # Enforce production-like degradation defaults: always queue, never silently drop.
        self._degrade_queue = True
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
        returns an object with the actual memory‑operation methods (``remember``).
        """
        return self._backend.for_namespace(self.namespace)

    # ---------------------------------------------------------------------
    # Circuit‑breaker delegation helpers
    # ---------------------------------------------------------------------
    def _is_circuit_open(self) -> bool:
        """Execute is circuit open."""

        return self._cb.is_open(self.tenant_id)

    def _mark_success(self) -> None:
        """Execute mark success."""

        self._cb.record_success(self.tenant_id)

    def _mark_failure(self) -> None:
        """Execute mark failure."""

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
        except Exception as exc:
            # Journal is best-effort; log but do not raise.
            import logging

            logging.getLogger(__name__).warning(
                "Failed to queue degraded write for tenant=%s action=%s: %s",
                self.tenant_id,
                action,
                exc,
            )

    # ---------------------------------------------------------------------
    # Public API used by the application and tests
    # ---------------------------------------------------------------------
    def remember(self, key: str, payload: dict, universe: str | None = None):
        """Execute remember.

        Args:
            key: The key.
            payload: The payload.
            universe: The universe.
        """

        if universe and "universe" not in payload:
            payload["universe"] = universe
        # Attempt auto-reset of circuit if backend has recovered.
        self._reset_circuit_if_needed()
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

    def recall(self, query: str, top_k: int = 3, universe: str | None = None):
        """Execute recall.

        Args:
            query: The query.
            top_k: The top_k.
            universe: The universe.
        """

        self._reset_circuit_if_needed()
        if self._is_circuit_open():
            raise RuntimeError("Memory service unavailable (circuit open)")
        try:
            hits = self.client().recall(query, top_k=top_k, universe=universe)
            self._mark_success()
            return hits
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

    def recall_with_scores(
        self, query: str, top_k: int = 3, universe: str | None = None
    ) -> List[Any]:
        """Recall memories while preserving similarity scores when supported."""

        self._reset_circuit_if_needed()
        if self._is_circuit_open():
            raise RuntimeError("Memory service unavailable (circuit open)")
        client = self.client()
        try:
            if hasattr(client, "recall_with_scores"):
                hits = client.recall_with_scores(query, top_k=top_k, universe=universe)
            else:
                hits = client.recall(query, top_k=top_k, universe=universe)
            self._mark_success()
            return hits
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

    async def aremember(self, key: str, payload: dict, universe: str | None = None):
        """Execute aremember.

        Args:
            key: The key.
            payload: The payload.
            universe: The universe.
        """

        if universe and "universe" not in payload:
            payload["universe"] = universe
        self._reset_circuit_if_needed()
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

    async def arecall(self, query: str, top_k: int = 3, universe: str | None = None):
        """Execute arecall.

        Args:
            query: The query.
            top_k: The top_k.
            universe: The universe.
        """

        self._reset_circuit_if_needed()
        if self._is_circuit_open():
            raise RuntimeError("Memory service unavailable (circuit open)")
        try:
            hits = await self.client().arecall(query, top_k=top_k, universe=universe)
            self._mark_success()
            return hits
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

    async def arecall_with_scores(
        self, query: str, top_k: int = 3, universe: str | None = None
    ) -> List[Any]:
        """Async variant of :meth:`recall_with_scores`."""

        self._reset_circuit_if_needed()
        if self._is_circuit_open():
            raise RuntimeError("Memory service unavailable (circuit open)")
        client = self.client()
        try:
            if hasattr(client, "arecall_with_scores"):
                hits = await client.arecall_with_scores(
                    query, top_k=top_k, universe=universe
                )
            else:
                hits = await client.arecall(query, top_k=top_k, universe=universe)
            self._mark_success()
            return list(hits)
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

    async def aremember_bulk(
        self,
        items: Iterable[tuple[str, dict]],
        universe: str | None = None,
    ) -> list[tuple[float, float, float]]:
        """Execute aremember bulk.

        Args:
            items: The items.
            universe: The universe.
        """

        prepared: list[tuple[str, dict]] = []
        for key, payload in items:
            body = dict(payload)
            if universe and "universe" not in body:
                body["universe"] = universe
            prepared.append((key, body))
        if not prepared:
            return []
        self._reset_circuit_if_needed()
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
        """Execute health check."""

        try:
            health = self.client().health()
        except Exception as exc:
            import logging

            logging.getLogger(__name__).debug(
                "Health check failed for namespace=%s: %s", self.namespace, exc
            )
            return False
        if isinstance(health, dict):
            if "http" in health:
                return bool(health.get("http"))
            return bool(health.get("ok"))
        return False

    def _reset_circuit_if_needed(self) -> bool:
        """Execute reset circuit if needed."""

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
        """Execute coord for key.

        Args:
            key: The key.
            universe: The universe.
        """

        return self.client().coord_for_key(key, universe)

    def fetch_by_coord(self, coord, universe: str | None = None):
        """Fetch memory payloads by coordinate using GET /memories/{coord}."""
        self._reset_circuit_if_needed()
        return self.client().fetch_by_coord(coord, universe)

    def delete(self, coordinate):
        """Execute delete.

        Args:
            coordinate: The coordinate.
        """

        self._reset_circuit_if_needed()
        return self.client().delete(coordinate)

    def health(self) -> dict:
        """Execute health."""

        return self.client().health()

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
        """Execute configure tenant thresholds.

        Args:
            tenant: The tenant.
        """

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
        """Execute should attempt reset.

        Args:
            tenant: The tenant.
        """

        return cls._circuit_breaker.should_attempt_reset(tenant)

    # ---------------------------------------------------------------------
    # Tenant‑label utilities – thin wrappers around the infrastructure module
    # ---------------------------------------------------------------------
    def _tenant_label(self, namespace: str) -> str:
        """Execute tenant label.

        Args:
            namespace: The namespace.
        """

        return tenant_label(namespace)

    def _resolve_namespace_for_label(self, label: str) -> str:
        """Execute resolve namespace for label.

        Args:
            label: The label.
        """

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
        """Execute update outbox metric.

        Args:
            tenant: The tenant.
            count: The count.
        """

        try:
            from somabrain import metrics

            gauge = getattr(metrics, "OUTBOX_PENDING", None)
            if gauge is not None and hasattr(gauge, "labels"):
                gauge.labels(tenant_id=str(tenant)).set(float(count))
        except Exception as exc:
            import logging

            logging.getLogger(__name__).debug(
                "Failed to update OUTBOX_PENDING metric for tenant=%s: %s", tenant, exc
            )

    @staticmethod
    def _update_tenant_outbox_metric(tenant: str, count: int) -> None:
        """Execute update tenant outbox metric.

        Args:
            tenant: The tenant.
            count: The count.
        """

        try:
            from somabrain import metrics

            gauge = getattr(metrics, "OUTBOX_PENDING_BY_TENANT", None)
            if gauge is not None and hasattr(gauge, "labels"):
                gauge.labels(tenant_id=str(tenant)).set(float(count))
        except Exception as exc:
            import logging

            logging.getLogger(__name__).debug(
                "Failed to update OUTBOX_PENDING_BY_TENANT metric for tenant=%s: %s",
                tenant,
                exc,
            )
