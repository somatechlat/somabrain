"""Central stub/fallback audit utilities.

This module enforces a strict backend policy when the environment variable
``SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1`` (or a true-ish value) is set. In this
mode any call to ``record_stub`` raises an error, preventing silent fallback to
stub or in-process simulated components.

Outside enforcement mode, we count stub usages for observability so tests or
runtime diagnostics can assert that *no* stub paths were exercised if that
is desired. Counts are kept process-local.

Usage:
    from somabrain.stub_audit import record_stub, BACKEND_ENFORCED, stub_stats
    record_stub("predictor.stub")

Expose minimal helper to fetch current counts.
"""

from __future__ import annotations

import os
import threading
from typing import Dict

_LOCK = threading.Lock()
_COUNTS: Dict[str, int] = {}


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name, "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


BACKEND_ENFORCED: bool = _env_bool("SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS", False)


class StubUsageError(RuntimeError):
    """Raised when a stub path is invoked while external backends are required."""


def record_stub(path: str) -> None:
    """Record that a stub/fallback path was invoked.

    If backend enforcement is enabled this raises immediately with an explanatory
    message instructing how to disable the stub path or configure the external
    component.
    """
    if BACKEND_ENFORCED:
        raise StubUsageError(
            f"Stub/fallback path '{path}' invoked while external backends are required. "
            "Configure the external component or unset SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS to allow stubs."
        )
    with _LOCK:
        _COUNTS[path] = _COUNTS.get(path, 0) + 1


def stub_stats() -> dict:
    """Return a shallow copy of current stub usage counts."""
    with _LOCK:
        return dict(_COUNTS)


__all__ = ["record_stub", "stub_stats", "BACKEND_ENFORCED", "StubUsageError"]
