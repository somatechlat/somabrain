"""Shim to expose ``observability.provider`` during tests.

This file ensures that ``from observability.provider import …`` works even when
only ``somabrain.observability.provider`` is present on ``sys.path``. It
forwards the provider implementation from the ``somabrain`` package.
"""

import importlib
import sys

# Load the provider implementation from the package under ``somabrain``.
_provider = importlib.import_module("somabrain.observability.provider")

# Register it under the expected name ``observability.provider``.
sys.modules[__name__ + ".provider"] = _provider

# Optional: expose attributes for direct access if someone imports ``observability``
# and expects to find ``get_tracer`` or ``init_tracing`` at the top level.
try:
    init_tracing = getattr(_provider, "init_tracing")  # type: ignore[attr-defined]
    get_tracer = getattr(_provider, "get_tracer")  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - best effort exposure only
    pass
