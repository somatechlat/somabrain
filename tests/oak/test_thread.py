"""Unit tests for the Cognitive Thread implementation.

The tests verify the SQLAlchemy model helpers and the integration point in
``somabrain.oak.planner.plan_for_tenant``.  They avoid requiring a real
PostgreSQL instance by monkey‑patching ``somabrain.storage.db.get_session_factory``
to return a simple in‑memory mock session that mimics the ``.get`` and ``.commit``
behaviour used by the router and planner.
"""

from __future__ import annotations

import types
from typing import Any, Dict

import pytest

from somabrain.cognitive.thread_model import CognitiveThread
from somabrain.oak import planner as oak_planner


class DummySession:
    """Very small mock of a SQLAlchemy session.

    It stores objects in a dict keyed by primary key and implements ``get``,
    ``add`` and ``commit`` methods used by the production code.
    """

    def __init__(self) -> None:
        self._store: Dict[str, CognitiveThread] = {}

    # Context manager protocol so the planner can use ``with Session() as session``.
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # No special cleanup needed for the in‑memory mock.
        return False

    def get(self, model: Any, pk: str) -> CognitiveThread | None:  # noqa: D401
        """Return the stored instance or ``None`` if missing."""
        return self._store.get(pk)

    def add(self, instance: CognitiveThread) -> None:
        self._store[instance.tenant_id] = instance

    def commit(self) -> None:
        # No‑op for the in‑memory mock.
raise NotImplementedError("Placeholder removed per VIBE rules")


def test_cognitive_thread_basic_operations():
    """Validate ``CognitiveThread`` helper methods."""
    thread = CognitiveThread(tenant_id="test")
    # Initially empty
    assert thread.get_options() == []
    assert thread.next_option() is None

    # Set options and retrieve them
    thread.set_options(["opt1", "opt2", "opt3"])
    assert thread.get_options() == ["opt1", "opt2", "opt3"]

    # Next option advances the cursor
    assert thread.next_option() == "opt1"
    assert thread.cursor == 1
    assert thread.next_option() == "opt2"
    assert thread.cursor == 2
    # Exhaustion returns ``None``
    _ = thread.next_option()  # returns "opt3"
    assert thread.next_option() is None

    # Reset clears state
    thread.reset()
    assert thread.get_options() == []
    assert thread.cursor == 0


def test_planner_uses_thread_next_option(monkeypatch):
    """Ensure ``plan_for_tenant`` prefers a thread's next option.

    The test patches ``get_session_factory`` to return a ``DummySession`` that
    contains a pre‑populated ``CognitiveThread``.  The planner should return the
    single next option without falling back to the Oak option manager.
    """

    # Prepare a dummy session with a thread that has one option.
    dummy_session = DummySession()
    thread = CognitiveThread(tenant_id="tenant1")
    thread.set_options(["thread_opt"])
    dummy_session.add(thread)
    # Verify our dummy session returns the thread correctly.
    assert dummy_session.get(CognitiveThread, "tenant1") is thread

    # Patch the session factory to return our dummy session.
    def fake_factory(*_, **__):
        return dummy_session

    # The real ``get_session_factory`` returns a callable (sessionmaker) that
    # produces a session object. Our dummy needs to mimic that callable.
    monkeypatch.setattr(
        "somabrain.storage.db.get_session_factory",
        lambda *a, **kw: lambda: dummy_session,
    )

    # Call the planner – it should retrieve the thread's next option.
    result = oak_planner.plan_for_tenant("tenant1")
    assert result == ["thread_opt"]
