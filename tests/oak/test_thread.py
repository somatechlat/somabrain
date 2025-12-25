from __future__ import annotations

import pytest

from django.conf import settings
from somabrain.models import CognitiveThread
from somabrain.oak import planner as oak_planner


"""
Integration tests for the Cognitive Thread implementation.

These rely on a real PostgreSQL instance configured via Django settings.
When the DSN is missing the tests skip rather than failing,
preserving the "no mocks" guarantee without causing false negatives.
"""

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

# Use centralized Settings for test configuration
PG_DSN = getattr(settings, "SOMABRAIN_POSTGRES_DSN", None) or getattr(settings, "DATABASE_URL", None)


def _require_pg() -> None:
    if not PG_DSN:
        pytest.skip("SOMABRAIN_POSTGRES_DSN or DATABASE_URL must be set for oak thread tests")


@pytest.mark.django_db
def test_cognitive_thread_basic_operations() -> None:
    """Validate ``CognitiveThread`` helper methods using Django ORM."""
    _require_pg()
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


@pytest.mark.django_db
def test_planner_uses_thread_next_option(monkeypatch) -> None:
    """Ensure ``plan_for_tenant`` prefers a thread's next option using Django ORM."""
    _require_pg()

    # Clear any leftover rows from previous runs to avoid PK collisions.
    CognitiveThread.objects.filter(tenant_id="tenant1").delete()

    # Create a new thread using Django ORM
    thread = CognitiveThread.objects.create(tenant_id="tenant1")
    thread.set_options(["thread_opt"])
    thread.save()

    # Run planner which should use Django ORM
    result = oak_planner.plan_for_tenant("tenant1")
    assert result == ["thread_opt"]
