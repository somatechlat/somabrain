"""Stub ``observability`` package used by the test suite.

The production code expects ``observability.provider`` to exist.  In the
repository we provide a minimal implementation in ``observability/provider.py``.
This ``__init__`` module imports that provider and registers it as a submodule
so that ``from observability.provider import init_tracing, get_tracer`` works
without any external dependencies.
"""

import importlib
import sys

# Load the provider implementation from the sibling ``provider.py``.
_provider = importlib.import_module("observability.provider")

# Expose it as ``observability.provider`` for import statements.
sys.modules[__name__ + ".provider"] = _provider
