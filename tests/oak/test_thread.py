from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from somabrain.cognitive.thread_model import Base, CognitiveThread
from somabrain.oak import planner as oak_planner

"""Unit tests for the Cognitive Thread implementation.

The tests verify the SQLAlchemy model helpers and the integration point in
``somabrain.oak.planner.plan_for_tenant``.
They use an in-memory SQLite database as a real replacement for PostgreSQL.
"""


@pytest.fixture
def db_session(monkeypatch):
    """Create an in-memory SQLite database and session for testing."""
    # Use SQLite in-memory database as a real implementation replacement for Postgres
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Patch the session factory used in planner
    monkeypatch.setattr(
        "somabrain.storage.db.get_session_factory",
        lambda *a, **kw: lambda: session,
    )

    yield session
    session.close()


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


def test_planner_uses_thread_next_option(db_session):
    """Ensure ``plan_for_tenant`` prefers a thread's next option."""
    # Create thread in the real (in-memory) DB
    thread = CognitiveThread(tenant_id="tenant1")
    thread.set_options(["thread_opt"])
    db_session.add(thread)
    db_session.commit()

    # Ensure it was saved
    saved_thread = db_session.get(CognitiveThread, "tenant1")
    assert saved_thread is not None
    assert saved_thread.get_options() == ["thread_opt"]

    # Run planner which should use the patched session factory
    result = oak_planner.plan_for_tenant("tenant1")
    assert result == ["thread_opt"]
