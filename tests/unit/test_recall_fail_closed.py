"""A recall outage must raise — never return [] dressed as success (T-5).

A caller cannot distinguish "no memories" from "the store is down" when both
arrive as an empty list, and an honest empty state gets shown when the truth is
a failure. The two states are separated at the type level:

* a genuine "no results" is a successful ``[]``
* an outage raises ``MemoryRecallUnavailable``

The same file guards the second half of T-5: no tenant/namespace path in any
fail-closed boundary module may fall back to ``"default"``. The agent side
already carries this guard
(``somaAgent01/tests/unit/test_no_silent_default_tenant.py``).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from somabrain.memory.recall_ops import (
    MemoryRecallUnavailable,
    memories_search_async,
    memories_search_sync,
)

pytestmark = pytest.mark.no_django

BRAIN_ROOT = Path(__file__).resolve().parents[2]
BOUNDARY_FILES = (
    BRAIN_ROOT / "somabrain" / "memory" / "recall_ops.py",
    BRAIN_ROOT / "somabrain" / "db" / "outbox.py",
    BRAIN_ROOT / "somabrain" / "services" / "retrieval_pipeline.py",
    # T-5 sweep: every remaining silent default tenant/namespace in the brain.
    BRAIN_ROOT / "somabrain" / "metrics" / "memory_metrics.py",
    BRAIN_ROOT / "somabrain" / "context" / "tenant_overrides.py",
    BRAIN_ROOT / "somabrain" / "workers" / "quota_manager.py",
    BRAIN_ROOT / "somabrain" / "services" / "outbox_sync.py",
    BRAIN_ROOT / "somabrain" / "brain_settings" / "models.py",
)


class _TransportPresent:
    """Non-None transport so the config guard passes.

    ``memories_search_sync`` / ``memories_search_async`` check the transport
    for presence (and ``async_client``) only; the HTTP hop itself goes through
    ``http_post_fn``. Nothing here fakes a store.
    """

    async_client = object()


def _outage_post(endpoint, body, headers, operation=None):
    """The exact tuple ``post_with_retries_sync`` returns when the store is down."""
    return False, 503, None


def _ok_empty_post(endpoint, body, headers, operation=None):
    """A 2xx with no hits — a successful empty, not an outage."""
    return True, 200, {"hits": []}


def _rescore(hits, query_text):
    return hits


def test_recall_outage_raises_not_empty_list():
    """A failing store raises MemoryRecallUnavailable; it never returns []."""
    with pytest.raises(MemoryRecallUnavailable) as excinfo:
        memories_search_sync(
            _TransportPresent(),
            "where did I put the keys",
            3,
            "real",
            "req-outage",
            _outage_post,
            _rescore,
            tenant="tenant-outage",
        )
    assert "503" in str(excinfo.value)
    assert not isinstance(excinfo.value, AssertionError)


def test_recall_outage_raises_async_not_empty_list():
    """Async recall fails closed the same way."""

    async def _run():
        async def _outage_post(endpoint, body, headers, operation=None):
            return False, 503, None

        return await memories_search_async(
            _TransportPresent(),
            "where did I put the keys",
            3,
            "real",
            "req-outage-async",
            _outage_post,
            _rescore,
            tenant="tenant-outage",
        )

    with pytest.raises(MemoryRecallUnavailable):
        asyncio.run(_run())


def test_recall_unavailable_is_a_typed_failure_not_an_empty_list():
    """The two states are distinguishable at the type level."""
    assert issubclass(MemoryRecallUnavailable, RuntimeError)
    outage = MemoryRecallUnavailable("store down")
    assert not isinstance(outage, list)
    # A genuine "no results" is the successful empty list — a different type.
    genuine_empty: list = []
    assert type(genuine_empty) is not type(outage)


def test_genuine_empty_recall_is_successful_empty():
    """A 2xx with no hits is a successful empty, not a failure."""
    result = memories_search_sync(
        _TransportPresent(),
        "nothing matches this query",
        3,
        "real",
        "req-empty",
        _ok_empty_post,
        _rescore,
        tenant="tenant-empty",
    )
    assert result == []


def test_missing_transport_is_refused_not_empty():
    """No transport configured raises — never a silent empty recall."""
    with pytest.raises(MemoryRecallUnavailable):
        memories_search_sync(
            None,
            "query",
            3,
            "real",
            "req-no-transport",
            _outage_post,
            _rescore,
            tenant="tenant-no-transport",
        )


def test_endpoint_incompatible_is_typed_failure():
    """404/405/422 name the incompatibility through the same typed failure."""

    def _gone_post(endpoint, body, headers, operation=None):
        return False, 404, None

    with pytest.raises(MemoryRecallUnavailable) as excinfo:
        memories_search_sync(
            _TransportPresent(),
            "query",
            3,
            "real",
            "req-gone",
            _gone_post,
            _rescore,
            tenant="tenant-gone",
        )
    assert "unavailable" in str(excinfo.value).lower()


def test_no_silent_default_tenant_on_boundary_paths():
    """No tenant/namespace path may name a fallback partition (AP-04, T-5).

    Covers both shapes of the silent default: a call-site ``or "default"``
    and a schema/parameter default that makes an uninitialised identity
    look initialised (``tenant: str = "default"``, ``default="default"``).
    """
    for path in BOUNDARY_FILES:
        source = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(source.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for needle in ('or "default"', "or 'default'"):
                if needle in stripped:
                    raise AssertionError(
                        f"silent default tenant/namespace at "
                        f"{path.name}:{lineno}: {stripped!r}"
                    )
            if 'getattr(' in stripped and '"default"' in stripped:
                raise AssertionError(
                    f"silent default tenant via getattr at "
                    f"{path.name}:{lineno}: {stripped!r}"
                )
            if 'tenant: str = "default"' in stripped or "tenant: str = 'default'" in stripped:
                raise AssertionError(
                    f"silent default tenant parameter at "
                    f"{path.name}:{lineno}: {stripped!r}"
                )
            if 'default="default"' in stripped or "default='default'" in stripped:
                raise AssertionError(
                    f"silent default tenant on the schema at "
                    f"{path.name}:{lineno}: {stripped!r}"
                )
