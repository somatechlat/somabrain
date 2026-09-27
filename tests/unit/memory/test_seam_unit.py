"""Mock-free unit tests for the canonical memory contract surface.

Behavioural seam proofs (remember → recall → forget, tenant isolation,
BrainBridge dialect) live in ``tests/integration/test_seam_contract.py`` and
run against the real SomaBrain API. Per ``somabrain/AGENT.md:138`` and
VIBE_CODING_RULES: no mocks, no stubs, no test doubles in this suite.

What remains here are pure, dependency-free checks that need no infrastructure:
route resolution and request-model fail-closed behaviour.
"""

from __future__ import annotations

import pytest

from somabrain.api.memory.models import MemoryWriteRequest


@pytest.mark.unit
def test_canonical_memory_routes_resolve() -> None:
    """Canonical paths and their aliases must all resolve to live handlers."""
    from django.urls import Resolver404, resolve

    live = [
        "/api/memory/remember",
        "/memory/remember",
        "/api/memory/recall",
        "/memory/recall",
        "/api/memory/forget",
        "/memory/forget",
        # legacy BrainBridge spellings — thin aliases
        "/api/remember",
        "/remember",
        "/api/recall",
        "/recall",
        "/api/forget",
        "/forget",
    ]
    for path in live:
        try:
            resolve(path)
        except Resolver404:
            raise AssertionError(f"route does not resolve: {path}")


@pytest.mark.unit
def test_write_request_rejects_empty_body() -> None:
    """No silent no-op: a write without identity or content must fail closed."""
    with pytest.raises(Exception):
        MemoryWriteRequest.model_validate({"tenant": "t"})
