"""Tests that verify the tight coupling between ``MemoryService`` circuit‑breaker
state changes and the ``TenantSleepState`` persistence/sleep‑gauge updates.

The real ``MemoryService`` talks to a SQLAlchemy session factory.  For unit
tests we replace that factory with a lightweight stub that records the calls
performed by ``_mark_failure`` and ``_mark_success``.  This allows us to assert
that:

* ``record_failure`` and ``record_success`` are delegated to the shared
  ``CircuitBreaker`` instance.
* The ``TenantSleepState`` row is created when missing and its ``current_state``
  is set to ``FREEZE`` on failure and ``ACTIVE`` on success.
* The Prometheus gauge ``somabrain_sleep_state`` is updated with the correct
  integer representation (3 for FREEZE, 0 for ACTIVE).

No external services (Postgres, Redis, OPA) are required – the test runs entirely
in‑process using ``unittest.mock``.
"""

from __future__ import annotations

import types
from unittest import mock

import pytest

from somabrain.services.memory_service import MemoryService as _MemoryService
from somabrain.sleep import SleepState


class DummySession:
    """Very small context manager mimicking the SQLAlchemy session used in the
    production code. It records the ``get`` and ``add`` calls for later
    assertions.
    """

    def __init__(self):
        self._stored = {}
        self.added = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, model_cls, tenant_id):
        # Return the stored instance if present, otherwise ``None``.
        return self._stored.get(tenant_id)

    def add(self, obj):
        # Store the object by its ``tenant_id`` attribute for later checks.
        self.added.append(obj)
        if hasattr(obj, "tenant_id"):
            self._stored[obj.tenant_id] = obj

    def commit(self):
        # No‑op – the object is already in ``_stored``.
        pass


@pytest.fixture
def dummy_backend():
    """A minimal memory backend that satisfies the ``MemoryService`` contract.
    Only the ``for_namespace`` method is required for the tests that exercise
    the circuit‑breaker helpers.
    """

    class Backend:
        def for_namespace(self, ns: str):  # pragma: no cover – not used directly
            return self

    return Backend()


def _patch_session_factory(monkeypatch, dummy_session):
    """Replace ``somabrain.services.memory_service.get_session_factory`` with a
    callable that returns a factory yielding ``dummy_session``.
    """

    def factory():
        return lambda: dummy_session

    monkeypatch.setattr(
        "somabrain.services.memory_service.get_session_factory", factory
    )


def test_mark_failure_updates_sleep_state_and_gauge(monkeypatch, dummy_backend):
    dummy_session = DummySession()
    _patch_session_factory(monkeypatch, dummy_session)

    # Patch the shared CircuitBreaker to a fresh instance so we can inspect it.
    from somabrain.infrastructure.circuit_breaker import CircuitBreaker

    cb = CircuitBreaker()
    monkeypatch.setattr(_MemoryService, "_circuit_breaker", cb, raising=False)

    # Patch the gauge acquisition to a dummy gauge that records ``set`` calls.
    dummy_gauge = mock.Mock()
    monkeypatch.setattr(
        "somabrain.services.memory_service.get_gauge",
        lambda *a, **kw: dummy_gauge,
    )

    # Instantiate the service for a concrete tenant.
    svc = _MemoryService(dummy_backend, "test_tenant")

    # Invoke the failure path.
    svc._mark_failure()

    # ---- Assertions -----------------------------------------------------
    # CircuitBreaker recorded a failure.
    state = cb.get_state("test_tenant")
    assert state["failure_count"] == 1
    assert state["circuit_open"] is False  # threshold not reached yet

    # A TenantSleepState row must have been created and set to FREEZE.
    stored = dummy_session._stored.get("test_tenant")
    assert stored is not None, "TenantSleepState was not persisted"
    assert stored.current_state == SleepState.FREEZE.value
    assert stored.target_state == SleepState.FREEZE.value

    # The gauge must have been called with state "3" (FREEZE).
    dummy_gauge.labels.assert_called_once_with(tenant="test_tenant", state="3")
    dummy_gauge.labels.return_value.set.assert_called_once_with(1)


def test_mark_success_resets_sleep_state_and_gauge(monkeypatch, dummy_backend):
    dummy_session = DummySession()
    _patch_session_factory(monkeypatch, dummy_session)

    from somabrain.infrastructure.circuit_breaker import CircuitBreaker

    cb = CircuitBreaker()
    monkeypatch.setattr(_MemoryService, "_circuit_breaker", cb, raising=False)

    dummy_gauge = mock.Mock()
    monkeypatch.setattr(
        "somabrain.services.memory_service.get_gauge",
        lambda *a, **kw: dummy_gauge,
    )

    svc = _MemoryService(dummy_backend, "test_tenant")

    # Simulate a prior failure so that a row already exists.
    # Manually insert a FREEZE state to see it transition to ACTIVE.
    from somabrain.sleep.models import TenantSleepState
    frozen = TenantSleepState(
        tenant_id="test_tenant",
        current_state=SleepState.FREEZE.value,
        target_state=SleepState.FREEZE.value,
    )
    dummy_session._stored["test_tenant"] = frozen

    # Call the success helper.
    svc._mark_success()

    # ---- Assertions -----------------------------------------------------
    state = cb.get_state("test_tenant")
    assert state["failure_count"] == 0
    assert state["circuit_open"] is False

    stored = dummy_session._stored.get("test_tenant")
    assert stored.current_state == SleepState.ACTIVE.value
    assert stored.target_state == SleepState.ACTIVE.value

    dummy_gauge.labels.assert_called_once_with(tenant="test_tenant", state="0")
    dummy_gauge.labels.return_value.set.assert_called_once_with(1)
