from __future__ import annotations

import os


from somabrain.cognitive.thread_model import CognitiveThread
from somabrain.storage.db import Base
from somabrain.oak import planner as oak_planner

"""
Unit tests for the Cognitive Thread implementation.

If a real PostgreSQL connection is not configured (via ``TEST_PG_DSN`` or
``DATABASE_URL``), the tests fail fast to enforce the no-mocks policy.
"""


PG_DSN = os.environ.get("TEST_PG_DSN") or os.environ.get("DATABASE_URL")


def test_cognitive_thread_basic_operations() -> None:
    """Validate ``CognitiveThread`` helper methods."""
    assert PG_DSN, "TEST_PG_DSN or DATABASE_URL must be set for oak thread tests"
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
    assert PG_DSN, "TEST_PG_DSN or DATABASE_URL must be set for oak thread tests"

    # The planner uses get_session_factory; ensure it points at configured DSN.
    def factory():
        from somabrain.storage.db import get_session_factory

        return get_session_factory()

    session_factory = factory()
    with session_factory() as session:
        # Ensure the cognitive_threads table exists for the real Postgres DSN.
        Base.metadata.create_all(session.get_bind())
        # Clear any leftover rows from previous runs to avoid PK collisions.
        session.query(CognitiveThread).delete()
        session.commit()
        thread = CognitiveThread(tenant_id="tenant1")
        thread.set_options(["thread_opt"])
        session.add(thread)
        session.commit()

    monkeypatch.setattr(
        "somabrain.storage.db.get_session_factory", lambda *_, **__: session_factory
    )

    result = oak_planner.plan_for_tenant("tenant1")
    assert result == ["thread_opt"]
