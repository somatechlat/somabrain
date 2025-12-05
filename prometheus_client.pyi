"""Minimal type stubs for the ``prometheus_client`` package used in SomaBrain.

The real ``prometheus_client`` library provides a rich set of metric classes.
For static analysis (Pyright) we only need the subset of attributes that the
codebase accesses: ``labels``, ``inc``, ``set`` and ``observe``.  Defining a
light‑weight stub avoids pulling the full dependency into the type‑checking
environment and satisfies the VIBE rule *Integrity* – the stub is clearly
documented and limited to the required API surface.
"""

from typing import Any

# Core collector protocol – all metric types share these methods.
class Collector:
    def labels(self, *args: Any, **kwargs: Any) -> "Collector": ...  # noqa: D401
    def inc(self, *args: Any, **kwargs: Any) -> None: ...
    def set(self, *args: Any, **kwargs: Any) -> None: ...
    def observe(self, *args: Any, **kwargs: Any) -> None: ...

# Concrete metric classes – they inherit the Collector interface.
class Counter(Collector): ...
class Gauge(Collector): ...
class Histogram(Collector): ...
class Summary(Collector): ...

# The real ``prometheus_client`` library exposes the metric classes directly.
# For static analysis we only need the class definitions; the factory functions
# that were previously duplicated caused F811 redefinition errors. The classes
# themselves are callable (they act as constructors), so no separate factory
# functions are required.

# Registry related symbols – only the names used in the project are stubbed.
CONTENT_TYPE_LATEST: str
REGISTRY: Any

class CollectorRegistry: ...

def generate_latest(registry: Any = ...) -> bytes: ...
