"""Top‑level proxy for the ``observability`` package used in tests.

The production code imports ``observability.provider``.  In the test
environment only the ``somabrain.observability`` package is installed, so a
top‑level ``observability`` package does not exist on ``sys.path``.  This shim
module loads the real provider implementation from ``somabrain.observability``
and registers it as a submodule of this placeholder, making
``from observability.provider import ...`` work without modifying the service
source files.
"""

import importlib
import sys

# Load the actual provider implementation from the ``somabrain`` package.
_provider = importlib.import_module("somabrain.observability.provider")

# Expose it as ``observability.provider`` so that ``from observability.provider``
# resolves correctly.
sys.modules[__name__ + ".provider"] = _provider
"""Top‑level proxy for the ``observability`` package used in tests.

The production code imports ``observability.provider``.  In the test
environment only the ``somabrain.observability`` package is installed, so a
top‑level ``observability`` package does not exist on ``sys.path``.  This shim
loads the real provider module and registers it as a submodule of this
placeholder, making ``from observability.provider import ...`` work without
modifying the service source files.
"""

import importlib
import sys

# Load the actual provider implementation from the ``somabrain`` package.
_provider = importlib.import_module("somabrain.observability.provider")

# Expose it as ``observability.provider`` so that ``from observability.provider``
# resolves correctly.
sys.modules[__name__ + ".provider"] = _provider
