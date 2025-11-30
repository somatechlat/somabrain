from __future__ import annotations

from typing import Any, Dict


from somabrain.cognitive.thread_model import CognitiveThread
from somabrain.oak import planner as oak_planner

"""Unit tests for the Cognitive Thread implementation.

The tests verify the SQLAlchemy model helpers and the integration point in
``somabrain.oak.planner.plan_for_tenant``. They avoid requiring a real
PostgreSQL instance by monkey-patching ``somabrain.storage.db.get_session_factory``
to return a simple in-memory mock session that mimics the ``.get`` and ``.commit``
behaviour used by the router and planner.
"""


class DummySession:
    """Very small mock of a SQLAlchemy session."""

    def __init__(self) -> None:
        self._store: Dict[str, CognitiveThread] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def get(self, model: Any, pk: str) -> CognitiveThread | None:  # noqa: D401
        """Return the stored instance or ``None`` if missing."""
        return self._store.get(pk)

    def add(self, instance: CognitiveThread) -> None:
        self._store[instance.tenant_id] = instance

    def commit(self) -> None:
        return None


def test_cognitive_thread_basic_operations() -> None:
    """Validate ``CognitiveThread`` helper methods."""
    thread = CognitiveThread(tenant_id="test")
    assert thread.get_options() == []
    assert thread.next_option() is None

    thread.set_options(["opt1", "opt2", "opt3"])
    assert thread.get_options() == ["opt1", "opt2", "opt3"]

    assert thread.next_option() == "opt1"
    assert thread.cursor == 1
    assert thread.next_option() == "opt2"
    assert thread.cursor == 2
    _ = thread.next_option()
    assert thread.next_option() is None

    thread.reset()
    assert thread.get_options() == []
    assert thread.cursor == 0


def test_planner_uses_thread_next_option(monkeypatch):
    """Ensure ``plan_for_tenant`` prefers a thread's next option."""

    dummy_session = DummySession()
    thread = CognitiveThread(tenant_id="tenant1")
    thread.set_options(["thread_opt"])
    dummy_session.add(thread)
    assert dummy_session.get(CognitiveThread, "tenant1") is thread

    def fake_factory(*_, **__):
        return dummy_session

    monkeypatch.setattr(
        "somabrain.storage.db.get_session_factory",
        lambda *a, **kw: lambda: dummy_session,
    )

    result = oak_planner.plan_for_tenant("tenant1")
    assert result == ["thread_opt"]
